from osv import osv, fields
from tools.translate import _

import base64
import logging
log = logging.getLogger('import.profile')

class import_profile(osv.osv):
    _name = 'import.profile'

    _columns = {
        'name': fields.char('Name', size=64),
        'type_id': fields.many2one('import.type', 'Import Type'),
        'line_ids': fields.one2many('import.profile.line', 'profile_id', 'Profile lines'),
    }

    def action_process(self, cursor, uid, ids, filedata, filename, context=None):
        """
            This action is called from an import wizard, it should return data
            that will be written into the osv_memory object 'import.wizard.record'
            to allow the user to verify data before importing.

            Individual records can have notes and this field should be filled
            with any remarks about the imported record.
        """

        prof_line = self.pool.get('import.profile.line')

        res = []
        for imp_profile in self.browse(cursor, uid, ids, context):
            imp_type = imp_profile.type_id
            imp_parser = imp_type.get_parser(context)

            res += imp_parser.parse( filename, base64.b64decode(filedata), imp_profile )
        return res
import_profile()

class import_profile_line(osv.osv):
    _name = 'import.profile.line'

    _order = 'sequence, id'

    def _get_actions(self, cursor, uid, context=None):
        res = (
            ('skip', 'Skip'),
            ('xmlid', 'XML Id'),
            ('field', 'Field'),
            ('record','Record'),
        )
        return res

    def _check_profile(self, cursor, uid, ids, context):
        """ self is 'import.profile' model """
        res = []
        for profile in self.browse(cursor, uid, ids, context):
            res += [ x.id for x in profile.line_ids ]
        return res

    def _get_line_name(self, cursor, uid, ids, field_name, arg, context=None):
        res = {}
        for line in self.browse(cursor, uid, ids, context):
            names = []
            if line.model_id:
                names += [line.model_id.name]
            if line.field_id:
                names += [line.field_id.name]
            res[line.id] = " ".join([line.action, " ".join(names), line.sub_action or 'value'])
            res[line.id] = res[line.id][:64]
        return res

    _columns = {
        'name': fields.function(_get_line_name, method=True, type='char', size=64, string='Name', store={
            'import.profile.line': (lambda self,cursor,uid,ids,context: ids, ['profile_id', 'action', 'sub_action', 'parent_id'], 10),
            'import.profile': (_check_profile, ['name'], 20),
        }),
        'profile_id': fields.many2one('import.profile', 'Import Profile', required=True, ondelete='cascade'),
        'parent_id': fields.many2one('import.profile.line', 'Parent', ondelete='restrict'),
        'child_ids': fields.one2many('import.profile.line', 'parent_id', 'Child lines'),
        'sequence': fields.integer('Sequence'),
        'action': fields.selection(_get_actions, 'Action',
            help="Field: uses the value in the import for the current field value (No child lines allowed)" \
                "Record: create a new record for the parent field (Child lines required)" # \
                #"Match: search in the related field for this xml_id or database id. (No child lines allowed)" \
        ),
        'sub_action': fields.selection( (('findid','Find ID'),('find','Find fields'),('create','Create')), 'Subaction',
            help="Find ID: Takes field value and tries to match it to an existing model using xml_id or database id" \
                "Find fields: Looks at the child fields and tries to match those in the related model" \
                "Create: Creates a new record using the child field definitions"
        ),
        'model_id': fields.many2one('ir.model', 'Model'),
        'field_id': fields.many2one('ir.model.fields', 'Field'),
        'include_func': fields.text('Include Function'),
        'value_func': fields.text('Value Function'),
    }
import_profile_line()
