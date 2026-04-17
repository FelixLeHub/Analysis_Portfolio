{
    'name': 'Freight_Forwarding Freight UAT Data',
    'version': '1.0',
    'category': 'Operations/Logistics',
    'summary': 'UAT seed data for freight UI testing',
    'author': 'Freight_Forwarding Logistics',
    'depends': ['account', 'mock_data', 'freight_forwarding_freight'],
    'data': [
        'data/res_partner_data.xml',
        'data/logistics_uat_data.xml',
        'data/logistics_quotation_uat_data.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
