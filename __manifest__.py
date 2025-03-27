{
    'name': 'Reconciliação',
    'version': '13.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Reconciliation of accounts',
    'description': """
        Standalone Banking Reconciliation System
        
        Features:
        - Custom bank statement management
        - Account reconciliation
        - Transaction matching
    """,
    'author': 'Saturnino Moreira Mendes',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/reconciliation_view.xml',
        'views/account_view.xml',
        'views/swift_view.xml',
        'views/nostro__swift_view.xml',
        'views/components/reconciliation_template.xml',
        'views/nostro_view.xml',
        'views/wizards/reconciliation_wizards_view.xml',
        'views/components/overrides.xml',
        'views/movimento_nostro_view.xml',
        # 'views/movimento_vostro_view.xml',
        # 'config/title.xml',
        # 'views/vostro_view.xml',
        # 'views/reconciliation_template.xml',
        # 'views/template/vostro_main_template.xml',
    ],
    'installable': True,
    # 'auto_install': False,
    'application': True,
    'sequence': 1,

    'images': [
        'static/description/icon.png',
    ],

    # 'qweb': [
    #     'static/src/xml/reconciliation.xml',
    #     'static/src/xml/vostro.xml',
    # ],

    # 'assets': {
    #     'web.assets_backend': [
    #         # '/reconciliation/static/src/css/menu_view.css',
    #         '/reconciliation/static/src/css/global.css',
    #         '/reconciliation/static/src/js/static_view.js', 
    #         '/reconciliation/static/src/js/static_reconciliation.js', 
    #         # '/reconciliation/static/src/js/reconciliation/reconciliation_interface.js'
    #     ],
    # },
    'assets': {
        'web.assets_backend': [
            # 'reconciliation/static/src/js/static_reconciliation.js',
        ],
    },
        
}

