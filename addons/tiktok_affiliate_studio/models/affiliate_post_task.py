from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AffiliatePostTask(models.Model):
    _name = 'affiliate.post.task'
    _description = 'TikTok Posting Task'

    name = fields.Char(required=True)
    video_id = fields.Many2one('affiliate.video', required=True, ondelete='restrict')
    channel_id = fields.Many2one(related='video_id.channel_id', store=True)
    product_id = fields.Many2one(related='video_id.product_id')
    video_path = fields.Char(related='video_id.video_path')
    caption = fields.Text(related='video_id.caption')
    hashtags = fields.Char(related='video_id.hashtags')
    state = fields.Selection(
        [('pending', 'Pending'), ('published', 'Published')],
        required=True, default='pending',
    )
    post_url = fields.Char()
    published_at = fields.Datetime()
    manual_minutes = fields.Float()

    @api.constrains('video_id')
    def _check_approved_video(self):
        for task in self:
            if task.video_id.state != 'approved':
                raise ValidationError('Choose an approved video.')

    @api.constrains('state', 'post_url', 'published_at')
    def _check_publication_details(self):
        for task in self:
            if task.state == 'published' and not (task.post_url and task.published_at):
                raise ValidationError('Enter the post URL and publishing time.')
