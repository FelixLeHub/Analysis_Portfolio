/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";
import { crmKanbanView } from "@crm/views/crm_kanban/crm_kanban_view";
import { useService } from "@web/core/utils/hooks";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { listView } from "@web/views/list/list_view";

// Open kanban cards in a popup dialog instead of navigating
patch(crmKanbanView.Controller.prototype, {
    setup() {
        super.setup();
        this.dialogService = useService("dialog");
    },

    openRecord(record) {
        this.dialogService.add(FormViewDialog, {
            resModel: "crm.lead",
            resId: record.resId,
            title: record.data.name,
        });
    },
});

// Use "New Lead" button label in CRM kanban
crmKanbanView.Controller.template = "freight_forwarding_crm.KanbanView";

// Register a CRM-specific list view that uses "New Lead" label
export const crmLeadListView = {
    ...listView,
    Controller: class extends listView.Controller {
        static template = "freight_forwarding_crm.ListView";
    },
};
registry.category("views").add("crm_lead_list", crmLeadListView);
