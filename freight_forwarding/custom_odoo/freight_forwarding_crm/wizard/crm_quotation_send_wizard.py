import base64

from odoo import api, fields, models


class CrmQuotationSendWizard(models.TransientModel):
    _name = 'crm.quotation.send.wizard'
    _description = 'Send Quotation Wizard'

    quotation_id = fields.Many2one('crm.lead.quotation', string='Quotation', required=True)
    service_type = fields.Char(related='quotation_id.freight_service_type', string='Service Type')
    show_additional = fields.Boolean(compute='_compute_show_additional')
    additional_quotation_id = fields.Many2one(
        'crm.lead.quotation', string='Attach Additional Quotation',
        domain="[('lead_id', '=', lead_id), ('id', '!=', quotation_id), "
               "('freight_service_type', '=', additional_service_type), "
               "('state', '=', 'draft')]",
    )
    lead_id = fields.Many2one(related='quotation_id.lead_id')
    additional_service_type = fields.Char(compute='_compute_show_additional')

    send_method = fields.Selection([
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
    ], string='Send Via', required=True, default='email')

    # Email fields
    email_to = fields.Char(string='Email To', compute='_compute_email_to', store=False, readonly=False)
    email_subject = fields.Char(string='Subject')
    email_body = fields.Html(string='Message')

    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    # WhatsApp fields
    whatsapp_number = fields.Char(string='WhatsApp Number', compute='_compute_whatsapp_number', store=False, readonly=False)
    whatsapp_message = fields.Text(string='WhatsApp Message')

    @api.depends('quotation_id.freight_service_type')
    def _compute_show_additional(self):
        for rec in self:
            st = rec.quotation_id.freight_service_type
            if st == 'fcl':
                rec.show_additional = True
                rec.additional_service_type = 'lcl'
            elif st == 'lcl':
                rec.show_additional = True
                rec.additional_service_type = 'fcl'
            else:
                rec.show_additional = False
                rec.additional_service_type = False

    @api.depends('quotation_id')
    def _compute_email_to(self):
        for rec in self:
            rec.email_to = rec.quotation_id.email_from or ''

    @api.depends('quotation_id')
    def _compute_whatsapp_number(self):
        for rec in self:
            rec.whatsapp_number = rec.quotation_id.phone or ''

    @api.onchange('quotation_id', 'send_method', 'additional_quotation_id')
    def _onchange_defaults(self):
        q = self.quotation_id
        if not q:
            return
        customer_name = q.partner_id.name or 'Customer'
        service_type = (q.freight_service_type or '').upper()
        pol = q.freight_pol_id.name or ''
        pod = q.freight_pod_id.name or ''
        weight = int(q.freight_weight) if q.freight_weight == int(q.freight_weight) else q.freight_weight
        volume = int(q.freight_volume) if q.freight_volume == int(q.freight_volume) else q.freight_volume
        self.email_subject = '%s :// %s - %s // %s KGS / %s CBM' % (service_type, pol, pod, weight, volume)
        self.email_body = '''<p>Dear %s,</p>
<p>Please find attached our freight quotation <strong>%s</strong>.</p>
<p>Please do not hesitate to contact us if you have any questions.</p>
<p>Best regards,</p>''' % (customer_name, q.name)
        # Auto-generate PDF attachment(s)
        report = self.env.ref('freight_forwarding_crm.action_report_crm_lead_quotation', raise_if_not_found=False)
        if report:
            try:
                attach_ids = []
                pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(report, q.ids)
                attach = self.env['ir.attachment'].create({
                    'name': 'Freight Quotation - %s.pdf' % q.name,
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_content),
                    'res_model': self._name,
                    'mimetype': 'application/pdf',
                })
                attach_ids.append(attach.id)
                # Attach additional quotation PDF if selected
                if self.additional_quotation_id:
                    aq = self.additional_quotation_id
                    pdf2, _ = self.env['ir.actions.report']._render_qweb_pdf(report, aq.ids)
                    attach2 = self.env['ir.attachment'].create({
                        'name': 'Freight Quotation - %s.pdf' % aq.name,
                        'type': 'binary',
                        'datas': base64.b64encode(pdf2),
                        'res_model': self._name,
                        'mimetype': 'application/pdf',
                    })
                    attach_ids.append(attach2.id)
                self.attachment_ids = [(6, 0, attach_ids)]
            except Exception:
                pass

        self.whatsapp_message = (
            'Dear %s,\n\nPlease find attached our freight quotation *%s*.\n\n'
            'Please do not hesitate to contact us if you have any questions.\n\n'
            'Best regards,'
        ) % (customer_name, q.name)

    def action_send(self):
        self.ensure_one()
        quotation = self.quotation_id

        if self.send_method == 'email':
            self._send_email(quotation)
        else:
            self._send_whatsapp(quotation)

        # Update state and lead stage
        quotation.write({'state': 'sent', 'sent_date': fields.Datetime.now()})
        sent_stage = self.env.ref('crm.stage_lead3', raise_if_not_found=False)
        if sent_stage and quotation.lead_id:
            quotation.lead_id.stage_id = sent_stage

        return {'type': 'ir.actions.act_window_close'}

    def _send_email(self, quotation):
        template = self.env.ref('freight_forwarding_crm.email_template_crm_quotation', raise_if_not_found=False)

        mail_values = {
            'subject': self.email_subject,
            'body_html': self.email_body,
            'email_to': self.email_to,
            'attachment_ids': [(6, 0, self.attachment_ids.ids)],
            'auto_delete': True,
        }
        if template:
            mail_values['email_from'] = template.email_from or self.env.company.email or ''

        mail = self.env['mail.mail'].create(mail_values)
        mail.send()

        # Log in chatter
        quotation.message_post(
            body='Quotation emailed to <b>%s</b>.' % self.email_to,
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

    def _send_whatsapp(self, quotation):
        # Generate a WhatsApp URL (wa.me deep link) and log it
        number = (self.whatsapp_number or '').replace(' ', '').replace('+', '').replace('-', '')
        import urllib.parse
        msg = urllib.parse.quote(self.whatsapp_message or '')
        wa_url = 'https://wa.me/%s?text=%s' % (number, msg)

        quotation.message_post(
            body='Quotation sent via WhatsApp to <b>%s</b>. <a href="%s" target="_blank">Open WhatsApp</a>' % (
                self.whatsapp_number, wa_url),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )
