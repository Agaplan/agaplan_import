from osv import osv, fields
from tools.translate import _

import logging
log = logging.getLogger('import.wizard')

class import_wizard(osv.osv_memory):
    _name = 'import.wizard'

    _columns = {
        'profile_id': fields.many2one('import.profile', 'Profile'),
        'filedata': fields.binary('File'),
        'filename': fields.char('Filename', size=128),
        'record_ids': fields.one2many('import.wizard.record', 'import_id', 'Imported Records'),
        'notes': fields.text('Notes'),
    }

    _defaults = {
        'profile_id': lambda self,cursor,uid,context: context.get('active_model') == 'import.profile' and context.get('active_id'),
    }

    def action_process(self, cursor, uid, ids, context=None):
        wiz = self.browse(cursor, uid, ids, context)[0]
        imp_profile = wiz.profile_id
        try:
            res = imp_profile.action_process(wiz.filedata, wiz.filename, context=context)
        except osv.except_osv, e:
            raise e
        except Exception, e:
            log.error("Import failed", exc_info=True)
            raise osv.except_osv( _("Import failed"), _("The import has failed: %s") % e )

        wiz.write({
            'notes': 'Processed',
            'record_ids': res,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'import.wizard',
            'res_id': wiz.id,
            'view_id': self.pool.get('ir.ui.view').search(cursor, uid, [('name','=','import.wizard.form.check')]),
            #'agaplan_import.import_wizard_form_view_check',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    def create_update_xml(self, cursor, uid, xml_id, model_id, res_id):
        ir = self.pool.get('ir.model.data')

        module = False
        if '.' in xml_id:
            module,xml_id = xml_id.split('.')

        search_args = [
            ('model','=',model_id.model),
            ('name','=',xml_id),
            ('module','=',module),
        ]
        search_ids = ir.search(cursor, uid, search_args)
        if search_ids:
            # Exists, need to update
            # TODO check if more than one result ? -> unique key on name should prevent it
            ir.write(cursor, uid, search_ids, {'res_id': res_id})
        else:
            # Does not exist yet
            rec_value = {
                'module': module or '',
                'name': xml_id,
                'model': model_id.model,
                'res_id': res_id
            }
            ir.create(cursor, uid, rec_value)
        return True

    def action_import(self, cursor, uid, ids, context=None):
        wiz = self.browse(cursor, uid, ids, context)[0]

        remarks = []
        all_ok = True
        xml_map = dict( [(r.xml_id,r.rec_id) for r in wiz.record_ids if r.rec_id and r.xml_id] )

        for record in wiz.record_ids:
            # Get the record model pool object
            rec_model = self.pool.get(record.rec_model.model)

            # Check if the id was filled
            if record.rec_id:
                # Update this record
                for field in record.field_ids:
                    if field.field_id.ttype == 'one2many' or field.field_id.ttype == 'many2many':
                        log.warn("Not yet implemented: updating '%s' fields", field.field_id.ttype)
                        remarks.append( _("Not yet implemented: updating '%s' fields") % (field.field_id.ttype) )
                        continue
                    if field.field_id.ttype == 'many2one':
                        try:
                            rec_model.write(cursor, uid, record.rec_id, {
                                field.field_id.name: xml_map[field.value],
                            })
                            field.write({'done':True})
                        except KeyError, k:
                            log.error("Unable to update field '%s' on model '%s' to '%s' because it was not found in the xml map",
                                field.field_id.name, record.rec_model.model, field.value)
                            remarks.append( _("Unable to update field '%s' on model '%s' with value '%s' because it was not found in the xml map")
                                % ( field.field_id.name, record.rec_model.model, field.value) )
                            all_ok = False
                    else:
                        try:
                            rec_model.write(cursor, uid, record.rec_id, {
                                field.field_id.name: field.value,
                            })
                            field.write({'done':True})
                        except Exception, e:
                            log.error("Unable to update field '%s' on model '%s' to '%s'",
                                field.field_id.name, record.rec_model.model, field.value, exc_info=True)
                            all_ok = False
                record.write({'done': True})
            else:
                # Create this record
                vals = {}
                for field in record.field_ids:
                    log.info("Adding '%s' : '%s' to values", field.field_id.name, field.value)
                    val = None
                    if field.field_id.ttype == 'many2one':
                        try:
                            val = xml_map.get(field.value,None) or int(field.value)
                        except ValueError:
                            # Conversion to int failed (means there is an xml id in field.value but it was not found in xml_map)
                            log.error("Could not find '%s' xmlid in the xml_map: %s", field.value, xml_map)
                            remarks.append( _("Could not find '%s' xmlid") % (field.value) )
                            all_ok = False
                    elif field.field_id.ttype == 'many2many':
                        # TODO Add all field lines together before writing it
                        val = [(6,0,[field.value])]
                    else:
                        val = field.value
                    vals.update({
                        field.field_id.name: val
                    })
                    field.write({'done':True})
                try:
                    status = rec_model.create(cursor, uid, vals, context=context)
                    xml_map[record.xml_id] = status
                    log.debug("XML_MAP: %s", xml_map)
                    record.write({'rec_id': status, 'done':True})
                    self.create_update_xml(cursor, uid, record.xml_id, record.rec_model, status)
                except Exception, e:
                    log.error("Unable to create record in model '%s' with values '%s'", record.rec_model.model, vals, exc_info=True)
                    remarks.append( _("Unable to create record '%s' in model '%s' with values '%s': %s")
                        % ( record.xml_id, record.rec_model.model, vals, e ) )
                    all_ok = False

        if all_ok:
            return {
                'type': 'ir.actions.act_window_close',
            }
        else:
            wiz.write({'notes': '\n'.join(remarks)})
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'import.wizard',
                'res_id': wiz.id,
                'view_id': self.pool.get('ir.ui.view').search(cursor, uid, [('name','=','import.wizard.form.notes')]),
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
            }
import_wizard()

class import_wizard_record(osv.osv_memory):
    _name = 'import.wizard.record'

    _columns = {
        'import_id': fields.many2one('import.wizard', 'Import'),
        'rec_id': fields.integer('Record ID'),
        'rec_model': fields.many2one('ir.model', 'Record Model'),
        'xml_id': fields.char('XML ID', size=64),
        'notes': fields.text('Source line'),
        'field_ids': fields.one2many('import.wizard.record.value', 'record_id', 'Fields'),
        'line_id': fields.many2one('import.profile.line', 'Line'),
        'done': fields.boolean('Imported'),
    }
import_wizard_record()

class import_wizard_record_value(osv.osv_memory):
    _name = 'import.wizard.record.value'

    _columns = {
        'record_id': fields.many2one('import.wizard.record', 'Record'),
        'field_id': fields.many2one('ir.model.fields', 'Field'),
        'value': fields.char(size=256, string='Value'),
        'line_id': fields.many2one('import.profile.line', 'Line'),
        'done': fields.boolean('Imported'),
    }
import_wizard_record_value()
