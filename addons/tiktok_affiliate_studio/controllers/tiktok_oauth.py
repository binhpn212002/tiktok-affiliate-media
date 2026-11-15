import secrets
import time

from odoo import _, http
from odoo.http import request

from ..services.tiktok_oauth import CALLBACK_PATH, TikTokError


class TikTokOAuth(http.Controller):
    @http.route(CALLBACK_PATH, type='http', auth='user', methods=['GET'], sitemap=False)
    def callback(self, state=None, code=None, error=None, **kwargs):
        pending = request.session.get('affiliate_tiktok_oauth')
        if (
            not pending or pending['uid'] != request.env.uid or pending['db'] != request.db
            or time.time() > pending['expires'] or not state
            or not secrets.compare_digest(state.encode(), pending['state'].encode())
        ):
            return request.make_response(_("Invalid or expired TikTok authorization. Start again from Channels."),
                                         status=400, headers=[('Cache-Control', 'no-store')])
        request.session.pop('affiliate_tiktok_oauth', None)

        channel = request.env['affiliate.channel'].browse(pending['channel_id']).exists()
        if not channel:
            return request.not_found()
        channel.check_access_rights('write')
        channel.check_access_rule('write')
        try:
            if error or not code:
                raise TikTokError(_("TikTok authorization was cancelled or denied."))
            channel._connect_tiktok(code)
        except TikTokError as failure:
            channel.write({'tiktok_sync_error': str(failure)})

        action = request.env.ref('tiktok_affiliate_studio.action_affiliate_channel').id
        return request.redirect(f'/web#action={action}&id={channel.id}&model=affiliate.channel&view_type=form',
                                code=303)
