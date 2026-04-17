{
    'name': 'Mock Test Data',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Mock data for testing: accounts, partners, products, invoices, payments, and test user',
    'author': 'Freight_Forwarding Logistics',
    'description': """
        This module creates mock data for testing purposes:
        - Chart of accounts (additional test accounts)
        - Partners (customers and suppliers)
        - Products
        - Customer invoices and vendor bills
        - Payments
        - Test user account with full access
    """,
    'depends': ['account', 'product', 'crm', 'freight_forwarding_crm'],
    'data': [
        'security/ir.model.access.csv',
        'data/res_users_data.xml',
        'data/res_partner_data.xml',
        'data/product_data.xml',
        'data/crm_lead_data.xml',
    ],
    'post_init_hook': '_create_mock_accounting_data',
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
