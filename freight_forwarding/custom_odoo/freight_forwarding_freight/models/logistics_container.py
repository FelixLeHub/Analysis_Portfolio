from odoo import models, fields


class LogisticsContainer(models.Model):
    _name = 'logistics.container'
    _description = 'Logistics Container'
    _order = 'job_id, id'

    name = fields.Char(string='Container No', required=True)
    job_id = fields.Many2one(
        'logistics.job', string='Job',
        required=True, ondelete='cascade',
    )
    container_type = fields.Selection([
        ('20gp', "20' GP"),
        ('40gp', "40' GP"),
        ('40hc', "40' HC"),
        ('20rf', "20' Reefer"),
        ('40rf', "40' Reefer"),
        ('20ot', "20' Open Top"),
        ('40ot', "40' Open Top"),
        ('45hc', "45' HC"),
    ], string='Type')
    seal_no = fields.Char(string='Seal No')
    gross_weight = fields.Float(string='Gross Weight (KG)')
    package_count = fields.Integer(string='No. of Packages')
    description = fields.Text(string='Goods Description')
    notes = fields.Text(string='Notes')
