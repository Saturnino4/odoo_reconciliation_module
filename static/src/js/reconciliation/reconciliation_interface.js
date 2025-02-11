odoo.define('reconciliation.reconciliation_interface', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var QWeb = core.qweb;

    var ReconciliationInterface = AbstractAction.extend({
        template: 'reconciliation_interface_template',
        init: function (parent, context) {
            this._super(parent, context);
            this.reconciliation_id = context.reconciliation_id;
        },
        start: function () {
            var self = this;
            return this._super().then(function () {
                self.$el.html(QWeb.render('reconciliation_interface_template', {docs: self.getDocs()}));
            });
        },
        getDocs: function () {
            // Fetch data from the server or use context data
            return [{name: "Example SWIFT Entry"}, {name: "Example Account"}];
        },
    });

    core.action_registry.add('reconciliation_interface', ReconciliationInterface);

    return ReconciliationInterface;
});