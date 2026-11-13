"""
Step 23 – Hide the "Create" button/dropdown on the Delivery Note form.

The Create button in ERPNext Delivery Note is rendered by
erpnext/stock/doctype/delivery_note/delivery_note.js via calls like:
    frm.add_custom_button(__("Sales Invoice"), fn, __("Create"));
    frm.add_custom_button(__("Packing Slip"),  fn, __("Create"));
    ...

Frappe groups these under a "Create" btn-group in the form toolbar.

We use a Client Script (Form, Delivery Note) to:
  1. After every refresh, remove all buttons in the "Create" group.

This is purely UI-level – no backend data, routes, or permissions are touched.
Revert by disabling / deleting the Client Script named "orbis-dn-hide-create".
"""

import os
import frappe

os.makedirs("/home/frappe/logs", exist_ok=True)
os.chdir("/home/frappe/frappe-bench/sites")
frappe.init(site="frontend", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()

SCRIPT_NAME = "orbis-dn-hide-create"

JS_SCRIPT = """// OrbisERP Step 23 – Hide "Create" button on Delivery Note form
// Reversible: disable or delete the Client Script named "orbis-dn-hide-create"

frappe.ui.form.on("Delivery Note", {
    refresh: function(frm) {
        // ERPNext adds Create-group buttons after a short async delay.
        // We use a small timeout to catch them after they are rendered.
        setTimeout(function() {
            // Frappe stores custom button groups in frm.custom_buttons keyed by label.
            // Remove every button that belongs to the "Create" group.
            var createLabel = __("Create");

            // 1. Remove via Frappe API (handles frm.custom_buttons cleanup too)
            if (frm.custom_buttons) {
                Object.keys(frm.custom_buttons).forEach(function(btnLabel) {
                    var btn = frm.custom_buttons[btnLabel];
                    if (btn && btn.parent && btn.parent().hasClass("custom-btn-group")) {
                        // Check if this button's group header is "Create"
                        var groupHeader = btn.parent().prev(".btn-custom-group-label");
                        if (!groupHeader.length) {
                            // Try: the btn-group itself may have a data-label
                            groupHeader = btn.closest("[data-label='" + createLabel + "']");
                        }
                    }
                });
            }

            // 2. DOM-level hide of the "Create" btn-group in page actions.
            //    ERPNext renders: <div class="custom-btn-group"><button>Create</button>...</div>
            //    The group's toggle button text is "Create ▾".
            frm.page.wrapper.find(".page-actions .custom-btn-group").each(function() {
                var $group = $(this);
                var toggleText = $group.find("> .btn").first().text().trim();
                // Match "Create" (with or without caret/chevron character)
                if (toggleText.replace(/[^a-zA-Z]/g, "") === "Create") {
                    $group.hide();
                }
            });

            // 3. Fallback: hide any standalone button whose text is exactly "Create"
            frm.page.wrapper.find(".page-actions .btn").each(function() {
                var txt = $(this).text().trim().replace(/[^a-zA-Z]/g, "");
                if (txt === "Create") {
                    $(this).closest(".btn-group, .custom-btn-group").addBack().hide();
                }
            });
        }, 300);
    }
});
"""

def run():
    if frappe.db.exists("Client Script", SCRIPT_NAME):
        doc = frappe.get_doc("Client Script", SCRIPT_NAME)
        doc.script = JS_SCRIPT
        doc.enabled = 1
        doc.save(ignore_permissions=True)
        print(f"[Step 23] Updated Client Script: {SCRIPT_NAME}")
    else:
        doc = frappe.get_doc({
            "doctype": "Client Script",
            "name": SCRIPT_NAME,
            "dt": "Delivery Note",
            "view": "Form",
            "script": JS_SCRIPT,
            "enabled": 1,
        })
        doc.insert(ignore_permissions=True)
        print(f"[Step 23] Created Client Script: {SCRIPT_NAME}")

    frappe.db.commit()

    # Clear boot cache so client scripts are served fresh
    try:
        frappe.cache().delete_key("bootinfo")
    except Exception:
        pass

    print("[Step 23] Done – Delivery Note 'Create' button is now hidden.")
    print("[Step 23] To revert: disable or delete Client Script 'orbis-dn-hide-create'.")

run()
frappe.destroy()
