odoo.define('reconciliation.static_view', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var QWeb = core.qweb;

    var StaticView = AbstractAction.extend({
        template: 'static_view_template',
        init: function (parent, context) {
            this._super(parent, context);
        },
        start: function () {
            var self = this;
            return this._super().then(function () {
                self.$el.html(QWeb.render('static_view_template'));
            });
        },
    });

    core.action_registry.add('static_view', StaticView);

    return StaticView;
});