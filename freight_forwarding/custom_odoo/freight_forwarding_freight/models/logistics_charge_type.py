from odoo import models, fields


class LogisticsChargeType(models.Model):
    _name = 'logistics.charge.type'
    _description = 'Logistics Charge Type'
    _order = 'category, name'

    name = fields.Char(string='Charge Name', required=True)
    code = fields.Char(string='Code')
    category = fields.Selection([
        ('freight', 'Freight'),
        ('terminal', 'Terminal / Port'),
        ('documentation', 'Documentation'),
        ('customs', 'Customs'),
        ('transport', 'Transport / Delivery'),
        ('handling', 'Handling'),
        ('surcharge', 'Surcharge'),
        ('revenue_share', 'Revenue Share'),
        ('other', 'Other'),
    ], string='Category', default='other')
    active = fields.Boolean(default=True)
