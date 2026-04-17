from odoo import api, fields, models, Command


class CrmLeadQuotation(models.Model):
    _name = 'crm.lead.quotation'
    _description = 'CRM Lead Quotation'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Quotation ID', readonly=True, default='New', copy=False)
    lead_id = fields.Many2one('crm.lead', string='Lead', required=True, ondelete='cascade', tracking=True)
    sent_date = fields.Datetime(string='Sent', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    previous_currency_id = fields.Many2one('res.currency', string='Previous Currency')
    stage_id = fields.Many2one(related='lead_id.stage_id', string='Lead Stage', readonly=True, store=True)

    # Revenue
    expected_revenue = fields.Monetary(string='Expected Revenue', currency_field='currency_id')

    # Shipment Details
    freight_incoterm = fields.Selection(related='lead_id.freight_incoterm', readonly=False, store=True)
    freight_direction_id = fields.Many2one(related='lead_id.freight_direction_id', readonly=False, store=True)
    freight_direction = fields.Char(related='freight_direction_id.code', store=True)
    freight_service_type_id = fields.Many2one(related='lead_id.freight_service_type_id', readonly=False, store=True)
    freight_service_type = fields.Char(related='freight_service_type_id.code', store=True)
    freight_pol_id = fields.Many2one(related='lead_id.freight_pol_id', readonly=False, store=True)
    freight_pod_id = fields.Many2one(related='lead_id.freight_pod_id', readonly=False, store=True)
    freight_carrier = fields.Char(string='Carrier')
    freight_tt_days = fields.Integer(string='T/T (days)')
    freight_frequency = fields.Char(string='Frequency')

    # Client Details
    partner_id = fields.Many2one(related='lead_id.partner_id', readonly=True, store=True)
    email_from = fields.Char(related='lead_id.email_from', readonly=True)
    phone = fields.Char(related='lead_id.phone', readonly=True)
    freight_point_of_request = fields.Selection(related='lead_id.freight_point_of_request', readonly=True)
    lead_create_date = fields.Datetime(related='lead_id.create_date', string='Created Date', readonly=True)

    # Cargo Details
    freight_weight = fields.Float(related='lead_id.freight_weight', readonly=False, store=True)
    freight_volume = fields.Float(related='lead_id.freight_volume', readonly=False, store=True)
    freight_commodity = fields.Char(related='lead_id.freight_commodity', readonly=False, store=True)
    freight_pallets = fields.Char(related='lead_id.freight_pallets', readonly=False, store=True)
    freight_cargo = fields.Char(related='lead_id.freight_cargo', readonly=False, store=True)
    freight_dimension = fields.Char(related='lead_id.freight_dimension', readonly=False, store=True)

    # Trucking: FTL override for rate bracket selection
    freight_ftl = fields.Selection([
        ('20dc', '20 DC'),
        ('40hc', '40 HC'),
    ], string='FTL')

    # LCL-specific cargo fields
    freight_chargeable_weight = fields.Float(string='Chargeable Weight',
                                             compute='_compute_lcl_weight_fields', store=True)
    freight_cwt = fields.Float(string='CWT', digits=(16, 2),
                               compute='_compute_lcl_weight_fields', store=True)
    freight_wb_100 = fields.Float(string='100 LBS', digits=(16, 3),
                                  compute='_compute_lcl_weight_fields', store=True)
    freight_wb_800 = fields.Float(string='800 LBS', digits=(16, 3),
                                  compute='_compute_lcl_weight_fields', store=True)
    freight_wb_1100 = fields.Float(string='1100 LBS', digits=(16, 3),
                                   compute='_compute_lcl_weight_fields', store=True)

    @api.depends('freight_weight', 'freight_volume')
    def _compute_lcl_weight_fields(self):
        for rec in self:
            kgs = rec.freight_weight or 0.0
            rec.freight_cwt = (kgs * 2.2046) / 100 if kgs else 0.0
            rec.freight_wb_100 = kgs / 45.359 if kgs else 0.0
            rec.freight_wb_800 = kgs / 363 if kgs else 0.0
            rec.freight_wb_1100 = kgs / 500 if kgs else 0.0
            rec.freight_chargeable_weight = max(rec.freight_weight, rec.freight_volume)

    # ── Quotation Lines by section ──
    # FCL sections
    ocean_rate_ids = fields.One2many('crm.lead.quotation.line', 'quotation_id',
                                     string='Ocean Rate', domain=[('section', '=', 'ocean_rate')])
    local_charge_ids = fields.One2many('crm.lead.quotation.line', 'quotation_id',
                                       string='Local Charge', domain=[('section', '=', 'local_charge')])
    exw_fee_ids = fields.One2many('crm.lead.quotation.line', 'quotation_id',
                                  string='Exw Fee', domain=[('section', '=', 'exw_fee')])

    fcl_local_charge_ids = fields.One2many('crm.lead.quotation.line', 'quotation_id',
                                           string='FCL Local Charge', domain=[('section', '=', 'fcl_local_charge')])

    # LCL sections
    lcl_rate_ids = fields.One2many('crm.lead.quotation.line', 'quotation_id',
                                    string='LCL Rate', domain=[('section', '=', 'lcl_rate')])
    lcl_local_charge_ids = fields.One2many('crm.lead.quotation.line', 'quotation_id',
                                            string='LCL Local Charge', domain=[('section', '=', 'lcl_local_charge')])
    lcl_exw_fee_ids = fields.One2many('crm.lead.quotation.line', 'quotation_id',
                                       string='LCL Exw Fee', domain=[('section', '=', 'lcl_exw_fee')])

    # Air sections
    air_rate_ids = fields.One2many('crm.lead.quotation.line', 'quotation_id',
                                    string='Air Rate', domain=[('section', '=', 'air_rate')])
    air_local_charge_ids = fields.One2many('crm.lead.quotation.line', 'quotation_id',
                                            string='Air Local Charge', domain=[('section', '=', 'air_local_charge')])
    air_exw_fee_ids = fields.One2many('crm.lead.quotation.line', 'quotation_id',
                                       string='Air Exw Fee', domain=[('section', '=', 'air_exw_fee')])

    # Trucking sections
    trucking_rate_ids = fields.One2many('crm.lead.quotation.line', 'quotation_id',
                                        string='Trucking Rate', domain=[('section', '=', 'trucking_rate')])
    trucking_surcharge_ids = fields.One2many('crm.lead.quotation.line', 'quotation_id',
                                              string='Trucking Surcharge', domain=[('section', '=', 'trucking_surcharge')])

    # Totals
    amount_total = fields.Monetary(string='Total', currency_field='currency_id',
                                   compute='_compute_amount_total', store=True)
    lead_freight_currency_id = fields.Many2one(
        'res.currency', related='lead_id.freight_currency_id', store=False)
    amount_total_lead_currency = fields.Monetary(
        string='Total Charges', currency_field='lead_freight_currency_id',
        compute='_compute_amount_total_lead_currency', store=False)

    @api.depends(
        'ocean_rate_ids.total', 'local_charge_ids.total', 'exw_fee_ids.total',
        'fcl_local_charge_ids.total',
        'lcl_rate_ids.total', 'lcl_local_charge_ids.total', 'lcl_exw_fee_ids.total',
        'air_rate_ids.total', 'air_local_charge_ids.total', 'air_exw_fee_ids.total',
        'trucking_rate_ids.total', 'trucking_surcharge_ids.total',
    )
    def _compute_amount_total(self):
        for rec in self:
            all_lines = (
                rec.ocean_rate_ids + rec.local_charge_ids + rec.exw_fee_ids +
                rec.fcl_local_charge_ids +
                rec.lcl_rate_ids + rec.lcl_local_charge_ids + rec.lcl_exw_fee_ids +
                rec.air_rate_ids + rec.air_local_charge_ids + rec.air_exw_fee_ids +
                rec.trucking_rate_ids + rec.trucking_surcharge_ids
            )
            rec.amount_total = sum(all_lines.mapped('total'))

    @api.depends('amount_total', 'currency_id', 'lead_freight_currency_id')
    def _compute_amount_total_lead_currency(self):
        today = fields.Date.today()
        for rec in self:
            lead_cur = rec.lead_freight_currency_id
            if not lead_cur or lead_cur == rec.currency_id:
                rec.amount_total_lead_currency = rec.amount_total
            else:
                rec.amount_total_lead_currency = rec.currency_id._convert(
                    rec.amount_total, lead_cur, rec.env.company, today
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('crm.lead.quotation') or 'New'
            if vals.get('lead_id'):
                lead = self.env['crm.lead'].browse(vals['lead_id'])
                if not vals.get('expected_revenue'):
                    vals['expected_revenue'] = lead.expected_revenue
                # Always inherit lead's currency on creation
                if lead.freight_currency_id:
                    vals['currency_id'] = lead.freight_currency_id.id
            if not vals.get('previous_currency_id') and vals.get('currency_id'):
                vals['previous_currency_id'] = vals['currency_id']
        records = super().create(vals_list)
        for rec in records:
            rec._populate_default_lines()
        return records

    def _populate_default_lines(self):
        """No auto-populated lines — rates are imported from freight pricelist."""
        pass

    @api.onchange('lead_id')
    def _onchange_lead_id(self):
        if self.lead_id:
            self.expected_revenue = self.lead_id.expected_revenue
            if self.lead_id.freight_currency_id:
                self.currency_id = self.lead_id.freight_currency_id
                self.previous_currency_id = self.lead_id.freight_currency_id

    @api.onchange('freight_service_type')
    def _onchange_freight_service_type(self):
        """No auto-populated lines — rates are imported from freight pricelist."""
        pass

    @api.onchange('currency_id')
    def _onchange_currency_id(self):
        new_cur = self.currency_id
        old_cur = self.previous_currency_id or self._origin.currency_id
        if not (old_cur and new_cur) or old_cur == new_cur:
            self.previous_currency_id = new_cur or old_cur
            return
        today = fields.Date.today()
        company = self.env.company
        if self.expected_revenue:
            self.expected_revenue = old_cur._convert(self.expected_revenue, new_cur, company, today)
        all_lines = (
            self.ocean_rate_ids + self.local_charge_ids + self.exw_fee_ids +
            self.lcl_rate_ids + self.lcl_local_charge_ids + self.lcl_exw_fee_ids +
            self.air_rate_ids + self.air_local_charge_ids + self.air_exw_fee_ids +
            self.trucking_rate_ids + self.trucking_surcharge_ids
        )
        for line in all_lines:
            if line.rate:
                line.rate = old_cur._convert(line.rate, new_cur, company, today)
        self.previous_currency_id = new_cur

    def action_retrieve_rates(self):
        """Navigate to the Freight Pricelist filtered by matching criteria."""
        self.ensure_one()
        st = self.freight_service_type
        domain = []
        if st == 'fcl':
            # FCL: filter by POL and POD
            if self.freight_pol_id:
                domain.append(('pol_id', '=', self.freight_pol_id.id))
            if self.freight_pod_id:
                domain.append(('pod_id', '=', self.freight_pod_id.id))
        else:
            # LCL, Air, Trucking: filter by lead_id
            if self.lead_id:
                domain.append(('lead_id', '=', self.lead_id.id))
        return {
            'type': 'ir.actions.act_window',
            'name': 'Freight Pricelist',
            'res_model': 'master.freight.pricelist',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': domain,
            'context': {'default_import_quotation_id': self.id},
        }

    def action_preview(self):
        """Download the quotation as PDF."""
        self.ensure_one()
        return self.env.ref('freight_forwarding_crm.action_report_crm_lead_quotation').report_action(self)

    def action_send_quotation(self):
        """Open send wizard to choose Email or WhatsApp channel."""
        self.ensure_one()
        wizard = self.env['crm.quotation.send.wizard'].create({
            'quotation_id': self.id,
        })
        wizard._onchange_defaults()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Send Quotation',
            'res_model': 'crm.quotation.send.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_confirm(self):
        self.write({'state': 'confirmed'})
        confirmed_stage = self.env.ref('freight_forwarding_crm.stage_lead_negotiation', raise_if_not_found=False)
        if confirmed_stage and self.lead_id:
            self.lead_id.stage_id = confirmed_stage

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_create_freight_job(self):
        """Create a logistics.job pre-filled from this quotation's lead data,
        then confirm the quotation and advance the lead to CS: Create Internal Booking."""
        self.ensure_one()
        service_map = {
            'fcl': 'sea_fcl_export' if self.freight_direction == 'export' else 'sea_fcl_import',
            'lcl': 'sea_lcl',
            'air': 'air',
            'trucking': 'trucking',
        }
        service_type = service_map.get(self.freight_service_type, 'sea_fcl_export')
        job = self.env['logistics.job'].create({
            'lead_id': self.lead_id.id,
            'customer_id': self.partner_id.id or self.lead_id.partner_id.id,
            'service_type': service_type,
            'direction': self.freight_direction or 'export',
            'pol': self.freight_pol_id.name or '',
            'pod': self.freight_pod_id.name or '',
            'commodity': self.freight_commodity,
            'weight_kgs': self.freight_weight,
            'volume_cbm': self.freight_volume,
            'currency_id': self.currency_id.id,
        })
        # Confirm the quotation and advance lead stage
        self.write({'state': 'confirmed'})
        confirmed_stage = self.env.ref('freight_forwarding_crm.stage_lead_cs_booking', raise_if_not_found=False)
        if confirmed_stage and self.lead_id:
            self.lead_id.stage_id = confirmed_stage
        return {
            'type': 'ir.actions.act_window',
            'name': 'Freight Job',
            'res_model': 'logistics.job',
            'view_mode': 'form',
            'res_id': job.id,
            'target': 'current',
        }


class CrmLeadQuotationLine(models.Model):
    _name = 'crm.lead.quotation.line'
    _description = 'CRM Lead Quotation Line'
    _order = 'section, sequence, id'

    quotation_id = fields.Many2one('crm.lead.quotation', string='Quotation',
                                    required=True, ondelete='cascade')
    section = fields.Selection([
        # FCL
        ('ocean_rate', 'Ocean Rate'),
        ('local_charge', 'Local Charge'),
        ('fcl_local_charge', 'FCL Local Charge'),
        ('exw_fee', 'Exw Fee'),
        # LCL
        ('lcl_rate', 'LCL Rate'),
        ('lcl_local_charge', 'LCL Local Charge'),
        ('lcl_exw_fee', 'LCL Exw Fee'),
        # Air
        ('air_rate', 'Air Rate'),
        ('air_local_charge', 'Air Local Charge'),
        ('air_exw_fee', 'Air Exw Fee'),
        # Trucking
        ('trucking_rate', 'Trucking Rate'),
        ('trucking_surcharge', 'Trucking Surcharge'),
    ], string='Section', required=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Name')
    container = fields.Selection([
        ('20DC', "20'DC"),
        ('40DC', "40'DC"),
        ('40HC', "40'HC"),
        ('45HC', "45'HC"),
    ], string='Container')
    quantity = fields.Float(string='Quantity', default=1)
    rate = fields.Float(string='Rate', digits=(16, 2))
    unit = fields.Selection([
        ('CBM', 'CBM'),
        ('RT', 'RT'),
        ('CWT', 'CWT'),
        ('SHMT', 'SHMT'),
        ('BL', 'B/L'),
        ('20DC', "20 DC"),
        ('40HC', "40 HC"),
    ], string='Unit')
    currency_id = fields.Many2one(related='quotation_id.currency_id', store=True, readonly=True)
    total = fields.Monetary(string='Total', currency_field='currency_id',
                            compute='_compute_total', store=True)
    note = fields.Char(string='Note')

    @api.depends('quantity', 'rate', 'unit', 'quotation_id.freight_weight', 'quotation_id.freight_volume')
    def _compute_total(self):
        for line in self:
            if line.unit in ('CBM', 'RT') and line.quotation_id:
                chargeable_weight = max(line.quotation_id.freight_weight, line.quotation_id.freight_volume)
                line.total = line.rate * chargeable_weight
            else:
                line.total = line.quantity * line.rate
