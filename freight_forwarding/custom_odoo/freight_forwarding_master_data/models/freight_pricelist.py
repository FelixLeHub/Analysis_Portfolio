from odoo import api, fields, models


class FreightPricelist(models.Model):
    _name = 'master.freight.pricelist'
    _description = 'Freight Pricelist'
    _order = 'partner_id, service_type_id'

    partner_id = fields.Many2one('res.partner', string='Partner Name', required=True)
    partner_type = fields.Selection([
        ('carrier', 'Carrier'),
        ('agent', 'Agent'),
    ], string='Carrier / Agent', required=True, default='carrier')
    lead_id = fields.Many2one('crm.lead', string='Lead')
    service_type_id = fields.Many2one('master.service.type', string='Service Type')
    service_type_code = fields.Char(related='service_type_id.code', store=True)
    display_mode = fields.Char(compute='_compute_display_mode')
    is_carrier = fields.Boolean(compute='_compute_display_mode')
    is_agent = fields.Boolean(compute='_compute_display_mode')
    pol_id = fields.Many2one('master.port.airport', string='POL/AOL')
    pod_id = fields.Many2one('master.port.airport', string='POD/AOD')
    valid_to = fields.Date(string='Valid To')
    freq = fields.Char(string='Freq')
    tt = fields.Char(string='TT')
    active = fields.Boolean(default=True)

    @api.depends('service_type_code', 'partner_type')
    def _compute_display_mode(self):
        for rec in self:
            rec.display_mode = '%s_%s' % (rec.service_type_code or '', rec.partner_type or '')
            rec.is_carrier = rec.partner_type == 'carrier'
            rec.is_agent = rec.partner_type == 'agent'

    # FCL sections
    fcl_line_ids = fields.One2many('master.freight.pricelist.fcl', 'pricelist_id', string='FCL Rates')
    fcl_ocean_rate_ids = fields.One2many(
        'master.freight.pricelist.fcl', 'pricelist_id',
        string='Ocean Rate', domain=[('section', '=', 'ocean_rate')])
    fcl_local_charge_ids = fields.One2many(
        'master.freight.pricelist.fcl', 'pricelist_id',
        string='Local Charge', domain=[('section', '=', 'local_charge')])
    fcl_exw_fee_ids = fields.One2many(
        'master.freight.pricelist.fcl', 'pricelist_id',
        string='Exw Fee', domain=[('section', '=', 'exw_fee')])

    # LCL sections
    lcl_line_ids = fields.One2many('master.freight.pricelist.lcl', 'pricelist_id', string='LCL Rates')
    lcl_rate_ids = fields.One2many(
        'master.freight.pricelist.lcl', 'pricelist_id',
        string='LCL Rate', domain=[('section', '=', 'lcl_rate')])
    lcl_exw_fee_ids = fields.One2many(
        'master.freight.pricelist.lcl', 'pricelist_id',
        string='LCL Exw Fee', domain=[('section', '=', 'lcl_exw_fee')])
    lcl_local_charge_ids = fields.One2many(
        'master.freight.pricelist.lcl', 'pricelist_id',
        string='LCL Local Charge', domain=[('section', '=', 'lcl_local_charge')])
    lcl_fcl_local_charge_ids = fields.One2many(
        'master.freight.pricelist.lcl', 'pricelist_id',
        string='FCL Local Charge', domain=[('section', '=', 'fcl_local_charge')])

    # Air sections
    air_line_ids = fields.One2many('master.freight.pricelist.air', 'pricelist_id', string='Air Rates')
    air_local_charge_ids = fields.One2many(
        'master.freight.pricelist.charge', 'pricelist_id',
        string='Air Local Charge', domain=[('section', '=', 'air_local_charge')])
    air_exw_fee_ids = fields.One2many(
        'master.freight.pricelist.charge', 'pricelist_id',
        string='Air Exw Fee', domain=[('section', '=', 'air_exw_fee')])

    # Trucking sections
    trucking_line_ids = fields.One2many(
        'master.freight.pricelist.trucking', 'pricelist_id',
        string='Trucking Carrier Rates', domain=[('section', '=', 'carrier')])
    trucking_agent_line_ids = fields.One2many(
        'master.freight.pricelist.trucking', 'pricelist_id',
        string='Trucking Agent Rates', domain=[('section', '=', 'agent')])
    trucking_surcharge_ids = fields.One2many(
        'master.freight.pricelist.charge', 'pricelist_id',
        string='Trucking Surcharge', domain=[('section', '=', 'trucking_surcharge')])


