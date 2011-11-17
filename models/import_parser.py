from osv import osv, fields
from tools import safe_eval
from tools.translate import _

import logging
import time
import re

log = logging.getLogger('import.parser')

class ParserInst(object):
    cursor = None
    uid = None
    context = None
    pool = None

    def __init__(self, cursor, uid, context, pool):
        self.cursor = cursor
        self.uid = uid
        self.context = context or {}
        self.pool = pool

    def feed(self, name, data):
        pass

    def get_record(self):
        pass

    def get_field(self):
        pass

    def get_value(self):
        pass

class import_parser(osv.osv):
    """
    Each new import parser has to inherit from this parser and implement a
    function called 'import_<parsername>'.
    """

    _name = 'import.parser'

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'arguments': fields.one2many('import.parser.argument', 'parser_id', 'Arguments'),
    }

    _sql_constraints = [
        ('unique_name', 'unique (name)', 'Duplicate parser names are not allowed'),
    ]

    def create(self, cursor, uid, vals, context=None):
        """
            Verification if the import_* method was actually added to the model.
        """
        if not hasattr(self, 'import_'+vals['name']):
            log.error('Attempt to create a new parser record without implementing the method function import_%s' % vals['name'])
            raise osv.except_osv( _("Invalid parser"), _("The parser %s has not been properly implemented, contact the maintainer.") % (vals['name']) )
        return super(import_parser, self).create(cursor, uid, vals, context)

    def get_parser(self, cursor, uid, ids, arguments, context=None):
        if len(ids) > 1:
            raise TypeError("Cannot fetch more than one parser at a time.")

        me = self.browse(cursor, uid, ids, context)[0]
        return getattr(me, 'import_'+me.name)(arguments=arguments, context=context)

import_parser()

class import_parser_argument(osv.osv):
    _name = 'import.parser.argument'

    _columns = {
        'parser_id': fields.many2one('import.parser', 'Parser', required=True, ondelete='cascade'),
        'name': fields.char('Name', size=64, required=True),
        'default_value': fields.char('Default value', size=64), # Hard to implement ? Remove ?
        'validation_func': fields.text('Validation rule', help="You can put python code here to validate the 'argument', the 'value' is the proposed value, 'valid' must be True/False"),
    }

    def _get_validation_context(self, cursor, uid, ids, context=None):
        res = {
            're': re,
            'time': time,
            'context': context or {},
            'log': log,
        }
        return res

    def validate(self, cursor, uid, ids, value, context=None):
        res = {}
        for rec in self.browse(cursor, uid, ids, context):
            if rec.validation_func:
                try:
                    ct = self._get_validation_context(cursor, uid, ids, context)
                    ct.update({
                        '__builtins__': None,
                        'True': True,
                        'False': False,
                        'None': None,
                        'str': str,
                        'bool': bool,
                        'int': int,
                        'float': float,
                        'dict': dict,
                        'list': list,
                        'tuple': tuple,
                        'set': set,
                        'map': map,
                        'reduce': reduce,
                        'filter': filter,
                        'abs': abs,
                        'len': len,
                        'round': round,
                        'name': rec.name,
                        'argument': rec,
                        'value': value,
                        'valid': False,
                    })
                    #valid = safe_eval( rec.validation_func, ct )
                    exec rec.validation_func in ct
                    log.debug('"%s" = %s', rec.validation_func, ct['valid'])
                    res[ rec.id ] = ct['valid']
                except Exception, e:
                    log.error("Parser argument validation failed: %s", e, exc_info=True)
                    raise osv.except_osv( _("Argument validation failed"), _("The argument %s failed to validate the value:\n%s") % (rec.name, value) )
        return res
import_parser_argument()

