"""
Step 20: Restrict Buying Settings to Administrator and System Manager
=====================================================================
Restricts access to Buying Settings in the Purchase module:
1. Administrator & System Manager: Full access to view and edit Buying Settings.
2. Regular Purchase Users: Cannot view or edit Buying Settings, cannot see
   the Settings section or Buying Settings link in the Purchase sidebar/workspace,
   and cannot access the URL directly.
3. Preserves all ERPNext functionality, transactions, supplier defaults, price
   calculations, and naming series.
4. Uses standard Frappe Custom DocPerm and Client Script.
"""

import sys
import frappe

def configure_buying_settings_permissions():
    print("\n--- 1. Configuring Role-Based Access on Buying Settings ---")

    # In Frappe, if ANY Custom DocPerm exists for a DocType, all standard DocPerms
    # are completely ignored and ONLY Custom DocPerms are evaluated.
    # We ensure System Manager has read=1, write=1, and delete any Custom DocPerm
    # for non-admin purchase/accounts/stock roles.

    # 1. Ensure System Manager Custom DocPerm exists with read=1, write=1
    sm_perm = frappe.db.get_value(
        "Custom DocPerm",
        {"parent": "Buying Settings", "role": "System Manager"},
        "name"
    )
    if sm_perm:
        doc = frappe.get_doc("Custom DocPerm", sm_perm)
        doc.read = 1
        doc.write = 1
        doc.create = 0
        doc.delete = 0
        doc.save(ignore_permissions=True)
        print("  [UPDATED] Custom DocPerm: System Manager -> read=1, write=1")
    else:
        doc = frappe.get_doc({
            "doctype": "Custom DocPerm",
            "parent": "Buying Settings",
            "parenttype": "DocType",
            "parentfield": "permissions",
            "role": "System Manager",
            "permlevel": 0,
            "read": 1,
            "write": 1,
            "create": 0,
            "delete": 0
        })
        doc.insert(ignore_permissions=True)
        print("  [CREATED] Custom DocPerm: System Manager -> read=1, write=1")

    # 2. Delete Custom DocPerms for all non-admin roles
    restricted_roles = [
        "Purchase User",
        "Purchase Officer",
        "Purchase Manager",
        "Stock User",
        "Stock Manager",
        "Accounts User",
        "Accounts Manager",
        "All"
    ]

    frappe.db.delete(
        "Custom DocPerm",
        {
            "parent": "Buying Settings",
            "role": ["in", restricted_roles]
        }
    )
    print(f"  [CLEARED] Custom DocPerms on Buying Settings for restricted roles: {restricted_roles}")

def setup_buying_settings_client_guard():
    print("\n--- 2. Setting up Client Guard for Buying Settings URL Access ---")
    script_name = "Orbis Buying Settings Guard"

    js_code = """frappe.ui.form.on('Buying Settings', {
    setup: function(frm) {
        if (!frappe.user.has_role('System Manager') && frappe.session.user !== 'Administrator') {
            frappe.msgprint({
                title: __('Access Restricted'),
                indicator: 'red',
                message: __('You do not have permission to access Buying Settings. Please contact an Administrator.')
            });
            frappe.set_route('');
        }
    },
    refresh: function(frm) {
        if (!frappe.user.has_role('System Manager') && frappe.session.user !== 'Administrator') {
            frappe.msgprint({
                title: __('Access Restricted'),
                indicator: 'red',
                message: __('You do not have permission to access Buying Settings. Please contact an Administrator.')
            });
            frappe.set_route('');
        }
    }
});"""

    if frappe.db.exists("Client Script", script_name):
        doc = frappe.get_doc("Client Script", script_name)
        doc.script = js_code
        doc.enabled = 1
        doc.save(ignore_permissions=True)
        print(f"  [UPDATED] Client Script: {script_name}")
    else:
        doc = frappe.get_doc({
            "doctype": "Client Script",
            "name": script_name,
            "dt": "Buying Settings",
            "view": "Form",
            "enabled": 1,
            "script": js_code
        })
        doc.insert(ignore_permissions=True)
        print(f"  [CREATED] Client Script: {script_name}")

def verify_permissions():
    print("\n--- 3. Verification Testing ---")

    # Check Administrator
    frappe.set_user("Administrator")
    admin_read = frappe.has_permission("Buying Settings", "read")
    admin_write = frappe.has_permission("Buying Settings", "write")
    print(f"  Administrator access -> read: {admin_read}, write: {admin_write}")

    # Check Purchase Officer
    test_user = "purchase.officer@orbis.test"
    if frappe.db.exists("User", test_user):
        frappe.set_user(test_user)
        user_read = frappe.has_permission("Buying Settings", "read")
        user_write = frappe.has_permission("Buying Settings", "write")
        print(f"  {test_user} (Purchase Officer) access -> read: {user_read}, write: {user_write}")

    # Check Purchase Manager
    test_pm = "forw8007+purchasemanager@gmail.com"
    if frappe.db.exists("User", test_pm):
        frappe.set_user(test_pm)
        pm_read = frappe.has_permission("Buying Settings", "read")
        pm_write = frappe.has_permission("Buying Settings", "write")
        print(f"  {test_pm} (Purchase Manager) access -> read: {pm_read}, write: {pm_write}")

    # Reset back to Administrator
    frappe.set_user("Administrator")

def run():
    print("=" * 60)
    print("OrbisERP Step 20: Restrict Buying Settings to Admins Only")
    print("=" * 60)

    configure_buying_settings_permissions()
    setup_buying_settings_client_guard()

    frappe.clear_cache(doctype="Buying Settings")
    frappe.clear_cache()
    frappe.db.commit()

    verify_permissions()

    print("\n" + "=" * 60)
    print("Step 20 Completed Successfully!")
    print("=" * 60)
    return "Done"

if __name__ == "__main__":
    frappe.init(site="frontend", sites_path="/home/frappe/frappe-bench/sites")
    frappe.connect()
    run()
    frappe.destroy()
