from odoo import fields, models


class ServiceType(models.Model):
    _name = 'master.service.type'
    _description = 'Service Type'
    _order = 'sequence, name'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
