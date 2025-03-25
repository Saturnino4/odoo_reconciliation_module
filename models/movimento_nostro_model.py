from odoo import models, fields, api
import requests

class MovimentoNostro(models.Model):
    _name = 'movimento_nostro.movimento_nostro'
    _description = 'Movimentos da conta nostra'

    documento = fields.Char(string='Documento', required=True)
    data_emissao = fields.Date(string='Data Emissão', required=True)
    data_conta = fields.Date(string='Data Contabilistica', required=True)
    movimento = fields.Float(string='Movimento', required=True)
    saldo = fields.Float(string='Saldo', required=True)
    conta_id = fields.Many2one('account.account', string='Conta', required=False)
    status = fields.Selection([
        ('ativo', 'Ativo'),
        ('inativo', 'Inativo'),
        ('pending', 'Pendente'), 
        ('reconciled', 'Reconciliado')
    ], string='Estado', default='ativo', required=False)

    def action_inactive(self):
        self.write({'status': 'inativo'})

    def action_active(self):
        self.write({'status': 'ativo'})

    def action_pending(self):
        self.write({'status': 'pending'})

    def action_reconciled(self):
        self.write({'status': 'reconciled'})

    def action_show_html(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_html',
            'params': {
                'content': '<h1>Custom HTML Content</h1>',
                'title': 'Custom HTML',
            }
        }