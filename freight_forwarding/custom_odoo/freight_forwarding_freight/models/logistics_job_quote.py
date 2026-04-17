from odoo import api, fields, models
from odoo.exceptions import ValidationError


RATE_SECTION_SELECTION = [
    ('truck_rate', 'Trucking Rate'),
    ('customs_import', 'Customs Import'),
    ('customs_export', 'Customs Export'),
    ('lcl_rate', 'LCL Rate'),
    ('fcl_ocean', 'FCL Ocean Rate'),
    ('air_rate', 'Air Rate'),
]

CHARGE_SECTION_SELECTION = [
    ('lcl_exwork', 'LCL Ex-work'),
    ('lcl_local_fcl', 'LCL Local FCL'),
    ('lcl_local_lcl', 'LCL Local LCL'),
    ('fcl_local', 'FCL Local Charge'),
    ('fcl_exwork', 'FCL Ex-work Fee'),
    ('air_exwork', 'Air Ex-work'),
    ('air_local', 'Air Local Charge'),
]

LAYOUT_SELECTION = [
    ('trucking_customs', 'Trucking + Customs'),
    ('sea_lcl', 'Sea LCL'),
    ('sea_fcl', 'Sea FCL'),
    ('air', 'Air'),
]

RATE_SECTIONS_BY_LAYOUT = {
    'trucking_customs': {'truck_rate', 'customs_import', 'customs_export'},
    'sea_lcl': {'lcl_rate'},
    'sea_fcl': {'fcl_ocean'},
    'air': {'air_rate'},
}

CHARGE_SECTIONS_BY_LAYOUT = {
    'trucking_customs': set(),
    'sea_lcl': {'lcl_exwork', 'lcl_local_fcl', 'lcl_local_lcl'},
    'sea_fcl': {'fcl_local', 'fcl_exwork'},
    'air': {'air_exwork', 'air_local'},
}

RATE_SECTION_LABELS = dict(RATE_SECTION_SELECTION)
CHARGE_SECTION_LABELS = dict(CHARGE_SECTION_SELECTION)
LAYOUT_LABELS = dict(LAYOUT_SELECTION)

RATE_FIELD_LABELS_BY_SECTION = {
    'truck_rate': {
        'name': 'Port or Airport',
        'destination_code': 'Destination',
        'amount_1': 'Truck 1.5 tons',
        'amount_2': 'Truck 3.5 tons',
        'amount_3': 'Truck 5 tons',
        'amount_4': '20 DC',
        'amount_5': '40 DC',
    },
    'customs_import': {
        'name': 'Types of Import',
        'destination_code': 'Destination',
        'amount_1': '1 - 3 CBMs',
        'amount_2': '3 - 5 CBMs',
        'amount_3': '5 - 10 CBMs',
        'amount_4': '20 DC',
        'amount_5': '40 DC',
    },
    'customs_export': {
        'name': 'Types',
        'carrier_or_party': 'Clients',
        'amount_1': '1 - 3 CBMs',
        'amount_2': '3 - 5 CBMs',
        'amount_3': '5 - 10 CBMs',
        'amount_4': '20 DC',
        'amount_5': '40 DC',
    },
    'lcl_rate': {
        'name': 'Country',
        'origin_code': 'POL',
        'destination_code': 'POD',
        'carrier_or_party': 'Line',
        'amount_1': 'Rate',
        'amount_2': 'CFS',
        'amount_3': 'THC',
        'amount_4': 'CIC',
        'amount_5': 'CLS',
        'amount_6': 'FRE',
        'transit_time': 'T/T',
    },
    'fcl_ocean': {
        'name': 'Lane',
        'origin_code': 'POL',
        'destination_code': 'POD',
        'carrier_or_party': 'Carrier',
        'amount_1': "20'DC",
        'amount_2': "40'HC",
        'frequency': 'Frequency',
        'note': 'Note',
        'transit_time': 'T/T',
    },
    'air_rate': {
        'name': 'Lane',
        'origin_code': 'AOL',
        'destination_code': 'AOD',
        'carrier_or_party': 'Carrier',
        'amount_1': '- 45 kgs',
        'amount_2': '+ 45 kgs',
        'amount_3': '+ 100 kgs',
        'amount_4': '+ 300 kgs',
        'amount_5': '+ 500 kgs',
        'amount_6': '+ 1000 kgs',
        'note': 'FRE',
        'transit_time': 'T/T',
    },
}

CHARGE_FIELD_LABELS_BY_SECTION = {
    'lcl_exwork': {
        'name': 'Charge',
        'unit_description': 'Unit',
        'amount': 'Amount',
    },
    'lcl_local_fcl': {
        'name': 'Charge',
        'amount_20dc': '20/40 Charge',
        'amount_40hc': '40HC Charge',
    },
    'lcl_local_lcl': {
        'name': 'Charge',
        'unit_description': 'Unit',
        'amount': 'Amount',
    },
    'fcl_local': {
        'name': 'Detail Charge',
        'unit_description': 'Unit Price',
        'amount_20dc': "20'DC",
        'amount_40hc': "40'HC",
        'remark': 'Remark',
    },
    'fcl_exwork': {
        'name': 'Charge',
        'unit_description': 'Unit',
        'amount': 'Amount',
    },
    'air_exwork': {
        'name': 'Charge',
        'unit_description': 'Unit',
        'amount': 'Amount',
    },
    'air_local': {
        'name': 'Charge',
        'unit_description': 'Unit',
        'amount': 'Amount',
    },
}


