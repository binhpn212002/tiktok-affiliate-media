import json
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase

from ..models import affiliate_video


class TestVideoRender(TransactionCase):
    def setUp(self):
        super().setUp()
        channel = self.env['affiliate.channel'].create({'name': 'Render test'})
        campaign = self.env['affiliate.campaign'].create({
            'name': 'Render test',
            'channel_id': channel.id,
            'campaign_type': 'community',
        })
        self.video = self.env['affiliate.video'].create({
            'name': 'Render test',
            'campaign_id': campaign.id,
        })

    def test_invalid_script_stays_idle(self):
        self.video.script_json = '{"scenes": []}'
        with self.assertRaises(ValidationError):
            self.video.action_queue_render()
        self.assertEqual(self.video.render_status, 'idle')

    def test_queue_and_render_in_sequence_order(self):
        url = 'https://images.example.com/product.png'
        self.video.script_json = json.dumps({
            'caption': 'Demo',
            'hashtags': ['#demo'],
            'scenes': [
                {'sequence': 2, 'narration': 'Second', 'image_url': url},
                {'sequence': 1, 'narration': 'First', 'image_url': url},
            ],
        })
        with patch.dict('os.environ', {'R2_PUBLIC_BASE_URL': 'https://images.example.com'}):
            self.video.action_queue_render()
            self.video.action_queue_render()
            self.assertEqual(self.video.render_status, 'queued')
            with (
                patch.object(affiliate_video, 'render_video', return_value=b'mock MP4') as render,
                patch.object(affiliate_video, 'upload_objects', return_value=[url]) as upload,
            ):
                self.video._cron_render_video()

        render.assert_called_once_with([
            {'sequence': 1, 'narration': 'First', 'image_url': url},
            {'sequence': 2, 'narration': 'Second', 'image_url': url},
        ], self.video.channel_id.voice)
        self.assertEqual(self.video.render_status, 'done')
        self.assertEqual(self.video.state, 'rendered')
        self.assertEqual(self.video.caption, 'Demo')
        self.assertEqual(self.video.hashtags, '#demo')
        self.assertEqual(self.video.video_path, url)
        upload.assert_called_once()
        [(key, data, content_type)] = upload.call_args.args[0]
        self.assertTrue(key.startswith('videos/') and key.endswith('.mp4'))
        self.assertEqual((data, content_type), (b'mock MP4', 'video/mp4'))
        self.assertFalse(self.video.rendered_mp4)
