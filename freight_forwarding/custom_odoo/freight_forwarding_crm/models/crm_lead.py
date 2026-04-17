from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def create(self, vals_list):
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        for vals in vals_list:
            name = vals.get('name') or ''
            if not name or name == 'New' or name.endswith("'s opportunity"):
                vals['name'] = self.env['ir.sequence'].next_by_code('crm.lead') or 'New'
        return super().create(vals_list)

    def write(self, vals):
        if 'freight_currency_id' in vals:
            old_currencies = {lead.id: lead.freight_currency_id for lead in self}
        result = super().write(vals)
        if 'freight_currency_id' in vals:
            today = fields.Date.today()
            company = self.env.company
            for lead in self:
                new_cur = lead.freight_currency_id
                old_cur = old_currencies[lead.id]
                if not old_cur or not new_cur or old_cur == new_cur:
                    continue
                # Propagate to quotations
                for q in lead.lead_quotation_ids:
                    line_vals = {}
                    if q.expected_revenue:
                        line_vals['expected_revenue'] = old_cur._convert(
                            q.expected_revenue, new_cur, company, today)
                    line_vals['currency_id'] = new_cur.id
                    line_vals['previous_currency_id'] = new_cur.id
                    q.write(line_vals)
                    # Convert quotation line rates
                    for line in self.env['crm.lead.quotation.line'].search(
                            [('quotation_id', '=', q.id)]):
                        if line.rate:
                            line.rate = old_cur._convert(line.rate, new_cur, company, today)
                # Propagate to freight jobs
                for job in lead.freight_job_ids:
                    job.write({'currency_id': new_cur.id})
        return result

    # Currency (editable, defaults to company currency)
    freight_currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
        tracking=True,
    )
    previous_freight_currency_id = fields.Many2one('res.currency', string='Previous Currency')

    @api.onchange('freight_currency_id')
    def _onchange_freight_currency_id(self):
        new_cur = self.freight_currency_id
        old_cur = self.previous_freight_currency_id or self._origin.freight_currency_id
        if not (old_cur and new_cur) or old_cur == new_cur:
            self.previous_freight_currency_id = new_cur or old_cur
            return
        today = fields.Date.today()
        company = self.env.company
        if self.expected_revenue:
            self.expected_revenue = old_cur._convert(self.expected_revenue, new_cur, company, today)
        self.previous_freight_currency_id = new_cur

    # Shipment Details
    freight_incoterm = fields.Selection([
        ('EXW', 'EXW'), ('FCA', 'FCA'), ('CPT', 'CPT'), ('CIP', 'CIP'),
        ('DAP', 'DAP'), ('DPU', 'DPU'), ('DDP', 'DDP'),
        ('FAS', 'FAS'), ('FOB', 'FOB'), ('CFR', 'CFR'), ('CIF', 'CIF'),
    ], string='Incoterm', tracking=True)

    freight_direction_id = fields.Many2one(
        'master.service.type', string='Direction',
        domain=[('code', 'in', ['export', 'import'])],
        tracking=True,
    )
    freight_service_type_id = fields.Many2one(
        'master.service.type', string='Service Type',
        domain=[('code', 'in', ['fcl', 'lcl', 'air', 'trucking'])],
        tracking=True,
    )
    # Computed code fields for view visibility logic
    freight_direction = fields.Char(
        related='freight_direction_id.code', store=True)
    freight_service_type = fields.Char(
        related='freight_service_type_id.code', store=True)

    freight_pol_id = fields.Many2one('master.port.airport', string='POL', tracking=True)
    freight_pod_id = fields.Many2one('master.port.airport', string='POD', tracking=True)

    # Cargo Details
    freight_weight = fields.Float(string='Weight (KGS)', digits=(16, 2), tracking=True)
    freight_volume = fields.Float(string='Volume (CBM)', digits=(16, 3), tracking=True)
    freight_commodity = fields.Char(string='Commodity', tracking=True)
    freight_pallets = fields.Char(string='Pallets', tracking=True)
    freight_cargo = fields.Char(string='Cargo', tracking=True)
    freight_dimension = fields.Char(string='Dimension', tracking=True)

    # Quotations
    lead_quotation_ids = fields.One2many('crm.lead.quotation', 'lead_id', string='Quotations')
    lead_quotation_count = fields.Integer(string='Quotation Count', compute='_compute_lead_quotation_count')

    def _compute_lead_quotation_count(self):
        for lead in self:
            lead.lead_quotation_count = len(lead.lead_quotation_ids)

    # Freight Jobs
    freight_job_ids = fields.One2many('logistics.job', 'lead_id', string='Freight Jobs')
    freight_job_count = fields.Integer(string='Freight Job Count', compute='_compute_freight_job_count')

    def _compute_freight_job_count(self):
        for lead in self:
            lead.freight_job_count = len(lead.freight_job_ids)

    def action_view_freight_jobs(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Freight Jobs',
            'res_model': 'logistics.job',
            'view_mode': 'list,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {'default_lead_id': self.id},
        }

    def action_sale_quotations_new(self):
        """Override sale_crm's New Quotation to open our custom quotation form.
        If lead is in Input Lead Detail or Request more details, move to Draft Quotation."""
        self.ensure_one()
        input_stage = self.env.ref('crm.stage_lead1', raise_if_not_found=False)
        request_stage = self.env.ref('freight_forwarding_crm.stage_lead_request_details', raise_if_not_found=False)
        draft_qt_stage = self.env.ref('freight_forwarding_crm.stage_lead_draft_quotation', raise_if_not_found=False)
        if draft_qt_stage and self.stage_id in (input_stage, request_stage):
            self.stage_id = draft_qt_stage
        return {
            'type': 'ir.actions.act_window',
            'name': 'New Quotation',
            'res_model': 'crm.lead.quotation',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_lead_id': self.id},
        }

    def action_view_lead_quotations(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quotations',
            'res_model': 'crm.lead.quotation',
            'view_mode': 'list,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {'default_lead_id': self.id},
        }

    def action_send_lead_email(self):
        """Open email compose wizard to request missing information for quotation.
        If the lead is in 'Input Lead Detail' stage, move it to 'Request more details'."""
        self.ensure_one()
        # Advance stage if currently in Input Lead Detail
        input_stage = self.env.ref('crm.stage_lead1', raise_if_not_found=False)
        request_stage = self.env.ref('freight_forwarding_crm.stage_lead_request_details', raise_if_not_found=False)
        if input_stage and request_stage and self.stage_id == input_stage:
            self.stage_id = request_stage
        template = self.env.ref('freight_forwarding_crm.email_template_lead_request_info', raise_if_not_found=False)
        ctx = {
            'default_model': 'crm.lead',
            'default_res_ids': self.ids,
            'default_template_id': template.id if template else False,
            'default_composition_mode': 'comment',
            'default_email_layout_xmlid': 'mail.mail_notification_light',
        }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Send Email',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': ctx,
        }

    # Client Details
    freight_point_of_request = fields.Selection([
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
        ('email_whatsapp', 'Email / WhatsApp'),
        ('phone', 'Phone'),
        ('referral', 'Referral'),
        ('walk_in', 'Walk-in'),
    ], string='Point of Request', tracking=True)
