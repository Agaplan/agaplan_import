from osv import osv, fields

class import_log(osv.osv):
    _name = 'import.log'

    _columns = {
        'orig_mail_id': fields.many2one('mailgate.message', 'Original Email'),
        'profile_id': fields.many2one('import.profile', 'Profile used'),
        'notes': fields.text('Notes'),
    }
import_log()

class import_log_line(osv.osv):
    _name = 'import.log.line'

    _columns = {
        'log_id': fields.many2one('import.log', 'Log'),
        'model_id': fields.many2one('ir.model', 'Model'),
        'res_id': fields.integer('Record id'),
        'xml_id': fields.char('XML id', size=128),
    }
import_log_line()
