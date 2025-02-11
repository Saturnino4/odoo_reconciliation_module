from odoo import models, fields, api

class Conta(models.Model):
    _name = 'account.account'
    _description = 'Modelo de Conta tanto para nostro como vostro'

    name = fields.Char(string='Nome', required=True)
    bank = fields.Char(string='Banco', required=True)
    number = fields.Char(string='Número', required=True)
    is_nostro = fields.Boolean(string='Nostro', default=False)
    status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ], string='Estado', default='active', required=True)


    def action_inactive(self):
        self.write({'status': 'inactive'})

    def action_active(self):
        self.write({'status': 'active'})
   