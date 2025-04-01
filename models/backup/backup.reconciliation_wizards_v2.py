from odoo import models, fields, api

class ReconciliationWizard(models.TransientModel):
    _name = 'reconciliation.wizard'
    _description = 'Resumo da Reconciliação'

    message = fields.Text(string="Resumo", readonly=True)
    conta1_id = fields.Many2one("account.account", string="Conta 1")
    conta2_id = fields.Many2one("account.account", string="Conta 2")
    other_data = fields.Char(string="Dados Adicionais")
    reconciliation_id = fields.Many2one("reconciliation.reconciliation", string="Reconciliação", readonly=True)
    
    pending_swift_ids = fields.Many2many(
        "movimento_vostro.movimento_vostro",
        string="Swifts Pendentes",
        compute="_compute_pending_swift"
    )
    pending_nostro_ids = fields.Many2many(
        "movimento_nostro.movimento_nostro",
        string="Nostro Pendentes",
        compute="_compute_pending_nostro"
    )

    @api.model
    def default_get(self, fields_list):
        res = super(ReconciliationWizard, self).default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            rec = self.env['reconciliation.reconciliation'].browse(active_id)
            res.update({
                'reconciliation_id': rec.id,
                'conta1_id': rec.conta1_id.id,
                'conta2_id': rec.conta2_id.id,
            })
            
            # Calculate summary directly without creating wizard instance first
            nostro_ids = rec.nostro_ids
            swift_ids = rec.swift_ids
            
            # Prepare data for pending calculations
            nostro_codes = [r.split(' ')[-1] for r in nostro_ids.mapped('reference') if r]
            pending_swifts = swift_ids.filtered(
                lambda s: s.reference and s.reference.split('.')[-1] not in nostro_codes
            )
            
            pending_nostro = self.env['movimento_nostro.movimento_nostro']
            for nost in nostro_ids:
                if nost.reference:
                    nostro_code = nost.reference.split(' ')[-1]
                    matching_swift = swift_ids.filtered(
                        lambda s: s.reference and s.reference.split('.')[-1] == nostro_code
                    )
                    if not matching_swift:
                        pending_nostro |= nost
            
            # Calculate totals using correct field names
            total_swift = sum(pending_swifts.mapped('amount'))
            total_nostro = sum(nostro_ids.mapped('saldo'))  # Changed from 'balance' to 'saldo'
            
            resumo = (
                f"Swift Pendentes: {len(pending_swifts)}\n"
                f"Nostro Pendentes: {len(pending_nostro)}\n"
                f"Total Swift: {total_swift}\n"
                f"Total Nostro: {total_nostro}\n"
                f"Diferença: {abs(total_swift - total_nostro)}\n"                
            )
            
            # Store IDs for the many2many fields
            if 'pending_swift_ids' in fields_list:
                res['pending_swift_ids'] = [(6, 0, pending_swifts.ids)]
            if 'pending_nostro_ids' in fields_list:
                res['pending_nostro_ids'] = [(6, 0, pending_nostro.ids)]
                
            res['message'] = resumo
            
        return res
    
    def action_confirm_wizard(self):
        active_id = self.env.context.get('active_id')
        if active_id:
            rec = self.env['reconciliation.reconciliation'].browse(active_id)
            nostro_codes = [r.split(' ')[-1] for r in rec.nostro_ids.mapped('reference') if r]

            matching_swifts = rec.swift_ids.filtered(
                lambda s: s.reference and s.reference.split('.')[-1] in nostro_codes
            )
            pending_swifts = rec.swift_ids.filtered(
                lambda s: s.reference and s.reference.split('.')[-1] not in nostro_codes
            )

            if matching_swifts:
                matching_swifts.action_reconciled()
            if pending_swifts:
                pending_swifts.action_pending()

            for nostro in rec.nostro_ids:
                if nostro.reference:
                    nostro_code = nostro.reference.split(' ')[-1]
                    matching_swift = rec.swift_ids.filtered(
                        lambda s: s.reference and s.reference.split('.')[-1] == nostro_code
                    )
                    if matching_swift:
                        nostro.action_reconciled()
                    else:
                        nostro.action_pending()

            rec.action_confirm()

        return {'type': 'ir.actions.act_window_close'}
    
    @api.depends('reconciliation_id', 'reconciliation_id.nostro_ids.reference', 'reconciliation_id.swift_ids.reference')
    def _compute_pending_swift(self):
        for wiz in self:
            if wiz.reconciliation_id:
                nostro_codes = [r.split(' ')[-1] for r in wiz.reconciliation_id.nostro_ids.mapped('reference') if r]
                wiz.pending_swift_ids = wiz.reconciliation_id.swift_ids.filtered(
                    lambda s: s.reference and s.reference.split('.')[-1] not in nostro_codes
                )
            else:
                wiz.pending_swift_ids = self.env['movimento_vostro.movimento_vostro']
    
    @api.depends('reconciliation_id', 'reconciliation_id.nostro_ids.reference', 'reconciliation_id.swift_ids.reference')
    def _compute_pending_nostro(self):
        for wiz in self:
            if wiz.reconciliation_id:
                pending = self.env['movimento_nostro.movimento_nostro']
                for nost in wiz.reconciliation_id.nostro_ids:
                    if nost.reference:
                        nostro_code = nost.reference.split(' ')[-1]
                        matching_swift = wiz.reconciliation_id.swift_ids.filtered(
                            lambda s: s.reference and s.reference.split('.')[-1] == nostro_code
                        )
                        if not matching_swift:
                            pending |= nost
                wiz.pending_nostro_ids = pending
            else:
                wiz.pending_nostro_ids = self.env['movimento_nostro.movimento_nostro']