from datetime import timedelta
import secrets
import time

from odoo import _, api, fields, models
from odoo.http import request

from ..services import tiktok_oauth


class AffiliateChannel(models.Model):
    _name = 'affiliate.channel'
    _description = 'TikTok Channel'

    name = fields.Char(required=True)
    topic = fields.Char()
    timezone = fields.Char(default='Asia/Ho_Chi_Minh', required=True)
    voice = fields.Char()
    active = fields.Boolean(default=True)

    tiktok_status = fields.Selection(
        [('disconnected', 'Disconnected'), ('connected', 'Connected'), ('expired', 'Reconnect required')],
        default='disconnected', readonly=True, copy=False,
    )
    tiktok_display_name = fields.Char(readonly=True, copy=False)
    tiktok_username = fields.Char(readonly=True, copy=False)
    tiktok_avatar_url = fields.Char(readonly=True, copy=False)
    tiktok_profile_url = fields.Char(readonly=True, copy=False)
    tiktok_bio = fields.Text(readonly=True, copy=False)
    tiktok_verified = fields.Boolean(readonly=True, copy=False)
    tiktok_followers = fields.Float(digits=(20, 0), readonly=True, copy=False)
    tiktok_following = fields.Float(digits=(20, 0), readonly=True, copy=False)
    tiktok_likes = fields.Float(digits=(20, 0), readonly=True, copy=False)
    tiktok_videos = fields.Float(digits=(20, 0), readonly=True, copy=False)
    tiktok_has_stats = fields.Boolean(readonly=True, copy=False)
    tiktok_synced_at = fields.Datetime(readonly=True, copy=False)
    tiktok_sync_attempt_at = fields.Datetime(readonly=True, copy=False)
    tiktok_sync_error = fields.Char(readonly=True, copy=False)

    def action_connect_tiktok(self):
        self.ensure_one()
        self.check_access_rights('write')
        self.check_access_rule('write')
        state = secrets.token_urlsafe(32)
        url = tiktok_oauth.authorization_url(state)
        request.session['affiliate_tiktok_oauth'] = {
            'state': state, 'channel_id': self.id, 'uid': self.env.uid,
            'db': self.env.cr.dbname, 'expires': time.time() + 600,
        }
        return {'type': 'ir.actions.act_url', 'url': url, 'target': 'self'}

    def action_sync_tiktok(self):
        self.ensure_one()
        self.check_access_rights('write')
        self.check_access_rule('write')
        self._sync_tiktok()
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def _tiktok_credential(self):
        self.ensure_one()
        return self.env['affiliate.tiktok.credential'].sudo().search([('channel_id', '=', self.id)], limit=1)

    def _lock_tiktok_channel(self):
        self.env.cr.execute("SELECT id FROM affiliate_channel WHERE id = %s FOR UPDATE", [self.id])

    def _tiktok_token_values(self, token):
        now = fields.Datetime.now()
        return {
            'channel_id': self.id,
            'open_id': token['open_id'],
            'access_token': token['access_token'],
            'refresh_token': token['refresh_token'],
            'scope': token['scope'],
            'expires_at': now + timedelta(seconds=token['expires_in']),
            'refresh_expires_at': now + timedelta(seconds=token['refresh_expires_in']),
        }

    def _connect_tiktok(self, code):
        self.ensure_one()
        self._lock_tiktok_channel()
        token = tiktok_oauth.request_token(code=code)
        if 'user.info.basic' not in token['scope'].split(','):
            raise tiktok_oauth.TikTokError(_("Grant access to basic TikTok account information and connect again."))
        credentials = self.env['affiliate.tiktok.credential'].sudo()
        if credentials.search_count([('open_id', '=', token['open_id']), ('channel_id', '!=', self.id)], limit=1):
            raise tiktok_oauth.TikTokError(_("This TikTok account is already connected to another channel."))
        credential = self._tiktok_credential()
        values = self._tiktok_token_values(token)
        if credential:
            credential.write(values)
        else:
            credentials.create(values)
        self.write({
            'tiktok_status': 'connected', 'tiktok_synced_at': False,
            'tiktok_has_stats': False, 'tiktok_sync_error': False,
            'tiktok_display_name': False, 'tiktok_username': False, 'tiktok_avatar_url': False,
            'tiktok_profile_url': False, 'tiktok_bio': False, 'tiktok_verified': False,
            'tiktok_followers': 0, 'tiktok_following': 0, 'tiktok_likes': 0, 'tiktok_videos': 0,
        })
        self._sync_tiktok()

    def _sync_tiktok(self):
        self.ensure_one()
        self._lock_tiktok_channel()
        credential = self._tiktok_credential()
        if not credential:
            return
        credential.invalidate_recordset()
        now = fields.Datetime.now()
        self.write({'tiktok_sync_attempt_at': now})
        try:
            if credential.expires_at <= now + timedelta(minutes=20):
                if credential.refresh_expires_at <= now:
                    raise tiktok_oauth.TikTokError(_("TikTok authorization expired. Connect again."), reauthorize=True)
                token = tiktok_oauth.request_token(refresh_token=credential.refresh_token)
                if token['open_id'] != credential.open_id:
                    raise tiktok_oauth.TikTokError(_("TikTok returned credentials for a different account."), reauthorize=True)
                credential.write(self._tiktok_token_values(token))

            user = tiktok_oauth.fetch_user(credential.access_token, credential.scope)
            if user['open_id'] != credential.open_id:
                raise tiktok_oauth.TikTokError(_("TikTok returned a different account profile."), reauthorize=True)
            has_stats = all(name in user for name in tiktok_oauth.SCOPE_FIELDS['user.info.stats'])
            self.write({
                'tiktok_status': 'connected',
                'tiktok_display_name': user.get('display_name'),
                'tiktok_username': user.get('username'),
                'tiktok_avatar_url': user.get('avatar_url'),
                'tiktok_profile_url': user.get('profile_deep_link'),
                'tiktok_bio': user.get('bio_description'),
                'tiktok_verified': user.get('is_verified', False),
                'tiktok_followers': user.get('follower_count', 0),
                'tiktok_following': user.get('following_count', 0),
                'tiktok_likes': user.get('likes_count', 0),
                'tiktok_videos': user.get('video_count', 0),
                'tiktok_has_stats': has_stats,
                'tiktok_synced_at': now,
                'tiktok_sync_error': False if has_stats else _("Grant the user.info.stats permission to see channel statistics."),
            })
        except tiktok_oauth.TikTokError as error:
            values = {'tiktok_sync_error': str(error)}
            if error.reauthorize:
                values['tiktok_status'] = 'expired'
            self.write(values)

    @api.model
    def _cron_sync_tiktok(self):
        now = fields.Datetime.now()
        credentials = self.env['affiliate.tiktok.credential'].sudo().search([
            ('channel_id.active', '=', True),
            ('channel_id.tiktok_status', '=', 'connected'),
            '|', ('channel_id.tiktok_sync_attempt_at', '=', False),
            ('channel_id.tiktok_sync_attempt_at', '<=', now - timedelta(minutes=9)),
            '|', ('expires_at', '<=', now + timedelta(minutes=20)),
            '|', ('channel_id.tiktok_synced_at', '=', False),
            ('channel_id.tiktok_synced_at', '<=', now - timedelta(hours=1)),
        ], order='expires_at, id', limit=20)
        for channel in credentials.mapped('channel_id'):
            channel._sync_tiktok()
