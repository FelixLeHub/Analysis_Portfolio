from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    logistics_job_id = fields.Many2one(
        'logistics.job', string='Logistics Job',
        index=True, tracking=True,
    )
