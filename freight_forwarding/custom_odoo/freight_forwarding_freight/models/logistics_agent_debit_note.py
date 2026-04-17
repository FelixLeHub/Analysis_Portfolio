from odoo import models, fields, api

ONES = {
    0: '', 1: 'ONE', 2: 'TWO', 3: 'THREE', 4: 'FOUR', 5: 'FIVE',
    6: 'SIX', 7: 'SEVEN', 8: 'EIGHT', 9: 'NINE', 10: 'TEN',
    11: 'ELEVEN', 12: 'TWELVE', 13: 'THIRTEEN', 14: 'FOURTEEN', 15: 'FIFTEEN',
    16: 'SIXTEEN', 17: 'SEVENTEEN', 18: 'EIGHTEEN', 19: 'NINETEEN',
}
TENS = {
    2: 'TWENTY', 3: 'THIRTY', 4: 'FORTY', 5: 'FIFTY',
    6: 'SIXTY', 7: 'SEVENTY', 8: 'EIGHTY', 9: 'NINETY',
}


def _number_to_words(n):
    """Convert an integer to English words."""
    if n < 0:
        return 'MINUS ' + _number_to_words(-n)
    if n == 0:
        return 'ZERO'
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10] + ('' if n % 10 == 0 else ' ' + ONES[n % 10])
    if n < 1000:
        rest = _number_to_words(n % 100)
        return ONES[n // 100] + ' HUNDRED' + ('' if not rest else ' AND ' + rest)
    if n < 1_000_000:
        rest = _number_to_words(n % 1000)
        return _number_to_words(n // 1000) + ' THOUSAND' + ('' if not rest else ' ' + rest)
    if n < 1_000_000_000:
        rest = _number_to_words(n % 1_000_000)
        return _number_to_words(n // 1_000_000) + ' MILLION' + ('' if not rest else ' ' + rest)
    return str(n)


def amount_to_words(amount, currency_name='USD'):
    """Convert a monetary amount to words.  e.g. 60.00 USD -> 'SAY USD SIXTY ONLY'"""
    abs_amount = abs(amount)
    whole = int(abs_amount)
    cents = round((abs_amount - whole) * 100)
    words = _number_to_words(whole)
    if cents:
        words += ' AND %s/100' % str(cents).zfill(2)
    prefix = 'MINUS ' if amount < 0 else ''
    return 'SAY %s%s %s ONLY' % (prefix, currency_name, words)


class LogisticsAgentDebitNote(models.Model):
    _name = 'logistics.agent.debit.note'
    _description = 'Agent Debit Note'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char(string='DN Number', required=True, tracking=True)
    job_id = fields.Many2one('logistics.job', string='Job', required=True, ondelete='cascade')
    agent_id = fields.Many2one('res.partner', string='Agent', required=True, tracking=True)
    note_type = fields.Selection([
        ('debit', 'Debit Note'),
        ('credit', 'Credit Note'),
    ], string='Type', default='debit', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    due_date = fields.Date(string='Due Date')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.ref('base.USD', raise_if_not_found=False),
    )
    prepared_by = fields.Char(string='Prepared By')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('paid', 'Paid'),
    ], string='Status', default='draft', tracking=True)

    line_ids = fields.One2many(
        'logistics.agent.debit.note.line', 'debit_note_id', string='Charge Lines',
    )
    total_amount = fields.Monetary(
        string='Total Amount', currency_field='currency_id',
        compute='_compute_total', store=True,
    )
    total_amount_words = fields.Char(
        string='Amount in Words', compute='_compute_total', store=True,
    )
    notes = fields.Text(string='Notes')

    # Related fields from job for display
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
    voyage_no = fields.Char(related='job_id.voyage_no')
    flight_no = fields.Char(related='job_id.flight_no')
    container_ids = fields.One2many(related='job_id.container_ids')

    # Agent bank details (from partner or manual override)
    agent_bank_name = fields.Char(string='Bank Name')
    agent_bank_address = fields.Char(string='Bank Address')
    agent_swift_code = fields.Char(string='SWIFT Code')
    agent_account_no = fields.Char(string='Account No')
    agent_beneficiary = fields.Char(string='Beneficiary')

    @api.depends('line_ids.amount')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('amount'))
            currency_name = rec.currency_id.name if rec.currency_id else 'USD'
            rec.total_amount_words = amount_to_words(rec.total_amount, currency_name)

    @api.onchange('job_id')
    def _onchange_job_id(self):
        for rec in self:
            if not rec.job_id:
                continue
            rec.agent_id = rec.job_id.agent_id
            if rec.job_id.currency_id:
                rec.currency_id = rec.job_id.currency_id

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_paid(self):
        self.write({'state': 'paid'})

    def action_draft(self):
        self.write({'state': 'draft'})


class LogisticsAgentDebitNoteLine(models.Model):
    _name = 'logistics.agent.debit.note.line'
    _description = 'Agent Debit Note Line'
    _order = 'debit_note_id, id'

    debit_note_id = fields.Many2one(
        'logistics.agent.debit.note', string='Debit Note',
        required=True, ondelete='cascade',
    )
    charge_type_id = fields.Many2one('logistics.charge.type', string='Charge Type')
    name = fields.Char(string='Description', required=True)
    remarks = fields.Char(string='Remarks')
    quantity = fields.Float(string='Quantity', default=1.0)
    unit = fields.Char(string='Unit')
    unit_price = fields.Float(string='Unit Price')
    currency_id = fields.Many2one(
        related='debit_note_id.currency_id', store=True,
    )
    amount = fields.Monetary(
        string='Amount', currency_field='currency_id',
        compute='_compute_amount', store=True, readonly=False,
    )
    is_taxable = fields.Boolean(string='Taxable', default=False)

    # Secondary currency (optional) - for invoices with 2 currency columns
    secondary_currency_id = fields.Many2one(
        'res.currency', string='Secondary Currency',
    )
    secondary_amount = fields.Monetary(
        string='Secondary Amount', currency_field='secondary_currency_id',
        compute='_compute_secondary_amount', store=True, readonly=False,
    )
    implied_exchange_rate = fields.Float(
        string='Implied Rate', digits=(12, 6),
        compute='_compute_implied_exchange_rate', store=True,
        help='Exchange rate derived from primary and secondary amounts',
    )

    @api.depends('quantity', 'unit_price')
    def _compute_amount(self):
        for line in self:
            line.amount = line.quantity * line.unit_price

    @api.depends('amount', 'secondary_currency_id', 'debit_note_id.currency_id', 'debit_note_id.date')
    def _compute_secondary_amount(self):
        for line in self:
            if line.secondary_currency_id and line.currency_id and line.amount:
                line.secondary_amount = line.currency_id._convert(
                    line.amount,
                    line.secondary_currency_id,
                    self.env.company,
                    line.debit_note_id.date or fields.Date.context_today(self),
                )
            else:
                line.secondary_amount = 0.0

    @api.depends('amount', 'secondary_amount')
    def _compute_implied_exchange_rate(self):
        for line in self:
            if line.amount and line.secondary_amount:
                line.implied_exchange_rate = line.secondary_amount / line.amount
            else:
                line.implied_exchange_rate = 0.0
