from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .logistics_job_quote import (
    CHARGE_SECTION_LABELS,
    CHARGE_SECTIONS_BY_LAYOUT,
    RATE_SECTION_LABELS,
    RATE_SECTIONS_BY_LAYOUT,
)


QUOTATION_LAYOUT_SELECTION = [
    ('trucking_customs', 'Trucking and Customs'),
    ('sea_lcl', 'LCL Rate'),
    ('sea_fcl', 'Seafreight'),
    ('air', 'Airfreight'),
]

QUOTATION_LAYOUT_LABELS = dict(QUOTATION_LAYOUT_SELECTION)

DIRECTION_SELECTION = [
    ('export', 'Export'),
    ('import', 'Import'),
]

INCOTERM_SELECTION = [
    ('EXW', 'EXW'),
    ('FCA', 'FCA'),
    ('FAS', 'FAS'),
    ('FOB', 'FOB'),
    ('CFR', 'CFR'),
    ('CIF', 'CIF'),
    ('CPT', 'CPT'),
    ('CIP', 'CIP'),
    ('DAP', 'DAP'),
    ('DPU', 'DPU'),
    ('DDP', 'DDP'),
]

SERVICE_MODE_SELECTION = [
    ('fcl', 'FCL'),
    ('lcl', 'LCL'),
    ('air', 'Air'),
    ('trucking', 'Trucking'),
]

SERVICE_MODE_BY_SERVICE_TYPE = {
    'sea_fcl_import': 'fcl',
    'sea_fcl_export': 'fcl',
    'sea_lcl': 'lcl',
    'air': 'air',
    'trucking': 'trucking',
}

SERVICE_TYPE_BY_SERVICE_MODE = {
    'lcl': 'sea_lcl',
    'air': 'air',
    'trucking': 'trucking',
}

DIRECTION_BY_SERVICE_TYPE = {
    'sea_fcl_import': 'import',
    'sea_fcl_export': 'export',
    'sea_lcl': 'export',
    'air': 'export',
    'trucking': 'export',
}


