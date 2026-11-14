from odoo import fields, models

from .campaign_types import CAMPAIGN_TYPES


class AffiliateVideoTemplate(models.Model):
    _name = 'affiliate.video.template'
    _description = 'Video Template'
    _order = 'code'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    campaign_type = fields.Selection(CAMPAIGN_TYPES, required=True)
    voice_requirement = fields.Selection(
        [('optional', 'Optional'), ('required', 'Required')],
        required=True, default='optional',
    )
    prompt = fields.Text()
    render_config = fields.Text()
    ready = fields.Boolean()
    _sql_constraints = [('code_unique', 'unique(code)', 'The template code must be unique.')]
