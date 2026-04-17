{
    'name': 'Freight_Forwarding Home Dashboard',
    'version': '19.0.1.0.0',
    'category': 'Freight_Forwarding Logistics',
    'summary': 'Home landing page with module shortcuts for employees',
    'author': 'Freight_Forwarding Logistics',
    'depends': ['web', 'sale_management', 'crm', 'contacts', 'freight_forwarding_freight', 'freight_forwarding_crm', 'freight_forwarding_master_data',
                'calendar', 'mail', 'spreadsheet_dashboard', 'account', 'utm'],
    'data': [
        'views/home_action.xml',
        'views/menu_reorder.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'freight_forwarding_home/static/src/js/home_dashboard.js',
            'freight_forwarding_home/static/src/xml/home_dashboard.xml',
            'freight_forwarding_home/static/src/scss/home_dashboard.scss',
        ],
    },
    'post_init_hook': '_set_home_action',
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
