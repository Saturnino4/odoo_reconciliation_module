from odoo import models, fields, api
from odoo.http import request
import xlwt
import base64
from io import BytesIO
import logging
_logger = logging.getLogger(__name__)

class ReconciliationWizard(models.TransientModel):
    _name = 'reconciliation.wizard'
    _description = 'Resumo da Reconciliação'
    _res_name = 'reconciliation.wizard'

    message = fields.Text(string="Resumo", readonly=True)
    # debito_nostro = fields.Float(string="Débito Nostro", readonly=True)
    # credito_nostro = fields.Float(string="Crédito Nostro", readonly=True)
    # debito_vostro = fields.Float(string="Débito Vostro", readonly=True)
    # credito_vostro = fields.Float(string="Crédito Vostro", readonly=True)
    
    reconciliation_id = fields.Many2one('reconciliation.reconciliation', string='Reconciliation')
    reconciliation_state = fields.Selection(related='reconciliation_id.state', string='Estado', readonly=True, store=True)
    
    conta1_id = fields.Many2one("account.account", string="Conta Vostro")
    conta2_id = fields.Many2one("account.account", string="Conta Nostro")
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
            
            # Calculate totals for Vostro using credit/debit logic based on ma field
            total_swift = 0
            vostro_credit_total = 0
            vostro_debit_total = 0
            vostro_credit_count = 0
            vostro_debit_count = 0
            
            for swift in swift_ids:
                # If ma is 'D' (debit), treat as debit; otherwise as credit
                if swift.ma and swift.ma.upper() == 'D':
                    vostro_debit_total += swift.amount
                    vostro_debit_count += 1
                    total_swift -= swift.amount
                else:
                    vostro_credit_total += swift.amount
                    vostro_credit_count += 1
                    total_swift += swift.amount
                    
            # For nostro, calculate credit and debit based on saldo sign
            nostro_credit_total = 0
            nostro_debit_total = 0
            nostro_credit_count = 0
            nostro_debit_count = 0
            
            for nostro in nostro_ids:
                if nostro.saldo >= 0:
                    # Positive saldo is credit
                    nostro_credit_total += nostro.saldo
                    nostro_credit_count += 1
                else:
                    # Negative saldo is debit (store as positive amount for display)
                    nostro_debit_total += abs(nostro.saldo)
                    nostro_debit_count += 1
                    
            # Calculate total nostro balance respecting signs
            total_nostro = sum(nostro_ids.mapped('saldo'))
            
            resumo = (
                f"Vostro:\n"
                f"\t - Pendentes: {len(pending_swifts)}\n"
                f"\t - Reconciliado: {len(reconciled_swifts)}\n"
                f"\t - Total Crédito: {vostro_credit_count} ({vostro_credit_total:.2f})\n"
                f"\t - Total Débito: {vostro_debit_count} ({vostro_debit_total:.2f})\n"
                f"\t - Saldo: {total_swift:.2f}\n"
                f"Nostro:\n"
                f"\t - Pendentes: {len(pending_nostro)}\n"
                f"\t - Reconciliado: {len(reconciled_nostro)}\n"
                f"\t - Total Crédito: {nostro_credit_count} ({nostro_credit_total:.2f})\n"
                f"\t - Total Débito: {nostro_debit_count} ({nostro_debit_total:.2f})\n"
                f"\t - Saldo: {total_nostro:.2f}\n"
                f"Diferença: {abs(total_swift - total_nostro):.2f}\n\n"            
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
    
    def action_check_wizard(self):
        """Check the reconciliation based on the wizard data"""
        self.ensure_one()
        if self.reconciliation_id:
            # Update the reconciliation record
            self.reconciliation_id.write({
                'state': 'checked',
                'write_date': fields.Date.today(),
                'write_uid': self.env.user.id,
            })
            
            # Display a notification
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Reconciliação Checada',
                    'message': f'A reconciliação foi checada com sucesso.',
                    'sticky': False,
                    'type': 'success',
                }
            }
        
        return {'type': 'ir.actions.act_window_close'}
    
    def action_approve_wizard(self):
        """Aprova the reconciliation based on the wizard data"""
        self.ensure_one()
        if self.reconciliation_id:
            # Update the reconciliation record
            self.reconciliation_id.write({
                'state': 'approved',
                'write_date': fields.Date.today(),
                'write_uid': self.env.user.id,
            })
            
            # Display a notification
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Reconciliação Aprovada',
                    'message': f'A reconciliação foi aprovada com sucesso.',
                    'sticky': False,
                    'type': 'success',
                }
            }
        
        return {'type': 'ir.actions.act_window_close'}
    
    def action_export_xls(self):

        wb = xlwt.Workbook()
        sheet_resumo = wb.add_sheet('Resumo')
        sheet = wb.add_sheet('Recolha')

       # Estilos
        bold = 'font: bold on;'
        align = 'align: horiz center;'
        center_align = "align: horiz center, vert center;"
        border_all = 'borders: left medium, right medium, top medium, bottom medium;'
        border_medium_vert = 'borders: left medium, right medium;'
        border_thin_vert = 'borders: left thin, right thin;'
        border_medium_right = 'borders: right medium;'
        border_medium_left = 'borders: left medium;'
        border_medium_top = 'borders: top medium;'
        border_medium_bottom = 'borders: bottom medium;'
        border_thin_top = 'borders: top thin;'
        border_thin_bottom = 'borders: bottom thin;'
        border_thin_left = 'borders: left thin;'
        border_thin_right = 'borders: right thin;'
        border_thin_all = 'borders: left thin, right thin, top thin, bottom thin;'
        yellow_highlight = 'pattern: pattern solid, fore_colour yellow;'

        style_title = xlwt.easyxf(f'{bold}{align}{border_all}')
        style_subtitle = xlwt.easyxf(f'{bold}{align}{border_all}')
        style_header = xlwt.easyxf(f'{bold}{align}{border_all}')
        style_total = xlwt.easyxf(f'{bold}{border_all}')
        style_data = xlwt.easyxf(border_thin_vert)
        style_title_center = xlwt.easyxf(f'{bold}{center_align}{border_all}')
        style_highlight = xlwt.easyxf(f'{yellow_highlight}')

        # === SHEET RESUMO ===
        row_offset = 5
        sheet_resumo.write_merge(7,7, 5, 7, 'FICHA DE CONTROLO', style_title_center)

        sheet_resumo.write(row_offset + 4, 5, 'Correspondente', xlwt.easyxf(f'{bold}{border_thin_left}{border_thin_top}'))
        sheet_resumo.write(row_offset + 4, 6, '', xlwt.easyxf(f'{border_thin_top}'))
        sheet_resumo.write(row_offset + 6, 6, '', xlwt.easyxf(f'{border_thin_bottom}'))
        sheet_resumo.write(row_offset + 5, 5, 'BANCO XPTO', xlwt.easyxf(f'{border_thin_left}'))  # TO_DONAMIC
        sheet_resumo.write(row_offset + 6, 5, 'BOSTON - USD', xlwt.easyxf(f'{border_thin_left}{border_thin_bottom}'))  # TO_DONAMIC

        sheet_resumo.write(row_offset + 4, 7, 'Mês de:', xlwt.easyxf(f'{bold}{border_thin_right}{border_thin_top}'))
        sheet_resumo.write(row_offset + 5, 7, 'DATA', xlwt.easyxf(f'{bold}{border_thin_right}'))
        sheet_resumo.write(row_offset + 6, 7, 'jan/25', xlwt.easyxf(f'{border_thin_right}{border_thin_bottom}'))  # TO_DONAMIC

        sheet_resumo.write_merge(row_offset + 9, row_offset + 9, 1, 7, 'RESUMO', style_title)

        sheet_resumo.write_merge(row_offset + 11, row_offset + 11, 1, 3, 'S/ EXTRACTO', style_subtitle)
        sheet_resumo.write_merge(row_offset + 11, row_offset + 11, 5, 7, 'N/ EXTRACTO', style_subtitle)

        # Cabeçalhos e dados estáticos
        sheet_resumo.write_merge(18,18,1,2, 'DESCRIÇÃO', style_header)
        sheet_resumo.write(18,3, 'VALORES', style_header)
        sheet_resumo.write_merge(18,18,5,6, 'DESCRIÇÃO', style_header)
        sheet_resumo.write(row_offset + 13, 7, 'VALORES', style_header)

        hoje = fields.Date.today()
        saldo_vostro = sum(self.reconciliation_id.swift_ids.filtered(lambda s: s.status == 'reconciled').mapped('amount'))
        saldo_nostro = sum(self.reconciliation_id.nostro_ids.filtered(lambda n: n.status == 'reconciled').mapped('saldo'))

        valores_abater_vostro = sum(s.amount for s in self.pending_swift_ids if (s.ma or '').upper() == 'D')
        valores_aumentar_vostro = sum(s.amount for s in self.pending_swift_ids if not (s.ma or '').upper() == 'D')
        saldo_conferido_vostro = saldo_vostro - valores_abater_vostro + valores_aumentar_vostro

        valores_abater_nostro = sum(abs(n.saldo) for n in self.pending_nostro_ids if n.saldo < 0)
        valores_aumentar_nostro = sum(n.saldo for n in self.pending_nostro_ids if n.saldo > 0)
        saldo_conferido_nostro = saldo_nostro - valores_abater_nostro + valores_aumentar_nostro

        diferenca = saldo_conferido_vostro - saldo_conferido_nostro

        sheet_resumo.write(row_offset + 15, 1, '', xlwt.easyxf(f'{bold}{border_medium_left}{border_medium_top}'))
        sheet_resumo.write(row_offset + 14, 1, 'Saldo em:', xlwt.easyxf(f'{bold}{border_medium_left}{border_medium_bottom}'))
        sheet_resumo.write(row_offset + 14, 2, hoje.strftime('%d-%m-%Y'), xlwt.easyxf(f'{border_thin_right}{border_medium_bottom}'))
        sheet_resumo.write(row_offset + 14, 3, round(saldo_vostro, 2), xlwt.easyxf(f'{border_medium_right}{border_medium_bottom}'))

        sheet_resumo.write(row_offset + 14, 5, 'Saldo em', xlwt.easyxf(f'{bold}{border_medium_left}{border_medium_bottom}'))
        sheet_resumo.write(row_offset + 14, 6, hoje.strftime('%d-%m-%Y'), xlwt.easyxf(f'{border_medium_bottom}{border_thin_right}'))
        sheet_resumo.write(row_offset + 14, 7, round(saldo_nostro, 2), xlwt.easyxf(f'{border_medium_right}{border_medium_bottom}'))

        sheet_resumo.write(row_offset + 15, 5, 'Posteriores', xlwt.easyxf(f'{border_medium_left}{border_thin_bottom}'))
        sheet_resumo.write(row_offset + 15, 7, '', xlwt.easyxf(f'{border_medium_right}'))
        sheet_resumo.write(row_offset + 15, 3, '', xlwt.easyxf(f'{border_medium_right}'))

        sheet_resumo.write(row_offset + 16, 1, 'Valores a', xlwt.easyxf(f'{bold}{border_medium_left}{border_thin_top}{border_thin_right}{border_thin_bottom}'))
        sheet_resumo.write(row_offset + 17, 1, '', xlwt.easyxf(f'{border_medium_left}{border_medium_bottom}'))
        sheet_resumo.write(row_offset + 17, 5, '', xlwt.easyxf(f'{border_medium_left}{border_medium_bottom}'))
        sheet_resumo.write(row_offset + 16, 2, 'A abater:', xlwt.easyxf(f'{border_thin_top}{border_thin_right}'))
        sheet_resumo.write(row_offset + 16, 3, round(valores_abater_vostro, 2), xlwt.easyxf(f'{border_thin_top}{border_medium_right}'))

        sheet_resumo.write(row_offset + 16, 5, 'Valores a', xlwt.easyxf(f'{bold}{border_medium_left}{border_thin_top}{border_thin_right}{border_thin_bottom}'))
        sheet_resumo.write(row_offset + 16, 6, 'A abater:', xlwt.easyxf(f'{border_thin_top}{border_thin_right}'))
        sheet_resumo.write(row_offset + 16, 7, round(valores_abater_nostro, 2), xlwt.easyxf(f'{border_thin_top}{border_medium_right}'))

        sheet_resumo.write(row_offset + 17, 2, 'A aumentar:', xlwt.easyxf(f'{border_thin_top}{border_thin_right}'))
        sheet_resumo.write(row_offset + 17, 3, round(valores_aumentar_vostro, 2), xlwt.easyxf(f'{border_thin_top}{border_medium_right}'))

        sheet_resumo.write(row_offset + 17, 6, 'A aumentar:', xlwt.easyxf(f'{border_thin_top}{border_thin_right}'))
        sheet_resumo.write(row_offset + 17, 7, round(valores_aumentar_nostro, 2), xlwt.easyxf(f'{border_thin_top}{border_medium_right}'))

        sheet_resumo.write_merge(23,23, 1,2, 'SALDO CONFERIDO', style_title)
        sheet_resumo.write(row_offset + 18, 3, round(saldo_conferido_vostro, 2), style_title)

        sheet_resumo.write_merge(23,23,5,6, 'SALDO CONFERIDO', style_title)
        sheet_resumo.write(row_offset + 18, 7, round(saldo_conferido_nostro, 2), style_title)

        sheet_resumo.write(row_offset + 18, 8, round(diferenca, 2), style_highlight)


        sheet_resumo.write_merge(27,27, 1,2, 'Elaborado por:', xlwt.easyxf(f'{align}'))
        sheet_resumo.write_merge(30,30, 1,2, '', xlwt.easyxf(f'{border_thin_bottom}'))

        sheet_resumo.write_merge(27,27, 6,7, 'Conferido por:', xlwt.easyxf(f'{align}'))
        sheet_resumo.write_merge(30,30, 6,7, '', xlwt.easyxf(f'{border_thin_bottom}'))


        ## >>>>>>>>>>>>>>>>>>>>  SHEET RECOLHA <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

        # Inserir logo da empresa ou nome
        company = self.env.company
        _logger.info("Campos da empresa: %s", list(company.fields_get().keys()))
        if company.logo:
            import base64
            from PIL import Image
            import io
            img_data = base64.b64decode(company.logo)
            image_stream = io.BytesIO(img_data)
            try:
                from xlwt.Utils import insert_bitmap_data
                insert_bitmap_data(sheet, image_stream, 0, 0, 5, 2)  # linhas 1 a 5, colunas A-B
            except Exception as e:
                _logger.exception("Erro ao inserir o logo da empresa: %s", e)
                sheet.write_merge(0, 4, 0, 1, company.name, style_title_center)
        else:
            sheet.write_merge(0, 4, 0, 1, company.name, style_title_center)

        # --- Cabeçalhos Especiais ---
        sheet.write(6, 0, 'CONTABILIDADE', xlwt.easyxf(f'{bold}'))
        sheet.write_merge(7, 7, 0, 1, 'SECTOR DE RECONCILIAÇÕES', xlwt.easyxf(f'{bold}{align}'))
        sheet.write(8, 0, 0.0)  # TO_DONAMIC: aqui vai o valor do saldo geral ou total mais tarde

        sheet.write_merge(0, 2, 7, 10, 'FICHA DE CONTROLO', style_title_center)

        sheet.write_merge(4, 4, 7, 8, 'CORRESPONDENTE', xlwt.easyxf(f'{bold}{align}{border_medium_left}{border_medium_top}'))
        sheet.write(4, 9, '', xlwt.easyxf(f'{border_medium_top}'))
        sheet.write(4, 10, 'MÊS', xlwt.easyxf(f'{border_medium_top}{border_medium_right}{bold}'))
        sheet.write(5, 7, 'Banco XPTO - 3322', xlwt.easyxf(f'{border_medium_left}')) # TO_DONAMIC
        sheet.write(6, 7, 'BOSTON - USD', xlwt.easyxf(f'{border_medium_left}{border_medium_bottom}'))  # TO_DONAMIC
        sheet.write(5, 10, '', xlwt.easyxf(f'{border_medium_right}'))  # TO_DONAMIC
        sheet.write(6, 8, '', xlwt.easyxf(f'{border_medium_bottom}'))  # TO_DONAMIC
        sheet.write(6, 9, '', xlwt.easyxf(f'{border_medium_bottom}'))  # TO_DONAMIC
        sheet.write(6, 10, 'jan/25', xlwt.easyxf(f'{border_medium_right}{border_medium_bottom}'))  # TO_DONAMIC

        # --- Tabela de Recolha ---
        sheet.write_merge(9, 9, 0, 9, 'RELAÇÃO DOS VALORES À CONRRESPONDER', style_title)
        sheet.write_merge(11, 11, 0, 4, 'S/EXTRATOS', style_subtitle)
        sheet.write_merge(11, 11, 5, 9, 'N/EXTRATOS', style_subtitle)

        headers = ['DATA', 'DESCRITIVO', 'REFERÊNCIA', 'DÉBITO', 'CRÉDITO']
        for i, h in enumerate(headers):
            sheet.write(12, i, h, style_header)
            sheet.write(12, i + 5, h, style_header)

        row = 13
        max_len = max(len(self.pending_swift_ids), len(self.pending_nostro_ids))

        for i in range(max_len):
            if i < len(self.pending_swift_ids):
                swift = self.pending_swift_ids[i]
                is_debit = swift.ma and swift.ma.upper() == 'D'
                sheet.write(row, 0, swift.date.strftime('%d-%m-%Y'), style_data)
                sheet.write(row, 1, swift.reference or '', style_data)
                sheet.write(row, 2, swift.movimento_nostro_id.reference or '', style_data)
                sheet.write(row, 3, swift.amount if is_debit else 0.0, style_data)
                sheet.write(row, 4, swift.amount if not is_debit else 0.0, style_data)
            else:
                for j in range(5):
                    sheet.write(row, j, '', style_data)

            if i < len(self.pending_nostro_ids):
                nostro = self.pending_nostro_ids[i]
                is_debit = nostro.saldo < 0
                sheet.write(row, 5, nostro.data_conta.strftime('%d-%m-%Y'), style_data)
                sheet.write(row, 6, nostro.reference or '', style_data)
                sheet.write(row, 7, nostro.movimento_vostro_id.reference or '', style_data)
                sheet.write(row, 8, abs(nostro.saldo) if is_debit else 0.0, style_data)
                sheet.write(row, 9, nostro.saldo if not is_debit else 0.0, style_data)
            else:
                for j in range(5):
                    sheet.write(row, j + 5, '', style_data)

            row += 1

        for col in range(10):
            if col == 0:
                sheet.write(row, col, 'TOTAL', style_total)
            elif col == 3:
                sheet.write(row, col, sum(s.amount for s in self.pending_swift_ids if (s.ma or '').upper() == 'D'), style_total)
            elif col == 4:
                sheet.write(row, col, sum(s.amount for s in self.pending_swift_ids if not (s.ma or '').upper() == 'D'), style_total)
            elif col == 8:
                sheet.write(row, col, sum(abs(n.saldo) for n in self.pending_nostro_ids if n.saldo < 0), style_total)
            elif col == 9:
                sheet.write(row, col, sum(n.saldo for n in self.pending_nostro_ids if n.saldo > 0), style_total)
            else:
                sheet.write(row, col, '', style_total)

        for col in range(10):
            sheet.col(col).width = 4000

        fp = BytesIO()
        wb.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()

        file_name = "reconciliacao.xls"
        base64_file = base64.b64encode(data)

        # Ajustar automaticamente a largura das colunas para o conteúdo
        for sheet_obj in [sheet_resumo, sheet]:
            for col in range(0, 15):
                sheet_obj.col(col).width = 50000  # aproximadamente 70 caracteres visíveis

        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'type': 'binary',
            'datas': base64_file,
            'res_model': self._name,
            'res_id': self.id,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'new',
        }
