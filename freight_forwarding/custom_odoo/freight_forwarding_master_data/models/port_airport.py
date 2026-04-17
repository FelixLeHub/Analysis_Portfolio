from odoo import api, fields, models


class PortAirport(models.Model):
    _name = 'master.port.airport'
    _description = 'Port & Airport'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    type = fields.Selection([
        ('seaport', 'Seaport'),
        ('airport', 'Airport'),
        ('inland', 'Inland Port'),
    ], string='Type', required=True, default='seaport')
    country_id = fields.Many2one('res.country', string='Country')
    city = fields.Char(string='City')
    active = fields.Boolean(default=True)

    _code_uniq = models.Constraint(
        'unique(code)',
        'The port/airport code must be unique.',
    )
