from odoo import models, fields, api

class Reconciliation(models.Model):
    _name = 'reconciliation.reconciliation'
    _description = 'Reconciliation'

    name = fields.Char(string='Nome', required=False)
    date_start = fields.Date(string='Data Inicio', required=True)
    date_end = fields.Date(string='Data Fim', required=True)
    description = fields.Text(string='Descrição')
    amount = fields.Float(string='Montante', required=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
    ], string='Estado', default='draft', required=True)

    # Novos campos para seleção de contas
    conta1_id = fields.Many2one('account.account', string="Conta 1")
    conta2_id = fields.Many2one('account.account', string="Conta 2")

    # Listas filtradas com base na conta selecionada. 
    # Supõe-se que os modelos swift.swift e account_nostro.account_nostro possuem um campo 'conta_id'
    swift_ids = fields.One2many(
        'swift.swift', 
        string='Swift Transactions', 
        compute='_compute_swift_ids', 
        readonly=True
    )
    nostro_ids = fields.One2many(
        'account_nostro.account_nostro', 
        string='Nostro Accounts', 
        compute='_compute_nostro_ids', 
        readonly=True
    )

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_reconcilie(self):
        self.ensure_one()
        if not self.conta1_id or not self.conta2_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Erro de Reconciliação',
                    'message': 'Você deve selecionar ambas as contas antes da reconciliação.',
                    'sticky': False,
                }
            }
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'reconciliation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id},
        }
    
    # def action_list_swift(self):
    #     """Ação para listar as Swift Transactions filtradas por conta1_id."""
    #     self.ensure_one()
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Swift Transactions',
    #         'res_model': 'swift.swift',
    #         'view_mode': 'tree,form',
    #         'domain': [('conta_id', '=', self.conta1_id.id)],
    #         'context': dict(self.env.context),
    #     }
    
    # def action_list_nostro(self):
    #     """Ação para listar as Nostro Accounts filtradas por conta2_id."""
    #     self.ensure_one()
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Nostro Accounts',
    #         'res_model': 'account_nostro.account_nostro',
    #         'view_mode': 'tree,form',
    #         'domain': [('conta_id', '=', self.conta2_id.id)],
    #         'context': dict(self.env.context),
    #     }

    @api.onchange('conta1_id', 'conta2_id')
    def _onchange_accounts(self):
        if self.conta1_id and self.conta2_id:
            self.name = "%s para %s" % (self.conta1_id.name, self.conta2_id.name)
        else:
            self.name = False

    @api.depends('conta1_id')
    def _compute_swift_ids(self):
        for rec in self:
            if rec.conta1_id:
                rec.swift_ids = self.env['swift.swift'].search([('conta_id', '=', rec.conta1_id.id)])
            else:
                rec.swift_ids = self.env['swift.swift']  # vazio

    @api.depends('conta2_id')
    def _compute_nostro_ids(self):
        for rec in self:
            if rec.conta2_id:
                rec.nostro_ids = self.env['account_nostro.account_nostro'].search([('conta_id', '=', rec.conta2_id.id)])
            else:
                rec.nostro_ids = self.env['account_nostro.account_nostro']  # vazio