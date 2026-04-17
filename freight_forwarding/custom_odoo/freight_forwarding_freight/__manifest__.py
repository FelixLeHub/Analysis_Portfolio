{
    'name': 'Freight_Forwarding Freight Management',
    'version': '19.0.2.0.0',
    'category': 'Operations/Logistics',
    'summary': 'Logistics job management with agent and customer debit notes',
    'author': 'Freight_Forwarding Logistics',
    'depends': ['account', 'mail', 'crm', 'freight_forwarding_master_data'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/logistics_charge_type_data.xml',
        'views/logistics_charge_type_views.xml',
        'views/logistics_job_views.xml',
        'views/logistics_agent_debit_note_views.xml',
        'views/logistics_customer_debit_note_views.xml',
        'views/account_move_views.xml',
        'report/logistics_job_quotation_report.xml',
        'wizard/retrieve_rates_wizard_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'freight_forwarding_freight/static/src/scss/logistics_job_form.scss',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
