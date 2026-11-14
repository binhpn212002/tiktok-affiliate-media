from odoo import fields, models


class AffiliateChannel(models.Model):
    _name = 'affiliate.channel'
    _description = 'TikTok Channel'

    name = fields.Char(required=True)
    topic = fields.Char()
    timezone = fields.Char(default='Asia/Ho_Chi_Minh', required=True)
    voice = fields.Char()
    active = fields.Boolean(default=True)
