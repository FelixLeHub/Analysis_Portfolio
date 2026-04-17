from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestLogisticsJobQuotation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Quotation Customer'})

    def _create_job(self, service_type, **extra_vals):
        values = {
            'service_type': service_type,
            'customer_id': self.partner.id,
            'pol': 'SIN',
            'pod': 'SGN',
            'place_of_delivery': 'HCM',
            'commodity': 'General Cargo',
        }
        values.update(extra_vals)
        return self.env['logistics.job'].create(values)

    def _create_rate_line(self, job, section_code, **extra_vals):
        values = {
            'job_id': job.id,
            'section_code': section_code,
            'name': f'{section_code} line',
        }
        values.update(extra_vals)
        return self.env['logistics.job.quote.rate.line'].create(values)

    def _create_charge_line(self, job, section_code, **extra_vals):
        values = {
            'job_id': job.id,
            'section_code': section_code,
            'name': f'{section_code} charge',
        }
        values.update(extra_vals)
        return self.env['logistics.job.quote.charge.line'].create(values)

    def test_default_quotation_layout_mapping(self):
        expected_layouts = {
            'trucking': 'trucking_customs',
            'sea_lcl': 'sea_lcl',
            'sea_fcl_import': 'sea_fcl',
            'sea_fcl_export': 'sea_fcl',
            'air': 'air',
        }
        for service_type, expected_layout in expected_layouts.items():
            job = self._create_job(service_type)
            self.assertEqual(job.quotation_layout, expected_layout)

    def test_action_print_quotation_opens_review_form(self):
        job = self._create_job('air')
        action = job.action_print_quotation()
        self.assertEqual(action['res_id'], job.id)
        self.assertEqual(
            action['view_id'],
            self.env.ref('freight_forwarding_freight.view_logistics_job_quotation_review_form').id,
        )

    def test_action_download_quotation_pdf_routes_to_expected_report(self):
        job = self._create_job('air')
        action = job.action_download_quotation_pdf()
        expected_action = self.env.ref(
            'freight_forwarding_freight.action_report_logistics_job_quotation_air'
        ).report_action(job)
        self.assertEqual(action, expected_action)

    def test_quotation_review_html_embeds_report_preview(self):
        job = self._create_job('sea_lcl')
        self.assertIn(
            '/report/html/freight_forwarding_freight.report_logistics_job_quotation_sea_lcl/%s' % job.id,
            job.quotation_review_html,
        )

    def test_service_type_write_updates_default_layout(self):
        job = self._create_job('sea_lcl')
        job.write({'service_type': 'trucking'})
        self.assertEqual(job.quotation_layout, 'trucking_customs')
        self.assertEqual(job.service_mode, 'trucking')
        self.assertEqual(job.direction, 'export')

    def test_quotation_layout_sets_service_type_for_simple_flows(self):
        job = self._create_job('trucking')
        job.write({'quotation_layout': 'air', 'service_type': False})
        self.assertEqual(job.service_type, 'air')
        self.assertEqual(job.service_mode, 'air')
        self.assertEqual(job.direction, 'export')

    def test_system_fields_follow_service_type_mapping(self):
        export_job = self._create_job('sea_fcl_export')
        self.assertEqual(export_job.service_mode, 'fcl')
        self.assertEqual(export_job.direction, 'export')

        import_job = self._create_job('sea_fcl_import')
        self.assertEqual(import_job.service_mode, 'fcl')
        self.assertEqual(import_job.direction, 'import')

        lcl_job = self._create_job('sea_lcl')
        self.assertEqual(lcl_job.service_mode, 'lcl')
        self.assertEqual(lcl_job.direction, 'export')

    def test_writing_system_fields_updates_backend_service_type_and_layout(self):
        job = self._create_job('sea_lcl')
        job.write({'service_mode': 'fcl', 'direction': 'import'})
        self.assertEqual(job.service_type, 'sea_fcl_import')
        self.assertEqual(job.quotation_layout, 'sea_fcl')

        job.write({'service_mode': 'air'})
        self.assertEqual(job.service_type, 'air')
        self.assertEqual(job.quotation_layout, 'air')
        self.assertEqual(job.direction, 'import')

    def test_incoterm_field_uses_standard_trade_terms(self):
        selection = dict(self.env['logistics.job']._fields['incoterms'].selection)
        self.assertEqual(
            list(selection.keys()),
            ['EXW', 'FCA', 'FAS', 'FOB', 'CFR', 'CIF', 'CPT', 'CIP', 'DAP', 'DPU', 'DDP'],
        )

    def test_customer_onchange_prefills_attention_to(self):
        job = self.env['logistics.job'].new({
            'service_type': 'trucking',
            'customer_id': self.partner.id,
        })
        job._onchange_customer_id_quotation_contact()
        self.assertEqual(job.attention_to, self.partner.name)

    def test_salesperson_defaults_follow_current_user(self):
        job = self._create_job('air')
        partner = self.env.user.partner_id
        expected_phone = getattr(partner, 'mobile', False) or getattr(partner, 'phone', False)
        self.assertEqual(job.salesperson_name, self.env.user.name)
        self.assertEqual(job.salesperson_email, partner.email)
        self.assertEqual(job.salesperson_phone, expected_phone)

        job.write({
            'salesperson_name': False,
            'salesperson_email': False,
            'salesperson_phone': False,
        })
        self.assertEqual(job._get_salesperson_name(), self.env.user.name)
        self.assertEqual(job._get_salesperson_email(), partner.email)
        self.assertEqual(job._get_salesperson_phone(), expected_phone)

    def test_confirm_opens_operations_form(self):
        job = self._create_job('air')
        action = job.action_confirm()
        self.assertEqual(job.state, 'confirmed')
        self.assertEqual(action['res_id'], job.id)
        self.assertEqual(
            action['view_id'],
            self.env.ref('freight_forwarding_freight.view_logistics_job_operation_form').id,
        )

    def test_open_quotation_form_uses_dedicated_view(self):
        job = self._create_job('sea_lcl')
        action = job.action_open_quotation_form()
        self.assertEqual(action['res_id'], job.id)
        self.assertEqual(
            action['view_id'],
            self.env.ref('freight_forwarding_freight.view_logistics_job_quotation_form').id,
        )

    def test_fcl_totals_and_report_render(self):
        job = self._create_job('sea_fcl_export')
        self.env['logistics.job.quote.charge.line'].create([
            {
                'job_id': job.id,
                'section_code': 'fcl_local',
                'name': 'Terminal charge',
                'unit_description': 'USD / 20DC or 40HC',
                'amount_20dc': 125.0,
                'amount_40hc': 200.0,
                'include_in_total': True,
            },
            {
                'job_id': job.id,
                'section_code': 'fcl_exwork',
                'name': 'Document fee',
                'unit_description': 'USD / shipment',
                'amount': 50.0,
                'include_in_total': True,
            },
            {
                'job_id': job.id,
                'section_code': 'fcl_exwork',
                'name': 'Optional charge',
                'unit_description': 'USD / shipment',
                'amount': 20.0,
                'include_in_total': False,
            },
        ])

        totals = job._get_quote_charge_totals('fcl_local', 'fcl_exwork')
        self.assertEqual(totals['amount'], 50.0)
        self.assertEqual(totals['amount_20dc'], 125.0)
        self.assertEqual(totals['amount_40hc'], 200.0)

        html = self.env['ir.actions.report']._render_qweb_html(
            'freight_forwarding_freight.report_logistics_job_quotation_sea_fcl',
            job.ids,
        )[0]
        if isinstance(html, bytes):
            html = html.decode()

        self.assertIn('Ho Chi Minh City Office', html)
        self.assertIn('Valid to :', html)
        self.assertIn('Quotation for Seafreight', html)
        self.assertIn('TOTAL', html)

    def test_air_report_includes_lane_and_remarks(self):
        job = self._create_job('air')
        self.env['logistics.job.quote.rate.line'].create({
            'job_id': job.id,
            'section_code': 'air_rate',
            'name': 'SIN to SGN',
            'origin_code': 'SIN',
            'destination_code': 'SGN',
            'carrier_or_party': 'SQ',
            'amount_1': 1.5,
            'amount_3': 2.5,
            'amount_6': 3.5,
            'note': 'MIN',
            'transit_time': '1 day',
        })
        self.env['logistics.job.quote.charge.line'].create([
            {
                'job_id': job.id,
                'section_code': 'air_exwork',
                'name': 'Export handling',
                'unit_description': 'USD / shipment',
                'amount': 45.0,
                'remark': 'Docs included',
            },
            {
                'job_id': job.id,
                'section_code': 'air_local',
                'name': 'Destination handling',
                'amount': 30.0,
                'remark': 'At consignee side',
            },
        ])

        html = self.env['ir.actions.report']._render_qweb_html(
            'freight_forwarding_freight.report_logistics_job_quotation_air',
            job.ids,
        )[0]
        if isinstance(html, bytes):
            html = html.decode()

        self.assertIn('Lane', html)
        self.assertIn('SIN to SGN', html)
        self.assertIn('Remark', html)
        self.assertIn('Docs included', html)
        self.assertIn('At consignee side', html)

    def test_lcl_rate_line_computes_total_from_all_breakdown_amounts(self):
        job = self._create_job('sea_lcl')
        line = self._create_rate_line(
            job,
            'lcl_rate',
            amount_1=10.0,
            amount_2=5.0,
            amount_3=2.5,
            amount_4=1.5,
            amount_5=0.5,
            amount_6=0.5,
        )
        self.assertEqual(line.amount_total, 20.0)

    def test_volume_weight_363_follows_lcl_volume(self):
        job = self._create_job('sea_lcl', volume_cbm=8.41)
        self.assertAlmostEqual(job.volume_weight_363, 3052.83, places=2)

    def test_rate_line_sections_match_job_layout(self):
        sea_lcl_job = self._create_job('sea_lcl')
        self._create_rate_line(sea_lcl_job, 'lcl_rate')
        with self.assertRaises(ValidationError):
            self._create_rate_line(sea_lcl_job, 'fcl_ocean')

    def test_charge_line_sections_match_job_layout(self):
        air_job = self._create_job('air')
        self._create_charge_line(air_job, 'air_local')
        with self.assertRaises(ValidationError):
            self._create_charge_line(air_job, 'fcl_local')

    def test_rate_line_fields_get_uses_business_labels(self):
        fields_meta = self.env['logistics.job.quote.rate.line'].with_context(
            quote_section_code='truck_rate',
        ).fields_get(['name', 'amount_1', 'amount_2', 'amount_4'])
        self.assertEqual(fields_meta['name']['string'], 'Port or Airport')
        self.assertEqual(fields_meta['amount_1']['string'], 'Truck 1.5 tons')
        self.assertEqual(fields_meta['amount_2']['string'], 'Truck 3.5 tons')
        self.assertEqual(fields_meta['amount_4']['string'], '20 DC')

    def test_sea_and_air_rate_fields_get_use_detailed_labels(self):
        sea_fields = self.env['logistics.job.quote.rate.line'].with_context(
            quote_section_code='fcl_ocean',
        ).fields_get(['origin_code', 'destination_code', 'carrier_or_party', 'amount_1', 'amount_2', 'transit_time'])
        self.assertEqual(sea_fields['origin_code']['string'], 'POL')
        self.assertEqual(sea_fields['destination_code']['string'], 'POD')
        self.assertEqual(sea_fields['carrier_or_party']['string'], 'Carrier')
        self.assertEqual(sea_fields['amount_1']['string'], "20'DC")
        self.assertEqual(sea_fields['amount_2']['string'], "40'HC")
        self.assertEqual(sea_fields['transit_time']['string'], 'T/T')

        air_fields = self.env['logistics.job.quote.rate.line'].with_context(
            quote_section_code='air_rate',
        ).fields_get(['origin_code', 'destination_code', 'carrier_or_party', 'amount_1', 'amount_3', 'amount_6', 'note'])
        self.assertEqual(air_fields['origin_code']['string'], 'AOL')
        self.assertEqual(air_fields['destination_code']['string'], 'AOD')
        self.assertEqual(air_fields['carrier_or_party']['string'], 'Carrier')
        self.assertEqual(air_fields['amount_1']['string'], '- 45 kgs')
        self.assertEqual(air_fields['amount_3']['string'], '+ 100 kgs')
        self.assertEqual(air_fields['amount_6']['string'], '+ 1000 kgs')
        self.assertEqual(air_fields['note']['string'], 'FRE')

    def test_charge_line_fields_get_uses_business_labels(self):
        fields_meta = self.env['logistics.job.quote.charge.line'].with_context(
            quote_section_code='fcl_local',
        ).fields_get(['name', 'unit_description', 'amount_20dc', 'amount_40hc'])
        self.assertEqual(fields_meta['name']['string'], 'Detail Charge')
        self.assertEqual(fields_meta['unit_description']['string'], 'Unit Price')
        self.assertEqual(fields_meta['amount_20dc']['string'], "20'DC")
        self.assertEqual(fields_meta['amount_40hc']['string'], "40'HC")

    def test_layout_change_with_incompatible_lines_raises_clear_error(self):
        job = self._create_job('sea_fcl_export')
        self._create_rate_line(job, 'fcl_ocean')
        self._create_charge_line(job, 'fcl_local')

        with self.assertRaisesRegex(
            UserError,
            'Cannot change quotation layout to "Airfreight" because this quotation still contains lines for: FCL Ocean Rate, FCL Local Charge',
        ):
            job.write({'quotation_layout': 'air', 'service_type': False})

    def test_lcl_report_only_shows_local_charge_for_lcl_section(self):
        job = self._create_job('sea_lcl')
        self._create_charge_line(job, 'lcl_local_fcl', name='Hidden FCL local charge', amount_20dc=10.0)
        self._create_charge_line(
            job,
            'lcl_local_lcl',
            name='Visible LCL local charge',
            unit_description='BL',
            amount=20.0,
        )

        html = self.env['ir.actions.report']._render_qweb_html(
            'freight_forwarding_freight.report_logistics_job_quotation_sea_lcl',
            job.ids,
        )[0]
        if isinstance(html, bytes):
            html = html.decode()

        self.assertIn('Local charge for LCL', html)
        self.assertIn('Visible LCL local charge', html)
        self.assertNotIn('Local charge for FCL', html)
        self.assertNotIn('Hidden FCL local charge', html)

    def test_quote_line_crud_supports_all_sections(self):
        rate_sections = [
            ('trucking', 'truck_rate'),
            ('trucking', 'customs_import'),
            ('trucking', 'customs_export'),
            ('sea_lcl', 'lcl_rate'),
            ('sea_fcl_export', 'fcl_ocean'),
            ('air', 'air_rate'),
        ]
        charge_sections = [
            ('sea_lcl', 'lcl_exwork'),
            ('sea_lcl', 'lcl_local_fcl'),
            ('sea_lcl', 'lcl_local_lcl'),
            ('sea_fcl_export', 'fcl_local'),
            ('sea_fcl_export', 'fcl_exwork'),
            ('air', 'air_exwork'),
            ('air', 'air_local'),
        ]

        for service_type, section_code in rate_sections:
            job = self._create_job(service_type)
            line = self._create_rate_line(job, section_code)
            line.write({
                'name': f'Updated {section_code}',
                'amount_1': 100.0,
                'amount_2': 200.0,
                'origin_code': 'SGN',
                'destination_code': 'LAX',
            })
            self.assertEqual(line.name, f'Updated {section_code}')
            self.assertEqual(line.amount_1, 100.0)
            line.unlink()
            self.assertFalse(line.exists())

        for service_type, section_code in charge_sections:
            job = self._create_job(service_type)
            line = self._create_charge_line(job, section_code)
            line.write({
                'name': f'Updated {section_code}',
                'amount': 50.0,
                'amount_20dc': 75.0,
                'amount_40hc': 90.0,
                'remark': 'Updated',
            })
            self.assertEqual(line.name, f'Updated {section_code}')
            self.assertEqual(line.remark, 'Updated')
            line.unlink()
            self.assertFalse(line.exists())

    def test_quotation_form_arch_uses_detailed_service_layouts(self):
        arch = self.env.ref('freight_forwarding_freight.view_logistics_job_quotation_form').arch_db
        lcl_page_start = arch.index('page string="1. Rate for LCL Shipment"')
        lcl_list_start = arch.index('<list editable="bottom" open_form_view="True" create="1" delete="1">', lcl_page_start)
        lcl_list_end = arch.index('</list>', lcl_list_start)
        lcl_list_arch = arch[lcl_list_start:lcl_list_end]
        self.assertIn('o_freight_forwarding_bottom_chatter_form', arch)
        self.assertIn('Shipment Parties', arch)
        self.assertNotIn('Sales Contact', arch)
        self.assertNotIn('Internal Notes', arch)
        self.assertNotIn('Introduction', arch)
        self.assertNotIn('Footer Note', arch)
        self.assertNotIn('Closing', arch)
        self.assertNotIn('field name="quotation_footer_note"', arch)
        self.assertNotIn('field name="quotation_intro"', arch)
        self.assertNotIn('field name="salesperson_email"', arch)
        self.assertIn('field name="routing_summary" invisible="1"', arch)
        self.assertIn('Trucking &amp; Customs Summary', arch)
        self.assertIn('LCL Shipment Summary', arch)
        self.assertIn('FCL Shipment Summary', arch)
        self.assertIn('Air Shipment Summary', arch)
        self.assertIn('field name="factory_name"', arch)
        self.assertIn('field name="weight_kgs"', arch)
        self.assertIn('field name="volume_weight_363"', arch)
        self.assertIn('field name="incoterms"', arch)
        self.assertIn('page string="1. Rate for LCL Shipment"', arch)
        self.assertIn('page string="3. Local Charge for LCL"', arch)
        self.assertNotIn('page string="3. Local Charge for FCL"', arch)
        self.assertNotIn('page string="4. Local Charge for LCL"', arch)
        self.assertIn('page string="1. Rate for Airfreight"', arch)
        self.assertIn('page string="2. Import Customs Fee"', arch)
        self.assertIn('page string="3. Export Customs Fee"', arch)
        self.assertIn('page string="2. Ex-work at Airport of Loading"', arch)
        self.assertIn('page string="3. Local Charge at Airport of Delivery"', arch)
        self.assertIn('open_form_view="True"', arch)
        self.assertIn('field name="direction"', arch)
        self.assertIn('field name="service_mode" string="Service Type"', arch)
        self.assertIn('field name="lcl_rate_line_ids"', arch)
        self.assertIn('field name="lcl_exwork_line_ids"', arch)
        self.assertIn('field name="lcl_local_lcl_line_ids"', arch)
        self.assertIn('field name="name" string="Country"', lcl_list_arch)
        self.assertIn('field name="origin_code" string="POL"', lcl_list_arch)
        self.assertIn('field name="destination_code" string="POD"', lcl_list_arch)
        self.assertIn('field name="amount_1" string="Rate"', lcl_list_arch)
        self.assertIn('field name="amount_2" string="CFS"', lcl_list_arch)
        self.assertIn('field name="amount_3" string="THC"', lcl_list_arch)
        self.assertIn('field name="amount_4" string="CIC"', lcl_list_arch)
        self.assertIn('field name="amount_5" string="CLS"', lcl_list_arch)
        self.assertIn('field name="amount_6" string="FRE"', lcl_list_arch)
        self.assertNotIn('field name="carrier_or_party" string="Carrier"', lcl_list_arch)
        self.assertIn('field name="carrier_or_party" string="Carrier"', arch)
        self.assertIn('field name="amount_total" string="Total"', arch)
        self.assertIn('field name="name" string="Lane"', arch)
        self.assertIn('field name="amount_2" string="CFS"', arch)
        self.assertIn('field name="amount_2" string="+ 45 kgs"', arch)
        self.assertIn('field name="amount_4" string="+ 300 kgs"', arch)
        self.assertIn('field name="amount_5" string="+ 500 kgs"', arch)
        self.assertIn('field name="amount_6" string="+ 1000 kgs"', arch)
        self.assertIn('field name="note" string="FRE"', arch)
        self.assertIn('field name="unit_description" string="Unit Price"', arch)
        self.assertIn('field name="frequency" string="Frequency"', arch)

    def test_operations_form_arch_uses_bottom_chatter_layout(self):
        arch = self.env.ref('freight_forwarding_freight.view_logistics_job_operation_form').arch_db
        self.assertIn('o_freight_forwarding_bottom_chatter_form', arch)
        self.assertIn('Quotation Snapshot', arch)
        self.assertIn('field name="factory_name"', arch)
        self.assertIn('field name="weight_kgs"', arch)
        self.assertIn('group string="Quotation Notes" invisible="1"', arch)
        self.assertIn('page string="Notes" name="notes" invisible="1"', arch)
        self.assertNotIn('group string="Sales Contact"', arch)

    def test_review_form_arch_exposes_preview_and_download(self):
        arch = self.env.ref('freight_forwarding_freight.view_logistics_job_quotation_review_form').arch_db
        self.assertIn('field name="quotation_review_html"', arch)
        self.assertIn('button name="action_download_quotation_pdf"', arch)
        self.assertIn('Back to Quotation', arch)
