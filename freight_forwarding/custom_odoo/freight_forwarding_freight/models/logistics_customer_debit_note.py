from odoo import models, fields, api


class LogisticsCustomerDebitNote(models.Model):
    _name = 'logistics.customer.debit.note'
    _description = 'Customer Debit Note'
    _inherit = ['mail.thread']
    _order = 'issue_date desc, id desc'

    name = fields.Char(
        string='Ref No', required=True, copy=False, readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('logistics.customer.debit.note') or 'New',
    )
    job_id = fields.Many2one('logistics.job', string='Job', required=True, ondelete='cascade')
    customer_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    contact_person = fields.Char(string='Contact Person')
    issue_date = fields.Date(string='Issue Date', required=True, default=fields.Date.context_today)
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.ref('base.USD', raise_if_not_found=False),
    )
    prepared_by = fields.Char(string='Prepared By')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
    ], string='Status', default='draft', tracking=True)

    line_ids = fields.One2many(
        'logistics.customer.debit.note.line', 'debit_note_id', string='Charge Lines',
    )
    total_amount = fields.Monetary(
        string='Total Amount', currency_field='currency_id',
        compute='_compute_total', store=True,
    )
    notes = fields.Text(string='Notes')

    # Related fields from job
    service_type = fields.Selection(related='job_id.service_type', store=True)
    mbl_no = fields.Char(related='job_id.mbl_no')
    hbl_no = fields.Char(related='job_id.hbl_no')
    mawb_no = fields.Char(related='job_id.mawb_no')
    hawb_no = fields.Char(related='job_id.hawb_no')
    pol = fields.Char(related='job_id.pol')
    pod = fields.Char(related='job_id.pod')
    etd = fields.Date(related='job_id.etd')
    eta = fields.Date(related='job_id.eta')
    vessel_name = fields.Char(related='job_id.vessel_name')
    consignee_id = fields.Many2one(related='job_id.consignee_id')
    volume_cbm = fields.Float(related='job_id.volume_cbm')
    package_count = fields.Integer(related='job_id.package_count')

    @api.depends('line_ids.amount_debit', 'line_ids.amount_credit')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('amount_debit')) - sum(rec.line_ids.mapped('amount_credit'))

    @api.onchange('job_id')
    def _onchange_job_id(self):
        for rec in self:
            if not rec.job_id:
                continue
            rec.customer_id = rec.job_id.customer_id
            if rec.job_id.currency_id:
                rec.currency_id = rec.job_id.currency_id

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_send(self):
        self.write({'state': 'sent'})

    def action_paid(self):
        self.write({'state': 'paid'})

    def action_draft(self):
        self.write({'state': 'draft'})


class LogisticsCustomerDebitNoteLine(models.Model):
    _name = 'logistics.customer.debit.note.line'
    _description = 'Customer Debit Note Line'
    _order = 'debit_note_id, id'

    debit_note_id = fields.Many2one(
        'logistics.customer.debit.note', string='Debit Note',
        required=True, ondelete='cascade',
    )
    charge_type_id = fields.Many2one('logistics.charge.type', string='Charge Type')
    name = fields.Char(string='Description', required=True)
    quantity = fields.Float(string='Quantity', default=1.0)
    unit = fields.Char(string='Unit')
    unit_price = fields.Float(string='Price')
    vat_percent = fields.Float(string='VAT %')
    currency_id = fields.Many2one(
        related='debit_note_id.currency_id', store=True,
    )
    amount_debit = fields.Monetary(
        string='Debit', currency_field='currency_id',
        compute='_compute_amount', store=True, readonly=False,
    )
    amount_credit = fields.Monetary(
        string='Credit', currency_field='currency_id',
    )

    # Secondary currency (optional) - for invoices with 2 currency columns
    secondary_currency_id = fields.Many2one(
        'res.currency', string='Secondary Currency',
    )
    secondary_amount_debit = fields.Monetary(
        string='Secondary Debit', currency_field='secondary_currency_id',
        compute='_compute_secondary_amounts', store=True, readonly=False,
    )
    secondary_amount_credit = fields.Monetary(
        string='Secondary Credit', currency_field='secondary_currency_id',
        compute='_compute_secondary_amounts', store=True, readonly=False,
    )
    implied_exchange_rate = fields.Float(
        string='Implied Rate', digits=(12, 6),
        compute='_compute_implied_exchange_rate', store=True,
        help='Exchange rate derived from primary and secondary amounts',
    )

    @api.depends('quantity', 'unit_price', 'vat_percent')
    def _compute_amount(self):
        for line in self:
            subtotal = line.quantity * line.unit_price
            vat = subtotal * line.vat_percent / 100.0 if line.vat_percent else 0.0
            line.amount_debit = subtotal + vat

    @api.depends('amount_debit', 'amount_credit', 'secondary_currency_id',
                 'debit_note_id.currency_id', 'debit_note_id.issue_date')
    def _compute_secondary_amounts(self):
        for line in self:
            if line.secondary_currency_id and line.currency_id:
                date = line.debit_note_id.issue_date or fields.Date.context_today(self)
                company = self.env.company
                line.secondary_amount_debit = line.currency_id._convert(
                    line.amount_debit, line.secondary_currency_id, company, date,
                ) if line.amount_debit else 0.0
                line.secondary_amount_credit = line.currency_id._convert(
                    line.amount_credit, line.secondary_currency_id, company, date,
                ) if line.amount_credit else 0.0
            else:
                line.secondary_amount_debit = 0.0
                line.secondary_amount_credit = 0.0

    @api.depends('amount_debit', 'secondary_amount_debit')
    def _compute_implied_exchange_rate(self):
        for line in self:
            if line.amount_debit and line.secondary_amount_debit:
                line.implied_exchange_rate = line.secondary_amount_debit / line.amount_debit
            else:
                line.implied_exchange_rate = 0.0
