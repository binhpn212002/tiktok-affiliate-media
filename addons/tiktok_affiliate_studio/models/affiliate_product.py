from odoo import fields, models


class AffiliateProduct(models.Model):
    _name = 'affiliate.product'
    _description = 'Affiliate Product'

    name = fields.Char(required=True)
    product_url = fields.Char()
    image_ids = fields.One2many("affiliate.product.image", "product_id", string="Images")
    channel_ids = fields.Many2many('affiliate.channel', string='Channels')
