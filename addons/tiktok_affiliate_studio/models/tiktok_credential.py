from odoo import fields, models


class TikTokCredential(models.Model):
    _name = 'affiliate.tiktok.credential'
    _description = 'TikTok OAuth Credential'
    _rec_name = 'channel_id'

    channel_id = fields.Many2one('affiliate.channel', required=True, ondelete='cascade', index=True)
    open_id = fields.Char(required=True)
    access_token = fields.Char(required=True)
    refresh_token = fields.Char(required=True)
    scope = fields.Char(required=True)
    expires_at = fields.Datetime(required=True, index=True)
    refresh_expires_at = fields.Datetime(required=True)

    _sql_constraints = [
        ('channel_unique', 'unique(channel_id)', 'A channel can only have one TikTok connection.'),
        ('account_unique', 'unique(open_id)', 'This TikTok account is already connected to another channel.'),
    ]
