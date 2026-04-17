/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";

export class Freight_ForwardingHomeDashboard extends Component {
    static template = "freight_forwarding_home.Dashboard";
    static props = { "*": true };

    setup() {
        this.actionService = useService("action");
        this.menuService = useService("menu");
    }

    get userName() {
        return session.name || "Employee";
    }

    async openSales() {
        const menus = this.menuService.getAll();
        const salesMenu = menus.find(m => m.xmlid === "sale.sale_menu_root");
        if (salesMenu) {
            this.menuService.selectMenu(salesMenu.id);
        }
    }

    async openCRM() {
        const menus = this.menuService.getAll();
        const crmMenu = menus.find(m => m.xmlid === "crm.crm_menu_root");
        if (crmMenu) {
            this.menuService.selectMenu(crmMenu.id);
        }
    }

    async openMasterData() {
        const menus = this.menuService.getAll();
        const masterDataMenu = menus.find(m => m.xmlid === "freight_forwarding_master_data.menu_master_data_root");
        if (masterDataMenu) {
            this.menuService.selectMenu(masterDataMenu.id);
        }
    }

    async openShipment() {
        await this.actionService.doAction("freight_forwarding_freight.action_logistics_job");
    }
}

registry.category("actions").add("freight_forwarding_home.dashboard", Freight_ForwardingHomeDashboard);
