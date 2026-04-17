from odoo import fields, models


class HSCode(models.Model):
    _name = 'master.hs.code'
    _description = 'HS Code'
    _order = 'code'

    name = fields.Char(string='Description', required=True)
    code = fields.Char(string='HS Code', required=True)
    chapter = fields.Char(string='Chapter')
    active = fields.Boolean(default=True)

    _code_uniq = models.Constraint(
        'unique(code)',
        'The HS Code must be unique.',
    )
