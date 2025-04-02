from odoo import models, fields, api
from datetime import timedelta

class Reconciliation(models.Model):
    _name = 'reconciliation.reconciliation'
    _description = 'Reconciliation'

    name = fields.Char(string='Nome', compute='_compute_name', store=True)
    date_start = fields.Date(string='Data Inicio', required=True)
    # date_end = fields.Date(string='Data Fim', required=True)
    date_end = fields.Date(string='Data Fim', required=True, default=fields.Date.context_today)
    description = fields.Text(string='Descrição')
    day_offset = fields.Integer(string='Desfasamento (dias)', default=0)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('checked', 'Checked'),
        ('approved', 'Approved'),
    ], string='Estado', default='draft', required=True)

    conta1_id = fields.Many2one('account.account',
                                domain=[('is_nostro', '=', False)],
                                required=True,
                                string="Selecione Vostro" )
    conta2_id = fields.Many2one('account.account', 
                                domain=[('is_nostro', '=', True)],
                                required=True,
                                string="Selecione Nostro"  )

    swift_ids = fields.One2many(
        'movimento_vostro.movimento_vostro', 
        string='Swift Transactions', 
        compute='_compute_swift_ids', 
        readonly=True
    )
    nostro_ids = fields.One2many(
        'movimento_nostro.movimento_nostro', 
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

    @api.onchange('conta1_id')
    def _onchange_conta1_id(self):
        """When vostro account (conta1) is selected, automatically set the corresponding nostro account"""
        if self.conta1_id:
            # Search for a nostro.vostro relationship where this account is the vostro
            relationship = self.env['nostro.vostro'].search([
                ('vostro_account_id', '=', self.conta1_id.id)
            ], limit=1)
            
            if relationship:
                # Set the nostro account
                self.conta2_id = relationship.nostro_account_id
            else:
                # No relationship found, clear the nostro account if one was previously set
                self.conta2_id = False

    @api.onchange('conta2_id')
    def _onchange_conta2_id(self):
        """When nostro account (conta2) is selected, automatically set the corresponding vostro account"""
        if self.conta2_id:
            # Search for a nostro.vostro relationship where this account is the nostro
            relationship = self.env['nostro.vostro'].search([
                ('nostro_account_id', '=', self.conta2_id.id)
            ], limit=1)
            
            if relationship:
                # Set the vostro account
                self.conta1_id = relationship.vostro_account_id
            else:
                # No relationship found, clear the vostro account if one was previously set
                self.conta1_id = False

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

    @api.depends('conta1_id', 'date_start', 'date_end')
    def _compute_swift_ids(self):
        for rec in self:
            if rec.conta1_id and rec.date_start and rec.date_end:
                # Create domain for the search
                domain = [
                    ('conta_id', '=', rec.conta1_id.id),
                    ('date', '<=', rec.date_end),
                    '|',  # OR condition for the following criteria
                    ('date', '>=', rec.date_start),  # Either date is >= start date
                    ('status', '!=', 'reconciled')   # Or status is not reconciled (regardless of date)
                ]
                
                rec.swift_ids = self.env['movimento_vostro.movimento_vostro'].search(domain)
            else:
                rec.swift_ids = self.env['movimento_vostro.movimento_vostro']
    
    @api.depends('conta2_id', 'date_start', 'date_end')
    def _compute_nostro_ids(self):
        for rec in self:
            if rec.conta2_id and rec.date_start and rec.date_end:
                # Create domain for the search
                domain = [
                    ('conta_id', '=', rec.conta2_id.id),
                    ('data_conta', '<=', rec.date_end),
                    '|',  # OR condition for the following criteria
                    ('data_conta', '>=', rec.date_start),  # Either date is >= start date
                    ('status', '!=', 'reconciled')         # Or status is not reconciled (regardless of date)
                ]
                
                rec.nostro_ids = self.env['movimento_nostro.movimento_nostro'].search(domain)
            else:
                rec.nostro_ids = self.env['movimento_nostro.movimento_nostro']