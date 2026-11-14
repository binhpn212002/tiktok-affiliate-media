from odoo import fields, models

from .campaign_types import CAMPAIGN_TYPES


class AffiliateCampaign(models.Model):
    _name = 'affiliate.campaign'
    _description = 'TikTok Campaign'

    name = fields.Char(required=True)
    channel_id = fields.Many2one('affiliate.channel', required=True, ondelete='restrict')
    campaign_type = fields.Selection(CAMPAIGN_TYPES, required=True, default='affiliate')
    active = fields.Boolean(default=True)