def _check_section_matches_layout(record, allowed_sections_by_layout, section_labels):
    layout = record.job_id.quotation_layout or record.layout
    if not layout or not record.section_code:
        return
    allowed_sections = allowed_sections_by_layout.get(layout, set())
    if record.section_code in allowed_sections:
        return
    raise ValidationError(
        'Section "%s" cannot be used for quotation layout "%s".'
        % (
            section_labels.get(record.section_code, record.section_code),
            LAYOUT_LABELS.get(layout, layout),
        )
    )


def _get_context_section_code(recordset):
    return (
        recordset.env.context.get('quote_section_code')
        or recordset.env.context.get('default_section_code')
        or (recordset.section_code if len(recordset) == 1 else False)
    )


def _apply_contextual_field_labels(fields_meta, section_code, labels_by_section):
    if not section_code:
        return fields_meta
    for field_name, label in labels_by_section.get(section_code, {}).items():
        if field_name in fields_meta:
            fields_meta[field_name]['string'] = label
    return fields_meta


class LogisticsJobQuoteRateLine(models.Model):
    _name = 'logistics.job.quote.rate.line'
    _description = 'Logistics Job Quotation Rate Line'
    _order = 'job_id, section_code, sequence, id'

    job_id = fields.Many2one(
        'logistics.job', string='Job',
        required=True, ondelete='cascade',
    )
    layout = fields.Selection(related='job_id.quotation_layout', store=True, readonly=True)
    section_code = fields.Selection(
        RATE_SECTION_SELECTION,
        string='Section',
        required=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Name', required=True)
    origin_code = fields.Char(string='Origin Code')
    destination_code = fields.Char(string='Destination Code')
    carrier_or_party = fields.Char(string='Carrier / Party')
    transit_time = fields.Char(string='Transit Time')
    frequency = fields.Char(string='Frequency')
    note = fields.Char(string='Note')
    currency_id = fields.Many2one(
        related='job_id.currency_id',
        store=True,
        readonly=True,
    )
    amount_1 = fields.Monetary(string='Amount 1', currency_field='currency_id')
    amount_2 = fields.Monetary(string='Amount 2', currency_field='currency_id')
    amount_3 = fields.Monetary(string='Amount 3', currency_field='currency_id')
    amount_4 = fields.Monetary(string='Amount 4', currency_field='currency_id')
    amount_5 = fields.Monetary(string='Amount 5', currency_field='currency_id')
    amount_6 = fields.Monetary(string='Amount 6', currency_field='currency_id')
    amount_total = fields.Monetary(
        string='Total',
        currency_field='currency_id',
        compute='_compute_amount_total',
        store=True,
    )

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        fields_meta = super().fields_get(allfields=allfields, attributes=attributes)
        return _apply_contextual_field_labels(
            fields_meta,
            _get_context_section_code(self),
            RATE_FIELD_LABELS_BY_SECTION,
        )

    @api.depends('amount_1', 'amount_2', 'amount_3', 'amount_4', 'amount_5', 'amount_6')
    def _compute_amount_total(self):
        for line in self:
            line.amount_total = sum((
                line.amount_1 or 0.0,
                line.amount_2 or 0.0,
                line.amount_3 or 0.0,
                line.amount_4 or 0.0,
                line.amount_5 or 0.0,
                line.amount_6 or 0.0,
            ))

    @api.constrains('job_id', 'layout', 'section_code')
    def _check_section_code_matches_layout(self):
        for line in self:
            _check_section_matches_layout(
                line,
                RATE_SECTIONS_BY_LAYOUT,
                RATE_SECTION_LABELS,
            )


class LogisticsJobQuoteChargeLine(models.Model):
    _name = 'logistics.job.quote.charge.line'
    _description = 'Logistics Job Quotation Charge Line'
    _order = 'job_id, section_code, sequence, id'

    job_id = fields.Many2one(
        'logistics.job', string='Job',
        required=True, ondelete='cascade',
    )
    layout = fields.Selection(related='job_id.quotation_layout', store=True, readonly=True)
    section_code = fields.Selection(
        CHARGE_SECTION_SELECTION,
        string='Section',
        required=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Name', required=True)
    unit_description = fields.Char(string='Unit Description')
    currency_id = fields.Many2one(
        related='job_id.currency_id',
        store=True,
        readonly=True,
    )
    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    amount_20dc = fields.Monetary(string="20'DC", currency_field='currency_id')
    amount_40hc = fields.Monetary(string="40'HC", currency_field='currency_id')
    amount_cbm_low = fields.Monetary(string='1-3 CBM', currency_field='currency_id')
    amount_cbm_mid = fields.Monetary(string='3-5 CBM', currency_field='currency_id')
    amount_cbm_high = fields.Monetary(string='5-10 CBM', currency_field='currency_id')
    remark = fields.Char(string='Remark')
    include_in_total = fields.Boolean(string='Include in Total')

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        fields_meta = super().fields_get(allfields=allfields, attributes=attributes)
        return _apply_contextual_field_labels(
            fields_meta,
            _get_context_section_code(self),
            CHARGE_FIELD_LABELS_BY_SECTION,
        )

    @api.constrains('job_id', 'layout', 'section_code')
    def _check_section_code_matches_layout(self):
        for line in self:
            _check_section_matches_layout(
                line,
                CHARGE_SECTIONS_BY_LAYOUT,
                CHARGE_SECTION_LABELS,
            )
