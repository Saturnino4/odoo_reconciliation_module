from odoo import models, fields, api

class Reconciliation(models.Model):
    _name = 'reconciliation.reconciliation'
    _description = 'Reconciliation'

    name = fields.Char(string='Nome', required=True)
    date_start = fields.Date(string='Data Inicio', required=True)
    date_end = fields.Date(string='Data Fim', required=True)
    description = fields.Text(string='Descrição')
    amount = fields.Float(string='Montante', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
    ], string='Estado', default='draft', required=True)

    swift_id = fields.Many2one('swift.swift', string="Swift")
    nostro_id = fields.Many2one('account_nostro.account_nostro', string="Nostro Account")

    # @api.multi
    def action_confirm(self):
        self.write({'state': 'confirmed'})

    # @api.multi
    def action_done(self):
        self.write({'state': 'done'})

    def action_reconcilie(self):
        """
        Simula a reconciliação e informa se não há registros disponíveis
        """
        # Exemplo fictício de validação: verificar se amount é menor que 1000
        # if not self.filtered(lambda rec: rec.amount > 1000):
        #     # Exibe uma notificação ao usuário
        #     self.env.user.notify_info(message="Nenhum registro disponível para reconciliar neste período.")
        # else:
        #     self.write({'state': 'done'})
        #     self.env.user.notify_success(message="Reconciliado com sucesso!")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Reconciliação',
                'message': 'Nenhum registro disponível para reconciliar neste período.',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'}
            }
        }

    # def action_reconcile(self):
    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'reconciliation_interface',
    #         'params': {
    #             'reconciliation_id': self.id,
    #         }
    #     }