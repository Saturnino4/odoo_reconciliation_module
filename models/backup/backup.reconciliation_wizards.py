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

            # Extrai os códigos de referência dos registros de nostro,
            # considerando a última parte do campo reference
            nostro_codes = [r.split(' ')[-1] for r in rec.nostro_ids.mapped('reference') if r]

            # Filtra os swifts que possuem um código (última parte da referência)
            # que NÃO esteja na lista dos códigos de nostro
            swifts_pending = rec.swift_ids.filtered(
                lambda s: s.reference and s.reference.split('.')[-1] not in nostro_codes
            )

            total_swift = sum(swifts_pending.mapped('amount'))
            total_nostro = sum(rec.nostro_ids.mapped('balance'))

            # Outros dados para exibição
            swift_refs = ", ".join(rec.swift_ids.mapped('reference'))
            nostro_refs = ", ".join(rec.nostro_ids.mapped('reference'))
            other_data = "Swifts: {0} | Nostro: {1}".format(swift_refs or 'Nenhum', nostro_refs or 'Nenhum')



            resumo = (
                f"{base_info}\n\n"
                f"Detalhes de Swift Pendentes:\n"
                f" - Quantidade: {len(swifts_pending)}\n"
                f" - Total Swift: {total_swift}\n\n"
                f" - Nostro codes: {nostro_codes}\n\n"
                f"Total Nostro: {total_nostro}\n\n"
               # f"Outros Dados: {other_data}"
            )


            
           

            #


            res.update({
                'message': resumo,
                'conta1_id': rec.conta1_id.id,
                'conta2_id': rec.conta2_id.id,
                'swift_pendente': swifts_pending,
                'other_data': other_data,
                'total_swift': total_swift,
                'total_nostro': total_nostro,
            })
        return res

    def action_confirm_wizard(self):
        # Aqui você coloca a lógica que processa os dados do wizard.
        # Pode chamar um controller, criar registros ou disparar outro fluxo.
        # Após o processamento, fecha o wizard.
        return {'type': 'ir.actions.act_window_close'}