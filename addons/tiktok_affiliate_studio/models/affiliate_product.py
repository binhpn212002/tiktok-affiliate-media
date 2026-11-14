from odoo import fields, models


class AffiliateProduct(models.Model):
    _name = 'affiliate.product'
    _description = 'Affiliate Product'

    name = fields.Char(required=True)
    shop_name = fields.Char(required=True)
    sku = fields.Char()
    tiktok_product_id = fields.Char()
    product_url = fields.Char()
    image = fields.Image()
    channel_ids = fields.Many2many('affiliate.channel', string='Channels')
