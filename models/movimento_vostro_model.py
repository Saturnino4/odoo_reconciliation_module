from odoo import models, fields, api
import requests

class MovimentoVostro(models.Model):
    _name = 'movimento_vostro.movimento_vostro'
    _description = 'Movimentos da conta vostro'

    value = fields.Char(string='Valor', required=False)
    date = fields.Date(string='Data', required=False)
    code = fields.Char(string='Código', required=False)
    entr = fields.Char(string='Entrada', required=False)
    reference = fields.Char(string='Referência', required=False)
    amount = fields.Float(string='Montante', required=False)
    ma = fields.Char(string='MA', required=False)
    status = fields.Selection([
        ('ativo', 'Ativo'),
        ('inativo', 'Inativo'),
        ('pending', 'Pendente'),
        ('reconciled', 'Reconciliado')
    ], string='Estado', default='pending', required=False)
    conta_id = fields.Many2one('account.account', string='Conta', required=False)

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

    # @api.model
    # def fetch_from_api(self):
    #     url = 'http://localhost:8000/api/v1/swift/?data_only=1'
    #     response = requests.get(url)
    #     if response.status_code == 200:
    #         data = response.json()
    #         for item in data:
    #             self.create({
    #                 'name': item.get('name'),
    #                 'bank': item.get('bank'),
    #                 'number': item.get('number'),
    #                 'is_nostro': item.get('is_nostro', False),
    #                 'status': item.get('status', 'active'),
    #             })
    #     else:
    #         raise Exception(f"Failed to fetch data from API. Status code: {response.status_code}")