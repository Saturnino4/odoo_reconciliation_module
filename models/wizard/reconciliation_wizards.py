from odoo import models, fields, api

class ReconciliationWizard(models.TransientModel):
    _name = 'reconciliation.wizard'
    _description = 'Resumo da Reconciliação'

    message = fields.Text(string="Resumo", readonly=True)
    conta1_id = fields.Many2one("account.account", string="Conta 1")
    conta2_id = fields.Many2one("account.account", string="Conta 2")
    other_data = fields.Char(string="Dados Adicionais")

    @api.model
    def default_get(self, fields_list):
        res = super(ReconciliationWizard, self).default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            rec = self.env['reconciliation.reconciliation'].browse(active_id)
            
            # Informações básicas
            base_info = "Conta 1: {0}\nConta 2: {1}\nNome: {2}".format(
                rec.conta1_id.name or 'N/D', rec.conta2_id.name or 'N/D', rec.name or 'Sem Nome'
            )

            # Extrai os códigos de referência (última parte) dos registros de nosso
            nostro_codes = [r.split(' ')[-1] for r in rec.nostro_ids.mapped('reference') if r]

            # Identifica os swifts pendentes: cujo último segmento da referência não consta em nosso_codes
            swifts_pending = rec.swift_ids.filtered(
                lambda s: s.reference and s.reference.split('.')[-1] not in nostro_codes
            )

            total_swift = sum(swifts_pending.mapped('amount'))
            total_nostro = sum(rec.nostro_ids.mapped('balance'))

            # Dados para exibição
            swift_refs = ", ".join(rec.swift_ids.mapped('reference'))
            nostro_refs = ", ".join(rec.nostro_ids.mapped('reference'))
            other_data = "Swifts: {0} | Nostro: {1}".format(swift_refs or 'Nenhum', nostro_refs or 'Nenhum')

            resumo = (
                f"{base_info}\n\n"
                f"Detalhes de Swift:\n"
                f" - Quantidade: {len(swifts_pending)}\n"
                f" - Total Swift: {total_swift}\n\n"
                f"Detalhes de Nostro:\n"
                f" - Quantidade: {len(rec.nostro_ids)}\n"
                f" - Total Nostro: {total_nostro}\n\n"
                # f"Swift para reconciliação: {swift_refs}\n\n"
                # f"Outros Dados: {other_data}"
                f"Dados Gerais:"
                f"Pendencias total: {total_swift + total_nostro}"
                f"Diferença entre os totais: {total_swift - total_nostro}"
            )

            res.update({
                'message': resumo,
                'conta1_id': rec.conta1_id.id,
                'conta2_id': rec.conta2_id.id,
                'other_data': other_data,
            })
        return res

    def action_confirm_wizard(self):
        active_id = self.env.context.get('active_id')
        if active_id:
            rec = self.env['reconciliation.reconciliation'].browse(active_id)
            # Recalcula os códigos de referência dos registros de nosso
            nostro_codes = [r.split(' ')[-1] for r in rec.nostro_ids.mapped('reference') if r]

            # Separa os swifts que tiveram match e os que não tiveram
            matching_swifts = rec.swift_ids.filtered(
                lambda s: s.reference and s.reference.split('.')[-1] in nostro_codes
            )
            pending_swifts = rec.swift_ids.filtered(
                lambda s: s.reference and s.reference.split('.')[-1] not in nostro_codes
            )

            # Processa os swifts:
            if matching_swifts:
                matching_swifts.action_reconciled()
            if pending_swifts:
                pending_swifts.action_pending()

            # Processa os nosso:
            for nostro in rec.nostro_ids:
                if nostro.reference:
                    # Pega o código do nosso (última parte da referência separado por espaço)
                    nostro_code = nostro.reference.split(' ')[-1]
                    # Verifica se existe algum swift cujo último segmento da referência (separado por ponto)
                    # corresponde ao código do nosso
                    matching_swift = rec.swift_ids.filtered(
                        lambda s: s.reference and s.reference.split('.')[-1] == nostro_code
                    )
                    if matching_swift:
                        nostro.action_reconciled()
                    else:
                        nostro.action_pending()

            # Confirma a reconciliação principal
            rec.action_confirm()

        return {'type': 'ir.actions.act_window_close'}