class FreightPricelistFCL(models.Model):
    _name = 'master.freight.pricelist.fcl'
    _description = 'Freight Pricelist FCL Line'

    pricelist_id = fields.Many2one('master.freight.pricelist', ondelete='cascade', required=True)
    section = fields.Selection([
        ('ocean_rate', 'Ocean Rate'),
        ('local_charge', 'Local Charge'),
        ('exw_fee', 'Exw Fee'),
    ], string='Section', required=True, default='ocean_rate')
    name = fields.Char(string='Name')
    rates = fields.Float(string='Rates')
    units = fields.Selection([
        ('cbm', 'CBM'),
        ('rt', 'RT'),
        ('cwt', 'CWT'),
        ('shmt', 'SHMT'),
        ('bl', 'B/L'),
        ('20dc', '20 DC'),
        ('40hc', '40 HC'),
    ], string='Units')


class FreightPricelistLCL(models.Model):
    _name = 'master.freight.pricelist.lcl'
    _description = 'Freight Pricelist LCL Line'

    pricelist_id = fields.Many2one('master.freight.pricelist', ondelete='cascade', required=True)
    section = fields.Selection([
        ('lcl_rate', 'LCL Rate'),
        ('lcl_exw_fee', 'LCL Exw Fee'),
        ('lcl_local_charge', 'LCL Local Charge'),
        ('fcl_local_charge', 'FCL Local Charge'),
    ], string='Section', required=True, default='lcl_rate')
    pol_id = fields.Many2one('master.port.airport', string='POL')
    pod_id = fields.Many2one('master.port.airport', string='POD')
    rates_name = fields.Char(string='Rates Name')
    rates = fields.Float(string='Rates')
    units = fields.Selection([
        ('cbm', 'CBM'),
        ('rt', 'RT'),
        ('cwt', 'CWT'),
        ('shmt', 'SHMT'),
        ('bl', 'B/L'),
        ('20dc', '20 DC'),
        ('40hc', '40 HC'),
    ], string='Units')


class FreightPricelistAir(models.Model):
    _name = 'master.freight.pricelist.air'
    _description = 'Freight Pricelist Air Line'

    pricelist_id = fields.Many2one('master.freight.pricelist', ondelete='cascade', required=True)
    name = fields.Char(string='Name')
    kg_minus_45 = fields.Float(string='- 45 kgs')
    kg_plus_45 = fields.Float(string='+ 45 kgs')
    kg_plus_100 = fields.Float(string='+ 100 kgs')
    kg_plus_300 = fields.Float(string='+ 300 kgs')
    kg_plus_500 = fields.Float(string='+ 500 kgs')
    kg_plus_1000 = fields.Float(string='+ 1000 kgs')
    units = fields.Selection([
        ('cbm', 'CBM'),
        ('rt', 'RT'),
        ('cwt', 'CWT'),
        ('shmt', 'SHMT'),
        ('bl', 'B/L'),
        ('20dc', '20 DC'),
        ('40hc', '40 HC'),
    ], string='Units')


class FreightPricelistTrucking(models.Model):
    _name = 'master.freight.pricelist.trucking'
    _description = 'Freight Pricelist Trucking Line'

    pricelist_id = fields.Many2one('master.freight.pricelist', ondelete='cascade', required=True)
    section = fields.Selection([
        ('carrier', 'Carrier'),
        ('agent', 'Agent'),
    ], string='Section', required=True, default='carrier')
    name = fields.Char(string='Name')
    units = fields.Selection([
        ('cbm', 'CBM'),
        ('rt', 'RT'),
        ('cwt', 'CWT'),
        ('shmt', 'SHMT'),
        ('bl', 'B/L'),
        ('20dc', '20 DC'),
        ('40hc', '40 HC'),
    ], string='Units')
    truck_1_5t = fields.Float(string='Truck 1.5 tons')
    truck_3_5t = fields.Float(string='Truck 3.5 tons')
    truck_5t = fields.Float(string='Truck 5 tons')
    cbm_1_3 = fields.Float(string='1-3 cbms')
    cbm_3_5 = fields.Float(string='3-5 cbms')
    cbm_5_10 = fields.Float(string='5-10 cbms')
    dc_20 = fields.Float(string='20 DC')
    dc_40 = fields.Float(string='40 DC')


class FreightPricelistCharge(models.Model):
    _name = 'master.freight.pricelist.charge'
    _description = 'Freight Pricelist Charge Line'

    pricelist_id = fields.Many2one('master.freight.pricelist', ondelete='cascade', required=True)
    section = fields.Selection([
        ('air_local_charge', 'Air Local Charge'),
        ('air_exw_fee', 'Air Exw Fee'),
        ('trucking_surcharge', 'Trucking Surcharge'),
    ], string='Section', required=True)
    name = fields.Char(string='Name')
    rates = fields.Float(string='Rates')
    units = fields.Selection([
        ('cbm', 'CBM'),
        ('rt', 'RT'),
        ('cwt', 'CWT'),
        ('shmt', 'SHMT'),
        ('bl', 'B/L'),
        ('20dc', '20 DC'),
        ('40hc', '40 HC'),
    ], string='Units')