class LogisticsJob(models.Model):
    _name = 'logistics.job'
    _description = 'Logistics Job'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Job No',
        required=True, copy=False, readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('logistics.job') or 'New',
    )
    state = fields.Selection([
        ('quotation', 'Quotation'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='quotation', tracking=True)

    # === Service Type ===
    service_type = fields.Selection([
        ('sea_fcl_import', 'Sea FCL Import'),
        ('sea_fcl_export', 'Sea FCL Export'),
        ('sea_lcl', 'Sea LCL'),
        ('air', 'Air'),
        ('trucking', 'Trucking'),
    ], string='Service Type', required=True, tracking=True)
    direction = fields.Selection(
        DIRECTION_SELECTION,
        string='Direction',
        default='export',
        tracking=True,
    )
    service_mode = fields.Selection(
        SERVICE_MODE_SELECTION,
        string='Service Mode',
        tracking=True,
    )
    quotation_layout = fields.Selection(
        QUOTATION_LAYOUT_SELECTION,
        string='Quotation Layout',
        tracking=True,
    )
    pricelist_id = fields.Many2one(
        'master.freight.pricelist',
        string='Freight Pricelist',
    )
    subject = fields.Char(string='Subject')
    attention_to = fields.Char(string='To')
    pic_name = fields.Char(string='PIC')
    valid_until = fields.Date(string='Valid Until')
    routing_summary = fields.Char(string='Routing Summary')
    volume_summary = fields.Char(string='Volume Summary')
    vat_percent = fields.Float(string='VAT %', default=10.0)
    quotation_intro = fields.Text(string='Quotation Intro')
    quotation_footer_note = fields.Text(string='Footer Note')
    quotation_review_html = fields.Html(
        string='Quotation Review',
        compute='_compute_quotation_review_html',
        sanitize=False,
    )
    salesperson_name = fields.Char(
        string='Salesperson',
        default=lambda self: self._get_default_salesperson_values()['salesperson_name'],
        copy=False,
    )
    salesperson_email = fields.Char(
        string='Salesperson Email',
        default=lambda self: self._get_default_salesperson_values()['salesperson_email'],
        copy=False,
    )
    salesperson_phone = fields.Char(
        string='Salesperson Phone',
        default=lambda self: self._get_default_salesperson_values()['salesperson_phone'],
        copy=False,
    )

    # === CRM Lead Link ===
    lead_id = fields.Many2one(
        'crm.lead', string='Lead', ondelete='set null', tracking=True,
        help='CRM lead that originated this freight job',
    )

    # === Parties ===
    customer_id = fields.Many2one(
        'res.partner', string='Customer', required=True, tracking=True,
        help='Khách hàng của Freight_Forwarding',
    )
    customer_ref = fields.Char(string='Customer Account No')
    shipper_id = fields.Many2one('res.partner', string='Shipper', tracking=True)
    consignee_id = fields.Many2one('res.partner', string='Consignee', tracking=True)
    notify_party_id = fields.Many2one('res.partner', string='Notify Party')
    agent_id = fields.Many2one(
        'res.partner', string='Agent',
        help='Đại lý nước ngoài (Atlas, ACP, MSL, ANB, TGL, UNITEX, SMOOTH...)',
    )
    shipping_line_id = fields.Many2one('res.partner', string='Shipping Line / Airline')

    # === Bill of Lading (Sea) ===
    mbl_no = fields.Char(string='Master B/L No')
    hbl_no = fields.Char(string='House B/L No')

    # === Air Waybill (Air) ===
    mawb_no = fields.Char(string='MAWB No')
    hawb_no = fields.Char(string='HAWB No')

    # === Transport Info ===
    vessel_name = fields.Char(string='Vessel Name')
    voyage_no = fields.Char(string='Voyage No')
    flight_no = fields.Char(string='Flight No')
    factory_name = fields.Char(string='Factory')
    pol = fields.Char(string='Port/Airport of Loading')
    pod = fields.Char(string='Port/Airport of Discharge')
    place_of_delivery = fields.Char(string='Place of Delivery')

    # === Dates ===
    etd = fields.Date(string='ETD')
    eta = fields.Date(string='ETA')
    arrival_date = fields.Date(string='Arrival Date')

    # === Cargo Info ===
    commodity = fields.Char(string='Commodity')
    hs_code = fields.Char(string='HS Code')
    package_count = fields.Integer(string='No. of Packages')
    weight_kgs = fields.Float(string='Weight (KGS)')
    gross_weight = fields.Float(string='Gross Weight (KG)')
    chargeable_weight = fields.Float(string='Chargeable Weight (KG)')
    volume_cbm = fields.Float(string='Volume (CBM)')
    volume_weight_363 = fields.Float(
        string='1:363 (KGS)',
        compute='_compute_volume_weight_363',
    )

    # === Terms ===
    freight_terms = fields.Selection([
        ('prepaid', 'Prepaid'),
        ('collect', 'Collect'),
    ], string='Freight Terms')
    incoterms = fields.Selection(INCOTERM_SELECTION, string='Incoterm', tracking=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.ref('base.USD', raise_if_not_found=False),
    )
    exchange_rate = fields.Float(string='Exchange Rate', digits=(12, 4))

    # === Containers ===
    container_ids = fields.One2many('logistics.container', 'job_id', string='Containers')
    quote_rate_line_ids = fields.One2many(
        'logistics.job.quote.rate.line', 'job_id', string='Quotation Rate Lines',
    )
    quote_charge_line_ids = fields.One2many(
        'logistics.job.quote.charge.line', 'job_id', string='Quotation Charge Lines',
    )
    truck_rate_line_ids = fields.One2many(
        'logistics.job.quote.rate.line',
        'job_id',
        string='Trucking Rate Lines',
        domain=[('section_code', '=', 'truck_rate')],
    )
    customs_import_line_ids = fields.One2many(
        'logistics.job.quote.rate.line',
        'job_id',
        string='Import Customs Lines',
        domain=[('section_code', '=', 'customs_import')],
    )
    customs_export_line_ids = fields.One2many(
        'logistics.job.quote.rate.line',
        'job_id',
        string='Export Customs Lines',
        domain=[('section_code', '=', 'customs_export')],
    )
    lcl_rate_line_ids = fields.One2many(
        'logistics.job.quote.rate.line',
        'job_id',
        string='LCL Rate Lines',
        domain=[('section_code', '=', 'lcl_rate')],
    )
    fcl_ocean_line_ids = fields.One2many(
        'logistics.job.quote.rate.line',
        'job_id',
        string='FCL Ocean Rate Lines',
        domain=[('section_code', '=', 'fcl_ocean')],
    )
    air_rate_line_ids = fields.One2many(
        'logistics.job.quote.rate.line',
        'job_id',
        string='Air Rate Lines',
        domain=[('section_code', '=', 'air_rate')],
    )
    lcl_exwork_line_ids = fields.One2many(
        'logistics.job.quote.charge.line',
        'job_id',
        string='LCL Ex-work Lines',
        domain=[('section_code', '=', 'lcl_exwork')],
    )
    lcl_local_lcl_line_ids = fields.One2many(
        'logistics.job.quote.charge.line',
        'job_id',
        string='LCL Local Charge Lines',
        domain=[('section_code', '=', 'lcl_local_lcl')],
    )
    fcl_local_line_ids = fields.One2many(
        'logistics.job.quote.charge.line',
        'job_id',
        string='FCL Local Charge Lines',
        domain=[('section_code', '=', 'fcl_local')],
    )
    fcl_exwork_line_ids = fields.One2many(
        'logistics.job.quote.charge.line',
        'job_id',
        string='FCL Ex-work Lines',
        domain=[('section_code', '=', 'fcl_exwork')],
    )
    air_exwork_line_ids = fields.One2many(
        'logistics.job.quote.charge.line',
        'job_id',
        string='Air Ex-work Lines',
        domain=[('section_code', '=', 'air_exwork')],
    )
    air_local_line_ids = fields.One2many(
        'logistics.job.quote.charge.line',
        'job_id',
        string='Air Local Charge Lines',
        domain=[('section_code', '=', 'air_local')],
    )
    container_count = fields.Integer(
        compute='_compute_related_counts', string='Container Count',
    )

    # === Debit Notes ===
    agent_debit_note_ids = fields.One2many(
        'logistics.agent.debit.note', 'job_id', string='Agent Debit Notes',
    )
    agent_debit_note_count = fields.Integer(
        compute='_compute_related_counts', string='Agent DN',
    )
    customer_debit_note_ids = fields.One2many(
        'logistics.customer.debit.note', 'job_id', string='Customer Debit Notes',
    )
    customer_debit_note_count = fields.Integer(
        compute='_compute_related_counts', string='Customer DN',
    )
    account_move_ids = fields.One2many(
        'account.move', 'logistics_job_id', string='Journal Entries',
    )
    account_move_count = fields.Integer(
        compute='_compute_related_counts', string='Invoices',
    )

    notes = fields.Html(string='Notes')

    # === Computed fields ===
    is_sea = fields.Boolean(compute='_compute_transport_flags', store=True)
    is_air = fields.Boolean(compute='_compute_transport_flags', store=True)

    def init(self):
        self._cr.execute("""
            UPDATE logistics_job
               SET service_mode = CASE service_type
                    WHEN 'sea_fcl_import' THEN 'fcl'
                    WHEN 'sea_fcl_export' THEN 'fcl'
                    WHEN 'sea_lcl' THEN 'lcl'
                    WHEN 'air' THEN 'air'
                    WHEN 'trucking' THEN 'trucking'
                END
             WHERE service_type IS NOT NULL
               AND service_mode IS NULL
        """)
        self._cr.execute("""
            UPDATE logistics_job
               SET direction = CASE service_type
                    WHEN 'sea_fcl_import' THEN 'import'
                    ELSE 'export'
                END
             WHERE service_type IS NOT NULL
               AND direction IS NULL
        """)

    @api.model
    def _get_default_salesperson_values(self):
        partner = self.env.user.partner_id
        return {
            'salesperson_name': self.env.user.name,
            'salesperson_email': partner.email,
            'salesperson_phone': getattr(partner, 'mobile', False)
            or getattr(partner, 'phone', False),
        }

    @api.depends('service_type')
    def _compute_transport_flags(self):
        for rec in self:
            rec.is_sea = rec.service_type in ('sea_fcl_import', 'sea_fcl_export', 'sea_lcl')
            rec.is_air = rec.service_type == 'air'

    @api.depends('volume_cbm')
    def _compute_volume_weight_363(self):
        for rec in self:
            rec.volume_weight_363 = (rec.volume_cbm or 0.0) * 363.0

    @api.depends('quotation_layout')
    def _compute_quotation_review_html(self):
        for rec in self:
            try:
                preview_url = rec._get_quotation_review_url()
            except UserError:
                rec.quotation_review_html = False
                continue
            rec.quotation_review_html = Markup(
                '<div class="o_freight_forwarding_quote_review_frame">'
                '<iframe src="%s" title="%s"></iframe>'
                '</div>'
            ) % (
                escape(preview_url),
                escape(_('Quotation Preview')),
            )

    @api.model
    def _get_service_mode_from_service_type(self, service_type):
        return SERVICE_MODE_BY_SERVICE_TYPE.get(service_type)

    @api.model
    def _get_default_direction_from_service_type(self, service_type, current_direction=False):
        if service_type in ('sea_fcl_import', 'sea_fcl_export'):
            return DIRECTION_BY_SERVICE_TYPE[service_type]
        return current_direction or DIRECTION_BY_SERVICE_TYPE.get(service_type) or 'export'

    @api.model
    def _get_service_type_from_system_fields(self, service_mode, direction=False):
        if not service_mode:
            return False
        if service_mode == 'fcl':
            return 'sea_fcl_import' if direction == 'import' else 'sea_fcl_export'
        return SERVICE_TYPE_BY_SERVICE_MODE.get(service_mode)

    @api.model
    def _get_default_quotation_layout(self, service_type):
        layout_map = {
            'trucking': 'trucking_customs',
            'sea_lcl': 'sea_lcl',
            'sea_fcl_import': 'sea_fcl',
            'sea_fcl_export': 'sea_fcl',
            'air': 'air',
        }
        return layout_map.get(service_type)

    @api.model
    def _get_default_service_type_from_layout(self, quotation_layout, direction=False):
        service_type_map = {
            'trucking_customs': 'trucking',
            'sea_lcl': 'sea_lcl',
            'air': 'air',
        }
        if quotation_layout == 'sea_fcl':
            return 'sea_fcl_import' if direction == 'import' else 'sea_fcl_export'
        return service_type_map.get(quotation_layout)

    @api.model
    def _sync_system_field_values(self, vals, record=False):
        values = dict(vals)
        has_service_mode = 'service_mode' in values
        has_direction = 'direction' in values
        has_service_type = 'service_type' in values
        has_quotation_layout = 'quotation_layout' in values

        current_service_mode = values.get('service_mode') if has_service_mode else record.service_mode if record else False
        current_direction = values.get('direction') if has_direction else record.direction if record else False

        if has_service_mode or (has_direction and not has_service_type and not has_quotation_layout):
            if current_service_mode and not current_direction:
                current_direction = 'export'
                values['direction'] = current_direction

            service_type = self._get_service_type_from_system_fields(current_service_mode, current_direction)
            if service_type:
                values['service_type'] = service_type
                if not values.get('quotation_layout'):
                    quotation_layout = self._get_default_quotation_layout(service_type)
                    if quotation_layout:
                        values['quotation_layout'] = quotation_layout

        elif values.get('quotation_layout') and not values.get('service_type'):
            service_type = self._get_default_service_type_from_layout(
                values.get('quotation_layout'),
                direction=current_direction,
            )
            if service_type:
                values['service_type'] = service_type

        service_type = values.get('service_type')
        if not service_type and record and not has_service_type:
            service_type = record.service_type

        if service_type and not values.get('quotation_layout'):
            quotation_layout = self._get_default_quotation_layout(service_type)
            if quotation_layout:
                values['quotation_layout'] = quotation_layout

        if service_type and not values.get('service_mode'):
            values['service_mode'] = self._get_service_mode_from_service_type(service_type)
        if service_type and not values.get('direction'):
            values['direction'] = self._get_default_direction_from_service_type(
                service_type,
                current_direction,
            )

        return values

    @api.depends('container_ids', 'agent_debit_note_ids', 'customer_debit_note_ids', 'account_move_ids')
    def _compute_related_counts(self):
        for rec in self:
            rec.container_count = len(rec.container_ids)
            rec.agent_debit_note_count = len(rec.agent_debit_note_ids)
            rec.customer_debit_note_count = len(rec.customer_debit_note_ids)
            rec.account_move_count = len(rec.account_move_ids)

    @api.onchange('service_type')
    def _onchange_service_type_quotation_layout(self):
        for rec in self:
            if rec.service_type:
                rec.quotation_layout = rec._get_default_quotation_layout(rec.service_type)
                rec.service_mode = rec._get_service_mode_from_service_type(rec.service_type)
                rec.direction = rec._get_default_direction_from_service_type(rec.service_type, rec.direction)

    @api.onchange('quotation_layout')
    def _onchange_quotation_layout_service_type(self):
        warning = False
        for rec in self:
            message = rec._get_layout_change_conflict_message(rec.quotation_layout)
            if message:
                rec.quotation_layout = rec._origin.quotation_layout if rec._origin else False
                if rec._origin and rec._origin.service_type:
                    rec.service_type = rec._origin.service_type
                warning = {
                    'title': _('Incompatible quotation lines'),
                    'message': message,
                }
                continue
            default_service_type = rec._get_default_service_type_from_layout(
                rec.quotation_layout,
                direction=rec.direction,
            )
            if default_service_type:
                rec.service_type = default_service_type
                rec.service_mode = rec._get_service_mode_from_service_type(default_service_type)
                rec.direction = rec._get_default_direction_from_service_type(default_service_type, rec.direction)
        if warning:
            return {'warning': warning}

    @api.onchange('service_mode', 'direction')
    def _onchange_system_fields(self):
        for rec in self:
            service_type = rec._get_service_type_from_system_fields(rec.service_mode, rec.direction)
            if service_type:
                rec.service_type = service_type

    @api.onchange('customer_id')
    def _onchange_customer_id_quotation_contact(self):
        for rec in self:
            if rec.customer_id and not rec.attention_to:
                rec.attention_to = rec.customer_id.name

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        return self._sync_system_field_values(values)

    def _get_incompatible_quote_section_labels(self, quotation_layout):
        self.ensure_one()
        allowed_rate_sections = RATE_SECTIONS_BY_LAYOUT.get(quotation_layout, set())
        allowed_charge_sections = CHARGE_SECTIONS_BY_LAYOUT.get(quotation_layout, set())
        incompatible_labels = []

        for section_code in sorted(set(self.quote_rate_line_ids.mapped('section_code')) - allowed_rate_sections):
            incompatible_labels.append(RATE_SECTION_LABELS.get(section_code, section_code))
        for section_code in sorted(set(self.quote_charge_line_ids.mapped('section_code')) - allowed_charge_sections):
            incompatible_labels.append(CHARGE_SECTION_LABELS.get(section_code, section_code))

        return incompatible_labels

    def _get_layout_change_conflict_message(self, quotation_layout):
        self.ensure_one()
        if not quotation_layout or quotation_layout == self.quotation_layout:
            return False
        incompatible_sections = self._get_incompatible_quote_section_labels(quotation_layout)
        if not incompatible_sections:
            return False
        return _(
            'Cannot change quotation layout to "%(layout)s" because this quotation still contains lines for: %(sections)s. Remove those lines first, then change the layout.'
        ) % {
            'layout': QUOTATION_LAYOUT_LABELS.get(quotation_layout, quotation_layout),
            'sections': ', '.join(incompatible_sections),
        }

    def _check_layout_change_conflicts(self, quotation_layout):
        for rec in self:
            message = rec._get_layout_change_conflict_message(quotation_layout)
            if message:
                raise UserError(message)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            for field_name, default_value in self._get_default_salesperson_values().items():
                if not vals.get(field_name):
                    vals[field_name] = default_value
            vals.update(self._sync_system_field_values(vals))
        return super().create(vals_list)

    def write(self, vals):
        sync_fields = {'direction', 'quotation_layout', 'service_mode', 'service_type'}
        if sync_fields.intersection(vals):
            for rec in self:
                synced_vals = rec._sync_system_field_values(vals, record=rec)
                rec._check_layout_change_conflicts(synced_vals.get('quotation_layout'))
                super(LogisticsJob, rec).write(synced_vals)
            return True

        vals = dict(vals)
        self._check_layout_change_conflicts(vals.get('quotation_layout'))
        return super().write(vals)

    # === State Actions ===
    def action_confirm(self):
        self.write({'state': 'confirmed'})
        if len(self) == 1:
            return self.action_open_operations_form()

    def action_in_progress(self):
        self.write({'state': 'in_progress'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_quotation(self):
        self.write({'state': 'quotation'})
        if len(self) == 1:
            return self.action_open_quotation_form()

    def _action_open_specific_form(self, view_xmlid, action_name):
        self.ensure_one()
        view = self.env.ref(view_xmlid)
        return {
            'type': 'ir.actions.act_window',
            'name': action_name,
            'res_model': 'logistics.job',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': view.id,
            'views': [(view.id, 'form')],
            'target': 'current',
        }

    def action_open_quotation_form(self):
        return self._action_open_specific_form(
            'freight_forwarding_freight.view_logistics_job_quotation_form',
            _('Quotation'),
        )

    def action_import_pricelist_rates(self):
        self.ensure_one()
        pricelist = self.pricelist_id
        if not pricelist:
            raise UserError(_('Please select a Freight Pricelist first.'))

        UNITS_LABEL = {
            'cbm': 'CBM', 'rt': 'RT', 'cwt': 'CWT', 'shmt': 'SHMT',
            'bl': 'B/L', '20dc': '20 DC', '40hc': '40 HC',
        }
        service_code = pricelist.service_type_code

        if service_code == 'lcl':
            for line in pricelist.lcl_line_ids:
                self.env['logistics.job.quote.charge.line'].create({
                    'job_id': self.id,
                    'section_code': 'lcl_exwork',
                    'name': line.rates_name or '/',
                    'amount': line.rates,
                    'unit_description': UNITS_LABEL.get(line.units, line.units or ''),
                })
        elif service_code == 'fcl':
            for line in pricelist.fcl_line_ids:
                self.env['logistics.job.quote.rate.line'].create({
                    'job_id': self.id,
                    'section_code': 'fcl_ocean',
                    'name': '%s - %s' % (line.pol_id.name or '', line.pod_id.name or ''),
                    'origin_code': line.pol_id.code or '',
                    'destination_code': line.pod_id.code or '',
                    'amount_1': line.of_rates,
                    'note': UNITS_LABEL.get(line.units, line.units or ''),
                })
        elif service_code == 'air':
            for line in pricelist.air_line_ids:
                self.env['logistics.job.quote.rate.line'].create({
                    'job_id': self.id,
                    'section_code': 'air_rate',
                    'name': '%s - %s' % (line.aol_id.name or '', line.aod_id.name or ''),
                    'origin_code': line.aol_id.code or '',
                    'destination_code': line.aod_id.code or '',
                    'amount_1': line.kg_minus_45,
                    'amount_2': line.kg_plus_45,
                    'amount_3': line.kg_plus_100,
                    'amount_4': line.kg_plus_300,
                    'amount_5': line.kg_plus_500,
                    'amount_6': line.kg_plus_1000,
                })
        elif service_code == 'trucking':
            for line in pricelist.trucking_line_ids:
                self.env['logistics.job.quote.rate.line'].create({
                    'job_id': self.id,
                    'section_code': 'truck_rate',
                    'name': '/',
                    'amount_1': line.truck_1_5t,
                    'amount_2': line.truck_3_5t,
                    'amount_3': line.truck_5t,
                    'amount_4': line.dc_20,
                    'amount_5': line.dc_40,
                })

        self.pricelist_id = False
        return True

    def action_open_operations_form(self):
        return self._action_open_specific_form(
            'freight_forwarding_freight.view_logistics_job_operation_form',
            _('Operations Job'),
        )

    def _get_quotation_report_definition(self):
        self.ensure_one()
        report_map = {
            'trucking_customs': 'freight_forwarding_freight.action_report_logistics_job_quotation_trucking_customs',
            'sea_lcl': 'freight_forwarding_freight.action_report_logistics_job_quotation_sea_lcl',
            'sea_fcl': 'freight_forwarding_freight.action_report_logistics_job_quotation_sea_fcl',
            'air': 'freight_forwarding_freight.action_report_logistics_job_quotation_air',
        }
        report_xmlid = report_map.get(self.quotation_layout)
        if not report_xmlid:
            raise UserError(_('Please choose a quotation layout before printing.'))
        return self.env.ref(report_xmlid)

    def _get_quotation_review_url(self):
        self.ensure_one()
        report = self._get_quotation_report_definition()
        return '/report/html/%s/%s' % (report.report_name, self.id)

    def action_print_quotation(self):
        self.ensure_one()
        self._get_quotation_report_definition()
        return self._action_open_specific_form(
            'freight_forwarding_freight.view_logistics_job_quotation_review_form',
            _('Quotation Review'),
        )

    def action_download_quotation_pdf(self):
        self.ensure_one()
        return self._get_quotation_report_definition().report_action(self)

    # === Smart Button Actions ===
    def action_view_agent_debit_notes(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Agent Debit Notes',
            'res_model': 'logistics.agent.debit.note',
            'view_mode': 'list,form',
            'domain': [('job_id', '=', self.id)],
            'context': {'default_job_id': self.id},
        }
        if self.agent_debit_note_count == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.agent_debit_note_ids.id
        return action

    def action_view_customer_debit_notes(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Customer Debit Notes',
            'res_model': 'logistics.customer.debit.note',
            'view_mode': 'list,form',
            'domain': [('job_id', '=', self.id)],
            'context': {'default_job_id': self.id},
        }
        if self.customer_debit_note_count == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.customer_debit_note_ids.id
        return action

    def action_view_account_moves(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Invoices',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('logistics_job_id', '=', self.id)],
            'context': {'default_logistics_job_id': self.id},
        }
        if self.account_move_count == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.account_move_ids.id
        return action

    def _get_quote_rate_lines(self, *section_codes):
        self.ensure_one()
        return self.quote_rate_line_ids.filtered(lambda line: line.section_code in section_codes)

    def _get_quote_charge_lines(self, *section_codes):
        self.ensure_one()
        return self.quote_charge_line_ids.filtered(lambda line: line.section_code in section_codes)

    def _get_quote_charge_totals(self, *section_codes):
        self.ensure_one()
        lines = self.quote_charge_line_ids.filtered('include_in_total')
        if section_codes:
            lines = lines.filtered(lambda line: line.section_code in section_codes)
        return {
            'amount': sum(lines.mapped('amount')),
            'amount_20dc': sum(lines.mapped('amount_20dc')),
            'amount_40hc': sum(lines.mapped('amount_40hc')),
            'amount_cbm_low': sum(lines.mapped('amount_cbm_low')),
            'amount_cbm_mid': sum(lines.mapped('amount_cbm_mid')),
            'amount_cbm_high': sum(lines.mapped('amount_cbm_high')),
        }

    def _get_quotation_title(self):
        self.ensure_one()
        origin = self.pol or '......'
        destination = self.place_of_delivery or self.pod or '......'
        titles = {
            'trucking_customs': _('Quotation for Trucking and Customs from %s to %s') % (origin, destination),
            'sea_lcl': _('Quotation for LCL Rate from %s to %s') % (origin, destination),
            'sea_fcl': _('Quotation for Seafreight from %s to %s') % (origin, destination),
            'air': _('Quotation for Airfreight from %s to %s') % (origin, destination),
        }
        return titles.get(self.quotation_layout) or _('Quotation')

    def _get_quotation_intro_text(self):
        self.ensure_one()
        if self.quotation_intro:
            return self.quotation_intro
        intro_map = {
            'trucking_customs': _(
                'Thank you so much for your interest in our services. '
                'I would like to advise the trucking fee and Customs fee as below:'
            ),
            'sea_lcl': _(
                'Thanks so much for your interest in our services. '
                'I would like to advise the Seafreight as below:'
            ),
            'sea_fcl': _(
                'Thanks so much for your interested in our services. '
                'I would like to advise the seafreight as below:'
            ),
            'air': _(
                'Thanks so much for your interested in our services. '
                'I would like to advise the airfreight as below:'
            ),
        }
        return intro_map.get(self.quotation_layout) or _(
            'Thank you so much for your interest in our services.'
        )

    def _get_quotation_footer_text(self):
        self.ensure_one()
        if self.quotation_footer_note:
            return self.quotation_footer_note
        return _('The above rates are subject %(vat)s%% VAT and inspection (if any).', vat=self.vat_percent)

    def _get_salesperson_name(self):
        self.ensure_one()
        return self.salesperson_name or self._get_default_salesperson_values()['salesperson_name']

    def _get_salesperson_email(self):
        self.ensure_one()
        return self.salesperson_email or self._get_default_salesperson_values()['salesperson_email']

    def _get_salesperson_phone(self):
        self.ensure_one()
        return self.salesperson_phone or self._get_default_salesperson_values()['salesperson_phone']
