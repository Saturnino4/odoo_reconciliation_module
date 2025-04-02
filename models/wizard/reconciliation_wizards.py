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

    def _extract_vostro_reference(self, reference):
        """Extract the actual reference number from vostro reference"""
        if not reference:
            return ""
        return reference.split(' ')[-1]
    
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
            
            # Get nostro codes (direct reference)
            nostro_codes = nostro_ids.mapped('reference')
    
            reconciled_swifts = swift_ids.filtered(
                lambda s: self._extract_vostro_reference(s.reference) in nostro_codes
            )
            # Filter swift records that don't match any nostro code
            pending_swifts = swift_ids.filtered(
                lambda s: self._extract_vostro_reference(s.reference) not in nostro_codes
            )
            
            # Find reconciled nostro records
            reconciled_nostro = self.env['movimento_nostro.movimento_nostro']
            pending_nostro = self.env['movimento_nostro.movimento_nostro']
            for nost in nostro_ids:
                if nost.reference:
                    # Find swifts with matching extracted reference
                    matching_swift = swift_ids.filtered(
                        lambda s: self._extract_vostro_reference(s.reference) == nost.reference
                    )
                    if matching_swift:
                        reconciled_nostro |= nost
                    else:
                        pending_nostro |= nost
            
            # Calculate totals using correct field names
            total_swift_reconciled = sum(reconciled_swifts.mapped('amount'))
            total_swift_pending = sum(pending_swifts.mapped('amount'))
            total_swift = total_swift_reconciled + total_swift_pending
            total_nostro = sum(nostro_ids.mapped('saldo'))
            
            resumo = (
                f"Vostro:\n"
                f"\t - Pendentes: {len(pending_swifts)}\n"
                f"\t - Reconciliado: {len(reconciled_swifts)}\n"
                f"\t - Saldo: {abs(total_swift):.2f}\n"
                f"Nostro:\n"
                f"\t - Pendentes: {len(pending_nostro)}\n"
                f"\t - Reconciliado: {len(reconciled_nostro)}\n"
                f"\t - Saldo: {abs(total_nostro):.2f}\n"
                f"Diferença: {abs(total_swift - total_nostro):.2f}\n"            
            )
            
            # Store IDs for the many2many fields
            if 'pending_swift_ids' in fields_list:
                res['pending_swift_ids'] = [(6, 0, pending_swifts.ids)]
            if 'pending_nostro_ids' in fields_list:
                res['pending_nostro_ids'] = [(6, 0, pending_nostro.ids)]
                
            res['message'] = resumo
            
        return res
    
    @api.depends('reconciliation_id', 'reconciliation_id.nostro_ids.reference', 'reconciliation_id.swift_ids.reference')
    def _compute_pending_swift(self):
        for wiz in self:
            if wiz.reconciliation_id:
                nostro_codes = wiz.reconciliation_id.nostro_ids.mapped('reference')
                wiz.pending_swift_ids = wiz.reconciliation_id.swift_ids.filtered(
                    lambda s: self._extract_vostro_reference(s.reference) not in nostro_codes
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
                        matching_swift = wiz.reconciliation_id.swift_ids.filtered(
                            lambda s: self._extract_vostro_reference(s.reference) == nost.reference
                        )
                        if not matching_swift:
                            pending |= nost
                wiz.pending_nostro_ids = pending
            else:
                wiz.pending_nostro_ids = self.env['movimento_nostro.movimento_nostro']
    
    def action_confirm_wizard(self):
        """Confirm the reconciliation based on the wizard data"""
        self.ensure_one()
        if self.reconciliation_id:
            # Update the reconciliation record
            self.reconciliation_id.write({
                'state': 'confirmed',
                'write_date': fields.Date.today(),
                'write_uid': self.env.user.id,
            })
            
            # Get nostro codes (direct references)
            nostro_codes = self.reconciliation_id.nostro_ids.mapped('reference')
            
            # Find matching swifts by comparing extracted references
            matching_swifts = self.reconciliation_id.swift_ids.filtered(
                lambda s: self._extract_vostro_reference(s.reference) in nostro_codes
            )
            
            # Update status of matched records
            matching_swifts.write({'status': 'reconciled'})
            
            # Find matching nostro records and update them
            reconciled_count = 0
            for swift in matching_swifts:
                extracted_ref = self._extract_vostro_reference(swift.reference)
                matching_nostro = self.reconciliation_id.nostro_ids.filtered(
                    lambda n: n.reference == extracted_ref
                )
                if matching_nostro:
                    # Update nostro status
                    matching_nostro.write({
                        'status': 'reconciled',
                        'movimento_vostro_id': swift.id,  # Set reference to the vostro movement
                    })
                    
                    # Update vostro with reference to nostro
                    swift.write({
                        'movimento_nostro_id': matching_nostro.id  # Set reference to the nostro movement
                    })
                    
                    reconciled_count += 1
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Reconciliação Confirmada',
                    'message': f'{reconciled_count} registros foram reconciliados com sucesso.',
                    'sticky': False,
                    'type': 'success',
                }
            }
        
        return {'type': 'ir.actions.act_window_close'}