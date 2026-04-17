from odoo import _, api, fields, models

UNITS_MAP = {
    'cbm': 'CBM', 'rt': 'RT', 'cwt': 'CWT', 'shmt': 'SHMT',
    'bl': 'BL', '20dc': '20DC', '40hc': '40HC',
}


class PricelistImportWizard(models.TransientModel):
    _name = 'freight.pricelist.import.wizard'
    _description = 'Import Pricelist Rates to Quotation'

    pricelist_id = fields.Many2one('master.freight.pricelist', required=True)
    pricelist_service_code = fields.Char(related='pricelist_id.service_type_code')
    pricelist_lead_id = fields.Many2one(related='pricelist_id.lead_id')
    pricelist_pol_id = fields.Many2one(related='pricelist_id.pol_id')
    pricelist_pod_id = fields.Many2one(related='pricelist_id.pod_id')
    quotation_id = fields.Many2one(
        'crm.lead.quotation',
        string='Quotation',
        required=True,
    )

    @api.onchange('pricelist_id')
    def _onchange_pricelist_id(self):
        if not self.pricelist_id:
            return
        code = self.pricelist_id.service_type_code
        if code == 'fcl':
            # FCL: match by POL and POD
            domain = [('freight_service_type', '=', 'fcl')]
            pol = self.pricelist_id.pol_id
            pod = self.pricelist_id.pod_id
            if pol:
                domain.append(('freight_pol_id', '=', pol.id))
            if pod:
                domain.append(('freight_pod_id', '=', pod.id))
        else:
            # LCL, Air, Trucking: match by lead_id and POL/POD
            domain = []
            lead = self.pricelist_id.lead_id
            if lead:
                domain.append(('lead_id', '=', lead.id))
            pol = self.pricelist_id.pol_id
            pod = self.pricelist_id.pod_id
            if pol:
                domain.append(('freight_pol_id', '=', pol.id))
            if pod:
                domain.append(('freight_pod_id', '=', pod.id))
        return {'domain': {'quotation_id': domain}}

    def action_import(self):
        self.ensure_one()
        quotation = self.quotation_id
        pricelist = self.pricelist_id
        pricelist_code = pricelist.service_type_code
        qt = quotation.freight_service_type
        Line = self.env['crm.lead.quotation.line']

        # Validate matching rules
        from odoo.exceptions import UserError
        if pricelist_code == 'fcl':
            if qt != 'fcl':
                raise UserError(_('This FCL pricelist can only be imported into an FCL quotation.'))
            if pricelist.pol_id and quotation.freight_pol_id and pricelist.pol_id != quotation.freight_pol_id:
                raise UserError(_('POL mismatch: pricelist POL (%s) does not match quotation POL (%s).') % (
                    pricelist.pol_id.name, quotation.freight_pol_id.name))
            if pricelist.pod_id and quotation.freight_pod_id and pricelist.pod_id != quotation.freight_pod_id:
                raise UserError(_('POD mismatch: pricelist POD (%s) does not match quotation POD (%s).') % (
                    pricelist.pod_id.name, quotation.freight_pod_id.name))
        else:
            # LCL, Air, Trucking: must match lead_id, service type, and POL/POD
            if pricelist.lead_id and quotation.lead_id and pricelist.lead_id != quotation.lead_id:
                raise UserError(_('This pricelist is linked to lead "%s" but the quotation belongs to lead "%s".') % (
                    pricelist.lead_id.name, quotation.lead_id.name))
            if qt and pricelist_code and qt != pricelist_code:
                raise UserError(_('Service type mismatch: pricelist is %s but quotation is %s.') % (
                    pricelist_code.upper(), qt.upper()))
            if pricelist.pol_id and quotation.freight_pol_id and pricelist.pol_id != quotation.freight_pol_id:
                raise UserError(_('POL mismatch: pricelist POL (%s) does not match quotation POL (%s).') % (
                    pricelist.pol_id.name, quotation.freight_pol_id.name))
            if pricelist.pod_id and quotation.freight_pod_id and pricelist.pod_id != quotation.freight_pod_id:
                raise UserError(_('POD mismatch: pricelist POD (%s) does not match quotation POD (%s).') % (
                    pricelist.pod_id.name, quotation.freight_pod_id.name))
        # ── FCL: Carrier → Ocean Rate, Agent → Local Charge / Exw Fee ──
        if pricelist_code == 'fcl':
            if pricelist.partner_type == 'carrier':
                # Carrier lines go to Ocean Rate
                for line in pricelist.fcl_line_ids:
                    Line.create({
                        'quotation_id': quotation.id,
                        'section': 'ocean_rate',
                        'name': line.name or '/',
                        'rate': line.rates,
                        'quantity': 1,
                        'unit': UNITS_MAP.get(line.units),
                    })
            else:
                # Agent lines go to their designated section
                for line in pricelist.fcl_local_charge_ids:
                    Line.create({
                        'quotation_id': quotation.id,
                        'section': 'local_charge',
                        'name': line.name or '/',
                        'rate': line.rates,
                        'quantity': 1,
                        'unit': UNITS_MAP.get(line.units),
                    })
                for line in pricelist.fcl_exw_fee_ids:
                    Line.create({
                        'quotation_id': quotation.id,
                        'section': 'exw_fee',
                        'name': line.name or '/',
                        'rate': line.rates,
                        'quantity': 1,
                        'unit': UNITS_MAP.get(line.units),
                    })

        # ── LCL: Carrier → lcl_rate, Agent → lcl_exw_fee / lcl_local_charge / fcl_local_charge ──
        elif pricelist_code == 'lcl':
            if pricelist.partner_type == 'carrier':
                for line in pricelist.lcl_line_ids:
                    Line.create({
                        'quotation_id': quotation.id,
                        'section': 'lcl_rate',
                        'name': line.rates_name or '/',
                        'rate': line.rates,
                        'quantity': 1,
                        'unit': UNITS_MAP.get(line.units),
                    })
            else:
                AGENT_SECTIONS = {
                    'lcl_exw_fee': 'lcl_exw_fee',
                    'lcl_local_charge': 'lcl_local_charge',
                    'fcl_local_charge': 'fcl_local_charge',
                }
                for lcl_section, qt_section in AGENT_SECTIONS.items():
                    lines = pricelist.lcl_line_ids.filtered(lambda l, s=lcl_section: l.section == s)
                    for line in lines:
                        Line.create({
                            'quotation_id': quotation.id,
                            'section': qt_section,
                            'name': line.rates_name or '/',
                            'rate': line.rates,
                            'quantity': 1,
                            'unit': UNITS_MAP.get(line.units),
                        })

        # ── Air: Carrier → air_rate, Agent → air_local_charge / air_exw_fee ──
        elif pricelist_code == 'air':
            if pricelist.partner_type == 'carrier':
                chargeable = max(quotation.freight_weight or 0.0, quotation.freight_volume or 0.0)
                for line in pricelist.air_line_ids:
                    if chargeable >= 1000:
                        rate = line.kg_plus_1000
                    elif chargeable >= 500:
                        rate = line.kg_plus_500
                    elif chargeable >= 300:
                        rate = line.kg_plus_300
                    elif chargeable >= 100:
                        rate = line.kg_plus_100
                    elif chargeable >= 45:
                        rate = line.kg_plus_45
                    else:
                        rate = line.kg_minus_45
                    Line.create({
                        'quotation_id': quotation.id,
                        'section': 'air_rate',
                        'name': line.name or '/',
                        'rate': rate,
                        'quantity': 1,
                    })
            else:
                for line in pricelist.air_local_charge_ids:
                    Line.create({
                        'quotation_id': quotation.id,
                        'section': 'air_local_charge',
                        'name': line.name or '/',
                        'rate': line.rates,
                        'quantity': 1,
                        'unit': UNITS_MAP.get(line.units),
                    })
                for line in pricelist.air_exw_fee_ids:
                    Line.create({
                        'quotation_id': quotation.id,
                        'section': 'air_exw_fee',
                        'name': line.name or '/',
                        'rate': line.rates,
                        'quantity': 1,
                        'unit': UNITS_MAP.get(line.units),
                    })

        # ── Trucking: Carrier → trucking_rate, Agent → trucking_surcharge ──
        elif pricelist_code == 'trucking':
            chargeable = max(quotation.freight_weight or 0.0, quotation.freight_volume or 0.0)
            ftl = quotation.freight_ftl
            if pricelist.partner_type == 'carrier':
                for line in pricelist.trucking_line_ids:
                    if ftl == '20dc':
                        rate = line.dc_20
                    elif ftl == '40hc':
                        rate = line.dc_40
                    elif chargeable <= 1500:
                        rate = line.truck_1_5t
                    elif chargeable <= 3500:
                        rate = line.truck_3_5t
                    else:
                        rate = line.truck_5t
                    Line.create({
                        'quotation_id': quotation.id,
                        'section': 'trucking_rate',
                        'name': line.name or '/',
                        'rate': rate,
                        'quantity': 1,
                    })
            else:
                for line in pricelist.trucking_agent_line_ids:
                    if ftl == '20dc':
                        rate = line.dc_20
                    elif ftl == '40hc':
                        rate = line.dc_40
                    elif chargeable <= 3:
                        rate = line.cbm_1_3
                    elif chargeable <= 5:
                        rate = line.cbm_3_5
                    else:
                        rate = line.cbm_5_10
                    Line.create({
                        'quotation_id': quotation.id,
                        'section': 'trucking_surcharge',
                        'name': line.name or '/',
                        'rate': rate,
                        'quantity': 1,
                    })

        return {
            'type': 'ir.actions.act_window',
            'name': quotation.name,
            'res_model': 'crm.lead.quotation',
            'res_id': quotation.id,
            'view_mode': 'form',
            'target': 'current',
        }


class FreightPricelistImport(models.Model):
    _inherit = 'master.freight.pricelist'

    def action_open_import_wizard(self):
        self.ensure_one()
        # If coming from a quotation's "Retrieve Rates", auto-import directly
        quotation_id = self.env.context.get('default_import_quotation_id')
        if quotation_id:
            wizard = self.env['freight.pricelist.import.wizard'].create({
                'pricelist_id': self.id,
                'quotation_id': quotation_id,
            })
            return wizard.action_import()
        # Otherwise, open the wizard to select a quotation
        return {
            'name': _('Import to Quotation'),
            'type': 'ir.actions.act_window',
            'res_model': 'freight.pricelist.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_pricelist_id': self.id},
        }

    def action_open_rates_import_wizard(self):
        self.ensure_one()
        return {
            'name': _('Import Rates'),
            'type': 'ir.actions.act_window',
            'res_model': 'freight.pricelist.rates.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_pricelist_id': self.id},
        }
