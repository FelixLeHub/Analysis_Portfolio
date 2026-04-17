from datetime import date
import logging

_logger = logging.getLogger(__name__)


def _create_mock_accounting_data(env):
    """Create mock accounting data after module installation."""
    company = env['res.company'].search([], limit=1)

    # Ensure company has a country (needed for chart of accounts)
    if not company.country_id:
        us_country = env['res.country'].search([('code', '=', 'US')], limit=1)
        if us_country:
            company.write({
                'country_id': us_country.id,
                'account_fiscal_country_id': us_country.id,
            })
            env.cr.flush()

    # Try to install a chart of accounts template if none exists
    sale_journal = env['account.journal'].search([
        ('type', '=', 'sale'),
        ('company_id', '=', company.id),
    ], limit=1)

    if not sale_journal:
        try:
            company.chart_template = 'generic_coa'
            env['account.chart.template'].try_loading('generic_coa', company, install_demo=False)
        except Exception as e:
            _logger.warning("Could not load chart of accounts: %s", e)
            return

    # Re-search journals after chart loading
    sale_journal = env['account.journal'].search([
        ('type', '=', 'sale'),
        ('company_id', '=', company.id),
    ], limit=1)

    purchase_journal = env['account.journal'].search([
        ('type', '=', 'purchase'),
        ('company_id', '=', company.id),
    ], limit=1)

    if not sale_journal or not purchase_journal:
        _logger.warning("No sale/purchase journal found, skipping invoice creation")
        return

    # Find income and expense accounts for invoice lines
    income_account = env['account.account'].search([
        ('company_ids', 'in', company.id),
        ('account_type', '=', 'income'),
    ], limit=1)

    expense_account = env['account.account'].search([
        ('company_ids', 'in', company.id),
        ('account_type', '=', 'expense'),
    ], limit=1)

    if not income_account or not expense_account:
        _logger.warning("No income/expense accounts found, skipping invoice creation")
        return

    # Get partner references
    partner_customer_1 = env.ref('mock_data.partner_customer_1')
    partner_customer_2 = env.ref('mock_data.partner_customer_2')
    partner_customer_3 = env.ref('mock_data.partner_customer_3')
    partner_supplier_1 = env.ref('mock_data.partner_supplier_1')
    partner_supplier_2 = env.ref('mock_data.partner_supplier_2')
    partner_supplier_3 = env.ref('mock_data.partner_supplier_3')

    # Get product references
    product_consulting = env.ref('mock_data.product_consulting')
    product_support = env.ref('mock_data.product_support')
    product_training = env.ref('mock_data.product_training')
    product_laptop = env.ref('mock_data.product_laptop')
    product_monitor = env.ref('mock_data.product_monitor')
    product_office_chair = env.ref('mock_data.product_office_chair')

    AccountMove = env['account.move'].with_company(company)

    # Customer Invoice #1 - Acme Corporation
    inv1 = AccountMove.create({
        'move_type': 'out_invoice',
        'partner_id': partner_customer_1.id,
        'invoice_date': date(2026, 1, 15),
        'date': date(2026, 1, 15),
        'journal_id': sale_journal.id,
        'invoice_line_ids': [
            (0, 0, {
                'name': 'IT Consulting Service - January',
                'product_id': product_consulting.id,
                'account_id': income_account.id,
                'quantity': 40,
                'price_unit': 150.00,
            }),
            (0, 0, {
                'name': 'Business Laptop Pro',
                'product_id': product_laptop.id,
                'account_id': income_account.id,
                'quantity': 5,
                'price_unit': 1299.99,
            }),
        ],
    })

    # Customer Invoice #2 - Global Tech Solutions
    inv2 = AccountMove.create({
        'move_type': 'out_invoice',
        'partner_id': partner_customer_2.id,
        'invoice_date': date(2026, 2, 1),
        'date': date(2026, 2, 1),
        'journal_id': sale_journal.id,
        'invoice_line_ids': [
            (0, 0, {
                'name': 'Technical Support - February',
                'product_id': product_support.id,
                'account_id': income_account.id,
                'quantity': 80,
                'price_unit': 75.00,
            }),
            (0, 0, {
                'name': '27 inch 4K Monitor',
                'product_id': product_monitor.id,
                'account_id': income_account.id,
                'quantity': 10,
                'price_unit': 449.99,
            }),
        ],
    })

    # Customer Invoice #3 - Prime Industries
    inv3 = AccountMove.create({
        'move_type': 'out_invoice',
        'partner_id': partner_customer_3.id,
        'invoice_date': date(2026, 3, 1),
        'date': date(2026, 3, 1),
        'journal_id': sale_journal.id,
        'invoice_line_ids': [
            (0, 0, {
                'name': 'Employee Training Program',
                'product_id': product_training.id,
                'account_id': income_account.id,
                'quantity': 3,
                'price_unit': 500.00,
            }),
            (0, 0, {
                'name': 'Ergonomic Office Chair',
                'product_id': product_office_chair.id,
                'account_id': income_account.id,
                'quantity': 15,
                'price_unit': 599.00,
            }),
        ],
    })

    # Vendor Bill #1 - Office Supplies Co.
    bill1 = AccountMove.create({
        'move_type': 'in_invoice',
        'partner_id': partner_supplier_1.id,
        'invoice_date': date(2026, 1, 10),
        'date': date(2026, 1, 10),
        'journal_id': purchase_journal.id,
        'invoice_line_ids': [
            (0, 0, {
                'name': 'Office Supplies - Q1 Bulk Order',
                'account_id': expense_account.id,
                'quantity': 1,
                'price_unit': 2500.00,
            }),
            (0, 0, {
                'name': 'Printer Paper (500 reams)',
                'account_id': expense_account.id,
                'quantity': 500,
                'price_unit': 5.50,
            }),
        ],
    })

    # Vendor Bill #2 - TechParts International
    bill2 = AccountMove.create({
        'move_type': 'in_invoice',
        'partner_id': partner_supplier_2.id,
        'invoice_date': date(2026, 2, 15),
        'date': date(2026, 2, 15),
        'journal_id': purchase_journal.id,
        'invoice_line_ids': [
            (0, 0, {
                'name': 'Server Components',
                'account_id': expense_account.id,
                'quantity': 4,
                'price_unit': 3200.00,
            }),
            (0, 0, {
                'name': 'Network Equipment',
                'account_id': expense_account.id,
                'quantity': 2,
                'price_unit': 1800.00,
            }),
        ],
    })

    # Vendor Bill #3 - Raw Materials Inc.
    bill3 = AccountMove.create({
        'move_type': 'in_invoice',
        'partner_id': partner_supplier_3.id,
        'invoice_date': date(2026, 3, 5),
        'date': date(2026, 3, 5),
        'journal_id': purchase_journal.id,
        'invoice_line_ids': [
            (0, 0, {
                'name': 'Raw Materials - Steel',
                'account_id': expense_account.id,
                'quantity': 100,
                'price_unit': 45.00,
            }),
            (0, 0, {
                'name': 'Raw Materials - Aluminum',
                'account_id': expense_account.id,
                'quantity': 50,
                'price_unit': 72.00,
            }),
        ],
    })

    # Confirm Invoice #1 so there's a posted invoice for testing
    try:
        inv1.action_post()
    except Exception as e:
        _logger.warning("Could not post invoice: %s", e)

    _logger.info("Mock accounting data created successfully: 3 invoices, 3 vendor bills")
