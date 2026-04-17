from odoo import api, fields, models


class AutoExchangeRate(models.Model):
    _name = 'master.exchange.rate'
    _description = 'Automatic Exchange Rate'
    _order = 'date desc'

    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    rate = fields.Float(string='Rate', digits=(12, 6), required=True)
    inverse_rate = fields.Float(string='Inverse Rate', digits=(12, 6),
                                compute='_compute_inverse_rate', store=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    source = fields.Char(string='Source')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    @api.depends('rate')
    def _compute_inverse_rate(self):
        for rec in self:
            rec.inverse_rate = (1.0 / rec.rate) if rec.rate else 0.0
