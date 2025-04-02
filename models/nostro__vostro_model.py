from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class NostroVostro(models.Model):
    _name = 'nostro.vostro'
    _description = 'Nostro Vostro Relationship'
    _rec_name = 'description'

    @api.model
    def _get_nostro_domain(self):
        """Return domain for nostro accounts excluding already used ones"""
        # Find all nostro accounts already in relationships (except for the current record)
        existing_ids = []
        if self._context.get('active_id'):
            existing_ids = self.search([
                ('id', '!=', self._context.get('active_id'))
            ]).mapped('nostro_account_id').ids
        else:
            existing_ids = self.search([]).mapped('nostro_account_id').ids
            
        domain = [('is_nostro', '=', True)]
        if existing_ids:
            domain.append(('id', 'not in', existing_ids))
        return domain
    
    @api.model
    def _get_vostro_domain(self):
        """Return domain for vostro accounts excluding already used ones"""
        # Find all vostro accounts already in relationships (except for the current record)
        existing_ids = []
        if self._context.get('active_id'):
            existing_ids = self.search([
                ('id', '!=', self._context.get('active_id'))
            ]).mapped('vostro_account_id').ids
        else:
            existing_ids = self.search([]).mapped('vostro_account_id').ids
            
        domain = [('is_nostro', '=', False)]
        if existing_ids:
            domain.append(('id', 'not in', existing_ids))
        return domain

    nostro_account_id = fields.Many2one(
        'account.account', 
        string='Nostro Account',
        domain=_get_nostro_domain,
        required=True
    )
    vostro_account_id = fields.Many2one(
        'account.account', 
        string='Vostro Account',
        domain=_get_vostro_domain,
        required=True
    )
    description = fields.Char(string='Description')
    status = fields.Selection([
        ('inactive', 'Inactive'),
        ('active', 'Active'),
    ], string='Status', default='active')
    
    # Use Many2many instead of One2many to avoid needing an inverse field
    movimento_nostro_ids = fields.Many2many(
        'movimento_nostro.movimento_nostro',
        string='Movimento Nostro',
        compute='_compute_movimento_nostro',
        store=False
    )
    
    movimento_vostro_ids = fields.Many2many(
        'movimento_vostro.movimento_vostro',
        string='Movimento Vostro',
        compute='_compute_movimento_vostro',
        store=False
    )
    
    # Add constraint to prevent duplicate accounts
    _sql_constraints = [
        ('nostro_vostro_unique', 
         'unique(nostro_account_id, vostro_account_id)',
         'This nostro-vostro relationship already exists!'),
        ('nostro_unique', 
         'unique(nostro_account_id)',
         'This nostro account is already used in another relationship!'),
        ('vostro_unique', 
         'unique(vostro_account_id)',
         'This vostro account is already used in another relationship!')
    ]

    @api.onchange('nostro_account_id', 'vostro_account_id')
    def _onchange_accounts(self):
        """Additional validation when accounts change"""
        if self.nostro_account_id and self.vostro_account_id and self.nostro_account_id == self.vostro_account_id:
            raise ValidationError(_("Nostro and Vostro accounts must be different!"))
    
    @api.depends('nostro_account_id')
    def _compute_movimento_nostro(self):
        for record in self:
            if record.nostro_account_id:
                record.movimento_nostro_ids = self.env['movimento_nostro.movimento_nostro'].search([
                    ('conta_id', '=', record.nostro_account_id.id)
                ])
            else:
                record.movimento_nostro_ids = self.env['movimento_nostro.movimento_nostro']
    
    @api.depends('vostro_account_id')
    def _compute_movimento_vostro(self):
        for record in self:
            if record.vostro_account_id:
                record.movimento_vostro_ids = self.env['movimento_vostro.movimento_vostro'].search([
                    ('conta_id', '=', record.vostro_account_id.id)
                ])
            else:
                record.movimento_vostro_ids = self.env['movimento_vostro.movimento_vostro']