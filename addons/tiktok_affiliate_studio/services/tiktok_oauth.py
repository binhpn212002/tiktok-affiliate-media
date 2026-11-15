import os
from urllib.parse import urlencode, urlsplit

import requests

from odoo import _
from odoo.exceptions import UserError

TOKEN_URL = 'https://open.tiktokapis.com/v2/oauth/token/'
USER_INFO_URL = 'https://open.tiktokapis.com/v2/user/info/'
CALLBACK_PATH = '/tiktok/oauth/callback'
SCOPE_FIELDS = {
    'user.info.basic': ('open_id', 'display_name', 'avatar_url'),
    'user.info.profile': ('username', 'bio_description', 'profile_deep_link', 'is_verified'),
    'user.info.stats': ('follower_count', 'following_count', 'likes_count', 'video_count'),
}


class TikTokError(UserError):
    def __init__(self, message, *, reauthorize=False):
        super().__init__(message)
        self.reauthorize = reauthorize


def configuration():
    key = os.getenv('TIKTOK_CLIENT_KEY', '').strip()
    secret = os.getenv('TIKTOK_CLIENT_SECRET', '').strip()
    redirect = os.getenv('TIKTOK_REDIRECT_URI', '').strip()
    url = urlsplit(redirect)
    if (
        not key or not secret or url.scheme != 'https' or not url.hostname
        or url.path != CALLBACK_PATH or url.username or url.query or url.fragment
    ):
        raise TikTokError(_("Set the TikTok client key, secret and HTTPS callback URL on the Odoo server."))
    return key, secret, redirect


def authorization_url(state):
    key, _, redirect = configuration()
    query = urlencode({
        'client_key': key,
        'response_type': 'code',
        'scope': ','.join(SCOPE_FIELDS),
        'redirect_uri': redirect,
        'state': state,
    })
    return f'https://www.tiktok.com/v2/auth/authorize/?{query}'


def _request(method, url, **kwargs):
    try:
        response = requests.request(method, url, timeout=(5, 15), allow_redirects=False, **kwargs)
        payload = response.json()
    except (requests.RequestException, ValueError):
        raise TikTokError(_("TikTok did not return a valid response. Try again later.")) from None
    if not isinstance(payload, dict):
        raise TikTokError(_("TikTok returned an unexpected response."))
    error = payload.get('error')
    code = error.get('code') if isinstance(error, dict) else error
    if response.status_code != 200 or code not in (None, 'ok'):
        expired = url == TOKEN_URL and code == 'invalid_grant'
        message = _("TikTok authorization expired or was revoked. Connect again.") if expired else _(
            "TikTok rejected the request. Check app settings and granted permissions."
        )
        raise TikTokError(message, reauthorize=expired)
    return payload


def request_token(*, code=None, refresh_token=None):
    key, secret, redirect = configuration()
    data = {'client_key': key, 'client_secret': secret}
    if code:
        data.update(grant_type='authorization_code', code=code, redirect_uri=redirect)
    else:
        data.update(grant_type='refresh_token', refresh_token=refresh_token)
    result = _request('POST', TOKEN_URL, data=data)
    for name in ('access_token', 'refresh_token', 'open_id', 'scope'):
        if not isinstance(result.get(name), str) or not result[name]:
            raise TikTokError(_("TikTok returned incomplete credentials."))
    for name in ('expires_in', 'refresh_expires_in'):
        if type(result.get(name)) is not int or result[name] <= 0:
            raise TikTokError(_("TikTok returned an invalid token expiry."))
    return result


def fetch_user(access_token, scope):
    granted = set(scope.split(','))
    requested = [field for name, names in SCOPE_FIELDS.items() if name in granted for field in names]
    if 'open_id' not in requested:
        raise TikTokError(_("Grant access to basic TikTok account information and connect again."))
    payload = _request('GET', USER_INFO_URL, params={'fields': ','.join(requested)},
                       headers={'Authorization': f'Bearer {access_token}'})
    data = payload.get('data')
    user = data.get('user') if isinstance(data, dict) else None
    if not isinstance(user, dict) or not user.get('open_id'):
        raise TikTokError(_("TikTok did not return an account profile."))
    return {field: user[field] for field in requested if field in user}
