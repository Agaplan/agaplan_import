{
    'name': 'Agaplan Import Module',
    'version': '0.1',
    'description': """
    This module allows you to import various file formats to any model.
    You have to define an import type (file definition) and an import profile.

    The import profile will define which fields to fill and which to use for
    matching existing data.
    """,
    'category': 'Generic Modules/Import',
    'author': 'Agaplan',
    'website': 'http://www.agaplan.eu',
    'depends': [
        'base',
    ],
    'init': [],
    'update_xml': [
        'agaplan_data.xml',
        'wizard/import_wizard_view.xml',
        'views/import_parser_view.xml',
        'views/import_type_view.xml',
        'views/import_profile_view.xml',
        'views/partner_view.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'test': [],
    'installable': True,
}
# vim:sts=4:et
