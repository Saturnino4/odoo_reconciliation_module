from odoo import models, fields, api

class NostroSwift(models.Model):
    _name = 'nostro.swift'
    _description = 'Nostro Swift'

    nostro_account_id = fields.Many2one('account.account', string='Nostro Account')
    swift_id = fields.Many2one('swift.swift', string='Swift Message')
    description = fields.Char(string='Description')
    status = fields.Selection([
        ('inactive', 'Inactive'),
        ('active', 'Active'),
    ], string='Status', default='active')

    @api.model
    def create(self, vals):
        res = super(NostroSwift, self).create(vals)
        if res.swift_id:
            res.swift_id.nostro_swift_id = res.id
        return res
    
    def write(self, vals):
        res = super(NostroSwift, self).write(vals)
        if self.swift_id:
            self.swift_id.nostro_swift_id = self.id

        return res
    
    def unlink(self):
        for record in self:
            if record.swift_id:
                record.swift_id.nostro_swift_id = False
        return super(NostroSwift, self).unlink()
    

