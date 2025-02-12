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
        "swift.swift",
        string="Swifts Pendentes",
        compute="_compute_pending_swift",
        store=True

    )
    pending_nostro_ids = fields.Many2many(
        "account_nostro.account_nostro",
        string="Nostro Pendentes",
        compute="_compute_pending_nostro",
        store=True
    )

    @api.model
    def default_get(self, fields_list):
        res = super(ReconciliationWizard, self).default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            rec = self.env['reconciliation.reconciliation'].browse(active_id)
            
            base_info = "Conta 1: {0}\nConta 2: {1}\nNome: {2}".format(
                rec.conta1_id.name or 'N/D', rec.conta2_id.name or 'N/D', rec.name or 'Sem Nome'
            )

            nostro_codes = [r.split(' ')[-1] for r in rec.nostro_ids.mapped('reference') if r]

            swifts_pending = rec.swift_ids.filtered(
                lambda s: s.reference and s.reference.split('.')[-1] not in nostro_codes
            )

            total_swift = sum(swifts_pending.mapped('amount'))
            total_nostro = sum(rec.nostro_ids.mapped('balance'))

            swift_refs = ", ".join(rec.swift_ids.mapped('reference'))
            nostro_refs = ", ".join(rec.nostro_ids.mapped('reference'))
            other_data = "Swifts: {0} | Nostro: {1}".format(swift_refs or 'Nenhum', nostro_refs or 'Nenhum')
            diferenca = total_swift - total_nostro if total_swift > total_nostro else total_nostro - total_swift

            resumo = (
                f"{base_info}\n\n"
                f"Detalhes de Swift:\n"
                f" - Pendentes: {len(swifts_pending)}\n"
                f" - Total Swift: {total_swift}\n\n"
                f"Detalhes de Nostro:\n"
                f" - Pendentes: {len(rec.nostro_ids)}\n"
                f" - Total Nostro: {total_nostro}\n\n"
                f"Dados Gerais: "
                f"Pendencias total: {total_swift + total_nostro}\n"
                f"Diferença entre os totais: {diferenca}\n"
            )

            res.update({
                'message': resumo,
                'conta1_id': rec.conta1_id.id,
                'conta2_id': rec.conta2_id.id,
                'other_data': other_data,
                'reconciliation_id': rec.id,
            })
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
                wiz.pending_swift_ids = self.env['swift.swift']

    @api.depends('reconciliation_id', 'reconciliation_id.nostro_ids.reference', 'reconciliation_id.swift_ids.reference')
    def _compute_pending_nostro(self):
        for wiz in self:
            if wiz.reconciliation_id:
                pending = self.env['account_nostro.account_nostro']
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
                wiz.pending_nostro_ids = self.env['account_nostro.account_nostro']