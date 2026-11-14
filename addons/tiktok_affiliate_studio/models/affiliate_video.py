from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AffiliateVideo(models.Model):
    _name = 'affiliate.video'
    _description = 'Affiliate Video'

    name = fields.Char(required=True)
    campaign_id = fields.Many2one('affiliate.campaign', required=True, ondelete='restrict')
    channel_id = fields.Many2one(related='campaign_id.channel_id', store=True)
    campaign_type = fields.Selection(related='campaign_id.campaign_type', store=True)
    template_id = fields.Many2one('affiliate.video.template', required=True, ondelete='restrict')
    product_id = fields.Many2one('affiliate.product', ondelete='restrict')
    script_json = fields.Text()
    caption = fields.Text()
    hashtags = fields.Char()
    video_path = fields.Char()
    state = fields.Selection(
        [('draft', 'Draft'), ('rendered', 'Rendered'), ('approved', 'Approved')],
        required=True, default='draft',
    )

    @api.constrains('campaign_id', 'template_id', 'product_id')
    def _check_campaign_inputs(self):
        for video in self:
            if video.template_id.campaign_type != video.campaign_type:
                raise ValidationError('Choose a template that matches the campaign type.')
            if video.campaign_type == 'affiliate' and not video.product_id:
                raise ValidationError('Choose a product for an affiliate video.')
            if video.product_id and video.channel_id not in video.product_id.channel_ids:
                raise ValidationError('The product must be assigned to the campaign channel.')

    @api.constrains('state', 'video_path')
    def _check_output(self):
        for video in self:
            if video.state in ('rendered', 'approved') and not video.video_path:
                raise ValidationError('Enter the MP4 path before marking the video rendered or approved.')
