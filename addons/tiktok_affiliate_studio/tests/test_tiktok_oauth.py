from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests import TransactionCase

from ..services import tiktok_oauth


class TestTikTokOAuth(TransactionCase):
    def setUp(self):
        super().setUp()
        self.channel = self.env['affiliate.channel'].create({'name': 'TikTok test'})
        self.token = {
            'access_token': 'first-access',
            'refresh_token': 'first-refresh',
            'open_id': 'account-1',
            'scope': 'user.info.basic,user.info.profile,user.info.stats',
            'expires_in': 7200,
            'refresh_expires_in': 86400,
        }

    def test_connect_syncs_profile(self):
        user = {
            'open_id': 'account-1', 'display_name': 'Example', 'username': 'example',
            'follower_count': 300, 'following_count': 10, 'likes_count': 500, 'video_count': 3,
        }
        with (
            patch.object(tiktok_oauth, 'request_token', return_value=self.token) as exchange,
            patch.object(tiktok_oauth, 'fetch_user', return_value=user),
        ):
            self.channel._connect_tiktok('authorization-code')
        exchange.assert_called_once_with(code='authorization-code')
        self.assertEqual(self.channel.tiktok_status, 'connected')
        self.assertEqual(self.channel.tiktok_followers, 300)
        self.assertEqual(self.channel.tiktok_likes, 500)
        self.assertTrue(self.channel.tiktok_has_stats)

    def test_cron_keeps_rotated_token_when_profile_sync_fails(self):
        credentials = self.env['affiliate.tiktok.credential'].sudo()
        credential = credentials.create(self.channel._tiktok_token_values(self.token))
        credential.expires_at = fields.Datetime.now() + timedelta(minutes=5)
        self.channel.tiktok_status = 'connected'
        rotated = dict(self.token, access_token='next-access', refresh_token='next-refresh')
        with (
            patch.object(tiktok_oauth, 'request_token', return_value=rotated) as refresh,
            patch.object(tiktok_oauth, 'fetch_user', side_effect=tiktok_oauth.TikTokError('Temporary failure')),
        ):
            self.channel._cron_sync_tiktok()
        refresh.assert_called_once_with(refresh_token='first-refresh')
        self.assertEqual(credential.refresh_token, 'next-refresh')
        self.assertEqual(credential.access_token, 'next-access')
        self.assertEqual(self.channel.tiktok_sync_error, 'Temporary failure')
        self.assertEqual(self.channel.tiktok_status, 'connected')
