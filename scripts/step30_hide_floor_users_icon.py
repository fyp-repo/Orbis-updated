"""
Step 30: Remove Floor Users Icon from Main Desktop/Framework Launcher
=====================================================================
Removes only the Floor Users icon/card from the main desktop module launcher
while strictly preserving:
- Floor Users Workspace document and route
- All underlying DocTypes (Job Card, Work Order, Issue, Non Conformance, etc.)
- User roles, permissions, and Floor Worker access
- All other module cards/icons on the desktop launcher
"""

import frappe

def run():
    print("=" * 80)
    print("  STEP 30: REMOVE FLOOR USERS ICON FROM MAIN FRAMEWORK LAUNCHER")
    print("=" * 80)

    # 1. Update Desktop Icon records
    if frappe.db.exists("DocType", "Desktop Icon"):
        icons = frappe.get_all(
            "Desktop Icon",
            filters={"link_to": ["in", ["Floor Users (Workers)", "Floor Users"]]},
            fields=["name", "label", "hidden"]
        )
        for icon in icons:
            frappe.db.set_value("Desktop Icon", icon.name, "hidden", 1)
            print(f"  [OK] Set hidden=1 on Desktop Icon: {icon.name} (label='{icon.label}')")

        # Also check by name/label substring if any
        more_icons = frappe.get_all(
            "Desktop Icon",
            filters={"name": ["like", "%Floor Users%"], "hidden": 0},
            fields=["name", "label"]
        )
        for icon in more_icons:
            frappe.db.set_value("Desktop Icon", icon.name, "hidden", 1)
            print(f"  [OK] Set hidden=1 on Desktop Icon: {icon.name}")

    # 2. Update Workspace record
    ws_names = frappe.get_all(
        "Workspace",
        filters={"name": ["in", ["Floor Users (Workers)", "Floor Users"]]},
        pluck="name"
    )
    for ws_name in ws_names:
        frappe.db.set_value("Workspace", ws_name, {
            "public": 0,
            "is_hidden": 1
        })
        print(f"  [OK] Set public=0, is_hidden=1 on Workspace: {ws_name}")

    # 3. Clear desktop icons caches
    try:
        from frappe.desk.doctype.desktop_icon.desktop_icon import clear_every_users_desktop_icons
        clear_every_users_desktop_icons()
        print("  [OK] Cleared all users' desktop icon caches.")
    except Exception as e:
        print(f"  [INFO] Desktop icon cache clear: {e}")

    frappe.clear_cache()
    frappe.db.commit()

    # 4. Verification
    visible_workspaces = frappe.get_all(
        "Workspace",
        filters={"public": 1, "is_hidden": 0},
        fields=["name", "title"]
    )
    visible_titles = [w.title for w in visible_workspaces]
    print(f"\n  Active Public Workspaces: {visible_titles}")
    assert "Floor Users (Workers)" not in visible_titles, "Floor Users should not be in public workspaces"

    if frappe.db.exists("DocType", "Desktop Icon"):
        visible_icons = frappe.get_all(
            "Desktop Icon",
            filters={"hidden": 0},
            fields=["name", "label"]
        )
        visible_labels = [i.label for i in visible_icons]
        print(f"  Active Desktop Icons: {visible_labels}")
        assert not any("Floor" in l for l in visible_labels), "Floor Users should not be in active desktop icons"

    # Verify Floor Worker doctypes still exist
    assert frappe.db.exists("DocType", "Job Card"), "Job Card doctype must exist"
    assert frappe.db.exists("DocType", "Work Order"), "Work Order doctype must exist"
    assert frappe.db.exists("Workspace", "Floor Users (Workers)"), "Floor Users Workspace record must still exist"

    print("\n" + "=" * 80)
    print("  STEP 30 COMPLETED SUCCESSFULLY: FLOOR USERS LAUNCHER ICON HIDDEN")
    print("=" * 80)
    return "Floor Users launcher icon successfully removed from main framework."

def main():
    return run()

if __name__ == "__main__":
    frappe.init(site="frontend", sites_path="/home/frappe/frappe-bench/sites")
    frappe.connect()
    run()
    frappe.destroy()

