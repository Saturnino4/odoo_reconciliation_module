from odoo import models, fields, api
import requests

# Account that belongs to the bank
class Nostro(models.Model):
    _name = 'account_nostro.account_nostro'
    _description = 'Nostro'

    name = fields.Char(string='Nome', required=True)
    account_number = fields.Char(string='Número de Conta', required=True)
    reference = fields.Char(string='Referência', required=True, default='N/A') 
    bank_name = fields.Char(string='Nome do Banco', required=True)
    balance = fields.Float(string='Saldo', required=True)
    currency = fields.Char(string='Moeda', required=True)
    date = fields.Date(string='Data', required=True)
    state = fields.Selection([
        ('ativo', 'Ativo'),
        ('inativo', 'Inativo'),
        ('pending', 'Pendente'),
        ('reconciled', 'Reconciliado')
    ], string='Estado', default='ativo', required=True)
    conta_id = fields.Many2one('account.account', string='Conta', required=False)

    def action_inactivate(self):
        self.write({'state': 'inativo'})

    def action_activate(self):
        self.write({'state': 'ativo'})

    def action_pending(self):
        self.write({'state': 'pending'})

    def action_reconciled(self):
        self.write({'state': 'reconciled'})

        

