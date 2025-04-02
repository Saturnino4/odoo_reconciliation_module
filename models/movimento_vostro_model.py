from odoo import models, fields, api
import requests

class MovimentoVostro(models.Model):
    _name = 'movimento_vostro.movimento_vostro'
    _description = 'Movimentos da conta vostro'
    _rec_name = 'reference'

    value = fields.Char(string='Valor', required=False)
    date = fields.Date(string='Data', required=False)
    code = fields.Char(string='Código', required=False)
    entr = fields.Char(string='Entrada', required=False)
    reference = fields.Char(string='Referência', required=False)
    amount = fields.Float(string='Montante', required=False)
    ma = fields.Char(string='MA', required=False)
    movimento_nostro_id = fields.Many2one('movimento_nostro.movimento_nostro', string='Nostro', required=False)
    status = fields.Selection([
        ('ativo', 'Ativo'),
        ('inativo', 'Inativo'),
        ('pending', 'Pendente'),
        ('reconciled', 'Reconciliado')
    ], string='Estado', default='pending', required=False)
    conta_id = fields.Many2one('account.account', string='Conta', required=False)
    
    
    adjusted_amount = fields.Float(
        string='Saldo',
        compute='_compute_adjusted_amount',
        store=True,  # Important for aggregation in group by views
        help='Montante ajustado considerando crédito/débito'
    )
    
    @api.depends('amount', 'ma')
    def _compute_adjusted_amount(self):
        for record in self:
            if record.ma and record.amount:
                if record.ma.upper() == 'D':
                    record.adjusted_amount = -record.amount
                else:  # 'C' or any other value
                    record.adjusted_amount = record.amount
            else:
                record.adjusted_amount = record.amount or 0.0

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
