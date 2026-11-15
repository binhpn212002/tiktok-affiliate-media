import hashlib
import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..services.r2_storage import upload_objects
from ..services.video_render import allowed_image_url, render_video

_logger = logging.getLogger(__name__)


class AffiliateVideo(models.Model):
    _name = 'affiliate.video'
    _description = 'Affiliate Video'

    name = fields.Char(required=True)
    campaign_id = fields.Many2one('affiliate.campaign', required=True, ondelete='restrict')
    channel_id = fields.Many2one(related='campaign_id.channel_id', store=True)
    campaign_type = fields.Selection(related='campaign_id.campaign_type', store=True)
    product_id = fields.Many2one('affiliate.product', ondelete='restrict')
    script_json = fields.Text()
    caption = fields.Text()
    hashtags = fields.Char()
    video_path = fields.Char()
    rendered_mp4 = fields.Binary(attachment=True, readonly=True, copy=False)
    render_status = fields.Selection(
        [('idle', 'Idle'), ('queued', 'Queued'), ('failed', 'Failed'), ('done', 'Done')],
        default='idle', required=True, readonly=True, copy=False,
    )
    render_error = fields.Char(readonly=True, copy=False)
    state = fields.Selection(
        [('draft', 'Draft'), ('rendered', 'Rendered'), ('approved', 'Approved')],
        required=True, default='draft',
    )

    @api.constrains('campaign_id', 'product_id')
    def _check_campaign_inputs(self):
        for video in self:
            if video.campaign_type == 'affiliate' and not video.product_id:
                raise ValidationError('Choose a product for an affiliate video.')
            if video.product_id and video.channel_id not in video.product_id.channel_ids:
                raise ValidationError('The product must be assigned to the campaign channel.')

    @api.constrains('state', 'video_path')
    def _check_output(self):
        for video in self:
            if video.state in ('rendered', 'approved') and not video.video_path:
                raise ValidationError('Enter the MP4 path before marking the video rendered or approved.')

    def _parse_render_script(self):
        self.ensure_one()
        try:
            payload = json.loads(self.script_json or '')
        except ValueError as error:
            raise ValidationError(_("Paste a valid JSON script.")) from error
        scenes = payload.get('scenes') if isinstance(payload, dict) else None
        if not isinstance(scenes, list) or not scenes:
            raise ValidationError(_("The JSON script must contain a non-empty scenes list."))

        image_urls = self.product_id.image_ids.sorted('id').mapped('url')
        sequences = set()
        parsed = []
        for position, scene in enumerate(scenes, start=1):
            if not isinstance(scene, dict):
                raise ValidationError(_("Scene %(position)s must be a JSON object.", position=position))
            sequence = scene.get('sequence')
            narration = scene.get('narration')
            if type(sequence) is not int or sequence < 1 or sequence in sequences:
                raise ValidationError(_("Scene %(position)s needs a unique positive sequence.", position=position))
            if not isinstance(narration, str) or not narration.strip():
                raise ValidationError(_("Scene %(scene)s needs narration.", scene=sequence))

            if 'image_index' in scene:
                index = scene['image_index']
                if 'image_url' in scene or type(index) is not int or not 1 <= index <= len(image_urls):
                    raise ValidationError(_("Scene %(scene)s has an invalid product image index.", scene=sequence))
                url = image_urls[index - 1]
            else:
                url = scene.get('image_url')
            if not allowed_image_url(url):
                raise ValidationError(_("Scene %(scene)s needs an image from the configured R2 bucket.", scene=sequence))
            sequences.add(sequence)
            parsed.append({'sequence': sequence, 'narration': narration.strip(), 'image_url': url})

        caption = payload.get('caption')
        hashtags = payload.get('hashtags')
        if 'caption' in payload and not isinstance(caption, str):
            raise ValidationError(_("Caption must be text."))
        if 'hashtags' in payload and (
            not isinstance(hashtags, list) or any(not isinstance(tag, str) for tag in hashtags)
        ):
            raise ValidationError(_("Hashtags must be a list of strings."))
        return sorted(parsed, key=lambda scene: scene['sequence']), payload

    def action_queue_render(self):
        self.ensure_one()
        self.check_access_rights('write')
        self.check_access_rule('write')
        self.env.cr.execute("SELECT id FROM affiliate_video WHERE id = %s FOR UPDATE", [self.id])
        self.invalidate_recordset(['render_status', 'state'])
        if self.render_status == 'queued':
            return
        if self.state != 'draft':
            raise UserError(_("Set the video to Draft before rendering."))
        _, payload = self._parse_render_script()
        values = {'render_status': 'queued', 'render_error': False}
        if 'caption' in payload:
            values['caption'] = payload['caption']
        if 'hashtags' in payload:
            values['hashtags'] = ' '.join(payload['hashtags'])
        self.write(values)
        self.env.ref('tiktok_affiliate_studio.ir_cron_render_video').sudo()._trigger()

    @api.model
    def _cron_render_video(self):
        self.flush_model(["render_status"])
        self.env.cr.execute("""
            SELECT id FROM affiliate_video
             WHERE render_status = 'queued'
             ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED
        """)
        row = self.env.cr.fetchone()
        if not row:
            return
        video = self.browse(row[0])
        try:
            with self.env.cr.savepoint():
                if video.state != 'draft':
                    raise UserError(_("Set the video to Draft before rendering."))
                scenes, _ = video._parse_render_script()
                mp4 = render_video(scenes, video.channel_id.voice)
                checksum = hashlib.sha256(mp4).hexdigest()
                key = f'videos/{checksum}.mp4'
                [url] = upload_objects([(key, mp4, 'video/mp4')])
                video.write({
                    'video_path': url,
                    'state': 'rendered',
                    'render_status': 'done',
                    'render_error': False,
                })
        except Exception as error:
            _logger.exception("Rendering affiliate video %s failed", video.id)
            message = str(error) if isinstance(error, UserError) else _("Render failed. Check the server log.")
            video.write({'render_status': 'failed', 'render_error': message})
        if self.search_count([('render_status', '=', 'queued')], limit=1):
            self.env.ref('tiktok_affiliate_studio.ir_cron_render_video').sudo()._trigger()
