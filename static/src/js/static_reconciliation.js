odoo.define('reconciliation.StaticReconciliationList', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core'); // Para registrar a ação no core

    console.log("Static Reconciliation carregado!"); // Para verificar se o arquivo foi carregado

    // Widget para o 'ir.actions.client'
    var StaticReconciliationList = AbstractAction.extend({
        template: 'static_reconciliation_list', // Nome do template XML
        start: function () {
            console.log("Static Reconciliation Widget Loaded!"); // Para verificar se o widget foi executado
            return this._super.apply(this, arguments);
        },
    });

    // Registra o widget no action_registry com o tag correspondente
    core.action_registry.add('static_reconciliation', StaticReconciliationList);

    return StaticReconciliationList;
});
