from odoo import models, fields, api
from datetime import timedelta

class Reconciliation(models.Model):
    _name = 'reconciliation.reconciliation'
    _description = 'Reconciliation'

    name = fields.Char(string='Nome', compute='_compute_name', store=True)
    date_start = fields.Date(string='Data Inicio', required=True)
    date_end = fields.Date(string='Data Fim', required=True)
    description = fields.Text(string='Descrição')
    day_offset = fields.Integer(string='Desfasamento (dias)', default=0)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('checked', 'Checked'),
        ('approved', 'Approved'),
    ], string='Estado', default='draft', required=True)

    conta1_id = fields.Many2one('account.account', string="Conta 1")
    conta2_id = fields.Many2one('account.account', string="Conta 2")

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

    @api.depends('conta1_id', 'conta2_id')
    def _compute_name(self):
        for rec in self:
            if rec.conta1_id and rec.conta2_id:
                rec.name = "%s para %s" % (rec.conta1_id.name, rec.conta2_id.name)
            else:
                rec.name = False

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_check(self):
        self.write({'state': 'checked'})

    def action_approve(self):
        self.write({'state': 'approved'})

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




    @api.depends('conta1_id', 'date_start', 'date_end', 'day_offset')
    def _compute_swift_ids(self):
        for rec in self:
            if rec.conta1_id and rec.date_start and rec.date_end:
                effective_date_start = fields.Date.from_string(rec.date_start) - timedelta(days=rec.day_offset)
                rec.swift_ids = self.env['swift.swift'].search([
                    ('conta_id', '=', rec.conta1_id.id),
                    ('date', '>=', effective_date_start),
                    ('date', '<=', rec.date_end)
                ])
            else:
                rec.swift_ids = self.env['swift.swift']

    @api.depends('conta2_id', 'date_start', 'date_end', 'day_offset')
    def _compute_nostro_ids(self):
        for rec in self:
            if rec.conta2_id and rec.date_start and rec.date_end:
                effective_date_start = fields.Date.from_string(rec.date_start) - timedelta(days=rec.day_offset)
                rec.nostro_ids = self.env['account_nostro.account_nostro'].search([
                    ('conta_id', '=', rec.conta2_id.id),
                    ('date', '>=', effective_date_start),
                    ('date', '<=', rec.date_end)
                ])
            else:
                rec.nostro_ids = self.env['account_nostro.account_nostro']




    # @api.depends('conta1_id', 'date_start', 'date_end')
    # def _compute_swift_ids(self):
    #     for rec in self:
    #         if rec.conta1_id and rec.date_start and rec.date_end:
    #             rec.swift_ids = self.env['swift.swift'].search([
    #                 ('conta_id', '=', rec.conta1_id.id),
    #                 ('date', '>=', rec.date_start),
    #                 ('date', '<=', rec.date_end)
    #             ])
    #         else:
    #             rec.swift_ids = self.env['swift.swift']

    # @api.depends('conta2_id', 'date_start', 'date_end')
    # def _compute_nostro_ids(self):
    #     for rec in self:
    #         if rec.conta2_id and rec.date_start and rec.date_end:
    #             rec.nostro_ids = self.env['account_nostro.account_nostro'].search([
    #                 ('conta_id', '=', rec.conta2_id.id),
    #                 ('date', '>=', rec.date_start),
    #                 ('date', '<=', rec.date_end)
    #             ])
    #         else:
    #             rec.nostro_ids = self.env['account_nostro.account_nostro']