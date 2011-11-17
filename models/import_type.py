from osv import osv, fields

import logging
log = logging.getLogger('import.type')

class import_type(osv.osv):
    _name = 'import.type'

    def _get_parser_list(self, cursor, uid, context=None):
        if context is None:
            context = {}

        res = []
        ip_obj = self.pool.get('import.parser')
        parser_ids = ip_obj.search(cursor, uid, [], context=context)
        for parser in ip_obj.browse(cursor, uid, parser_ids, context=context):
            res += [(parser.id, parser.name)]
        return res

    _columns = {
        'name': fields.char('Name', size=64),
        'parser_id': fields.many2one('import.parser', selection=_get_parser_list, required=True, string='Parser'),
        'multi_record': fields.boolean('Multiple Records'),
        'arguments': fields.one2many('import.type.argument', 'type_id', 'Arguments'),
        'file_header': fields.text('File Header'),
        'file_footer': fields.text('File Footer'),
    }

    def get_parser(self, cursor, uid, ids, context=None):
        if len(ids) > 1:
            raise TypeError("Cannot fetch parser for multiple types at once.")

        me = self.browse(cursor, uid, ids, context)[0]
        arguments = {}
        for arg in me.arguments:
            arguments.update({
                arg.argument_id.name: arg.value
            })
        log.info("Creating a parser instance of type %s with arguments %s" % (me.parser_id.name, arguments))
        return me.parser_id.get_parser(arguments,context)

import_type()

class import_type_arg(osv.osv):
    _name = 'import.type.argument'

    _columns = {
        'argument_id': fields.many2one('import.parser.argument', 'Argument'),
        'type_id': fields.many2one('import.type', 'Import Type'),
        'value': fields.char('Value', size=64),
    }

    def check_argument(self, cursor, uid, ids, context=None):
        res = True
        for type_arg in self.browse(cursor, uid, ids, context):
            res = res & type_arg.argument_id.validate( type_arg.value ).values()[0]
        return res

    _constraints = [
        (check_argument, 'The argument value was not valid', ['argument_id', 'value']),
    ]
import_type_arg()
