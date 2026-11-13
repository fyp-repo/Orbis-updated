"""
Step 18: Purchase Module UI Fixes
==================================
Implements the following Purchase/Buying module UI fixes:

1. Material Request - Filter Connections section to only show:
   - Request for Quotation, Supplier Quotation, Purchase Order,
     Purchase Receipt, Stock Entry, Work Order
   (Hides: Pick List, Internal Transfer, Sales Order, Cost Center)

2. Supplier - Hide the "Edit Full" button from the Supplier quick form
   via a Client Script.

3. RFQ - Hide "Opportunity" from the "Get Items From" dropdown.

4. RFQ - Fix missing RFQ display (list refresh + cache clear approach).

5. Auto-refresh: Add a Client Script hook to auto-refresh workspace
   shortcuts after customizations.

Scope: ONLY Purchase/Buying module. No changes to Stock, Manufacturing,
Accounts, or other modules.
"""

import frappe


def upsert_client_script(name, dt, code, view="Form"):
    if frappe.db.exists("Client Script", name):
        cs = frappe.get_doc("Client Script", name)
        cs.script = code
        cs.enabled = 1
        cs.save(ignore_permissions=True)
        print(f"  [UPDATED] Client Script: {name}")
    else:
        cs = frappe.get_doc({
            "doctype": "Client Script",
            "name": name,
            "dt": dt,
            "view": view,
            "enabled": 1,
            "script": code
        })
        cs.insert(ignore_permissions=True)
        print(f"  [CREATED] Client Script: {name}")


def fix1_material_request_connections():
    print("\n--- Fix 1: Material Request - filter Connections section ---")
    script_code = """
frappe.ui.form.on('Material Request', {
    refresh: function(frm) {
        filter_mr_connections(frm);
    }
});

function filter_mr_connections(frm) {
    var allowed = [
        'Request for Quotation',
        'Supplier Quotation',
        'Purchase Order',
        'Purchase Receipt',
        'Stock Entry',
        'Work Order'
    ];

    function do_filter() {
        if (frm.dashboard && frm.dashboard.data && frm.dashboard.data.transactions) {
            frm.dashboard.data.transactions.forEach(function(group) {
                if (group.items) {
                    group.items = group.items.filter(function(item) {
                        return allowed.indexOf(item) !== -1;
                    });
                }
            });
            frm.dashboard.data.transactions = frm.dashboard.data.transactions.filter(function(g) {
                return g.items && g.items.length > 0;
            });
        }
        var hidden_dts = ['Pick List', 'Internal Transfer', 'Sales Order', 'Cost Center'];
        hidden_dts.forEach(function(dt) {
            $('.document-link[data-doctype="' + dt + '"]').hide();
        });
    }

    do_filter();
    setTimeout(do_filter, 200);
    setTimeout(do_filter, 600);
    setTimeout(do_filter, 1200);
}
"""
    upsert_client_script("Orbis MR Connections Filter", "Material Request", script_code)


def fix2_supplier_hide_edit_full():
    print("\n--- Fix 2: Supplier - Hide Edit Full button ---")
    script_code = """
frappe.ui.form.on('Supplier', {
    refresh: function(frm) { hide_edit_full(frm); },
    onload: function(frm) { hide_edit_full(frm); }
});

function hide_edit_full(frm) {
    function do_hide() {
        frm.wrapper.find('.btn-edit-full').hide();
        frm.wrapper.find('[data-label="Edit Full"]').hide();
        frm.wrapper.find('button:contains("Edit Full")').hide();
        frm.wrapper.find('a:contains("Edit Full")').hide();
        frm.wrapper.find('.edit-full').hide();
        frm.wrapper.find('[title="Edit in Full Page"]').hide();
        $('[data-label="Edit in Full Page"]').hide();
        $('.modal-dialog .btn-modal-edit-full').hide();
        $('.quick-entry-btn').filter(function() {
            var t = $(this).text().toLowerCase();
            return t.indexOf('edit full') !== -1 || t.indexOf('edit in full page') !== -1;
        }).hide();
    }
    do_hide();
    setTimeout(do_hide, 150);
    setTimeout(do_hide, 500);
}
"""
    upsert_client_script("Orbis Supplier Hide Edit Full", "Supplier", script_code)

    list_script = """
frappe.listview_settings['Supplier'] = frappe.listview_settings['Supplier'] || {};
var _orig = frappe.listview_settings['Supplier'].onload;
frappe.listview_settings['Supplier'].onload = function(listview) {
    if (_orig) _orig(listview);
    var observer = new MutationObserver(function() {
        $('.btn-edit-full, .edit-full, [data-label="Edit Full"], [title="Edit in Full Page"]').hide();
        $('button, a').filter(function() {
            var t = $(this).text().trim().toLowerCase();
            return t === 'edit full' || t === 'edit in full page';
        }).hide();
    });
    observer.observe(document.body, { childList: true, subtree: true });
};
"""
    upsert_client_script("Orbis Supplier List Hide Edit Full", "Supplier", list_script, view="List")


def fix3_rfq_hide_opportunity():
    print("\n--- Fix 3: RFQ - Hide Opportunity from Get Items From ---")
    script_code = """
frappe.ui.form.on('Request for Quotation', {
    refresh: function(frm) {
        filter_rfq_opportunity(frm);
    }
});

function filter_rfq_opportunity(frm) {
    function do_filter() {
        $('li[data-label="Opportunity"]').hide();
        $('.dropdown-menu li a').filter(function() {
            return $(this).text().trim() === 'Opportunity';
        }).closest('li').hide();
        frm.page.inner_toolbar && frm.page.inner_toolbar.find('[data-label="Opportunity"]').closest('li').hide();
    }
    do_filter();
    setTimeout(do_filter, 300);
    setTimeout(do_filter, 800);
    $(document).off('show.bs.dropdown.rfq_opp').on('show.bs.dropdown.rfq_opp', function() {
        setTimeout(do_filter, 50);
    });
}
"""
    upsert_client_script("Orbis RFQ Hide Opportunity", "Request for Quotation", script_code)

    meta = frappe.get_meta("Request for Quotation")
    if meta.get_field("opportunity"):
        name = "Request for Quotation-opportunity-hidden"
        if frappe.db.exists("Property Setter", name):
            ps = frappe.get_doc("Property Setter", name)
            ps.value = "1"
            ps.save(ignore_permissions=True)
        else:
            frappe.get_doc({
                "doctype": "Property Setter",
                "name": name,
                "doc_type": "Request for Quotation",
                "doctype_or_field": "DocField",
                "field_name": "opportunity",
                "property": "hidden",
                "value": "1",
                "property_type": "Check"
            }).insert(ignore_permissions=True)
        print("  [DONE] Property Setter: RFQ opportunity field hidden")


def fix4_rfq_fix_display():
    print("\n--- Fix 4: RFQ - Fix missing RFQ display ---")
    try:
        frappe.cache().delete_keys("*Request for Quotation*")
        print("  [DONE] Cleared RFQ cache keys")
    except Exception as e:
        print(f"  [WARN] Cache clear: {e}")

    list_script = """
frappe.listview_settings['Request for Quotation'] = frappe.listview_settings['Request for Quotation'] || {};
var _orig_rfq = frappe.listview_settings['Request for Quotation'].onload;
frappe.listview_settings['Request for Quotation'].onload = function(listview) {
    if (_orig_rfq) _orig_rfq.call(this, listview);
    if (listview && listview.filter_area) {
        listview.refresh();
    }
};
"""
    upsert_client_script("Orbis RFQ List Fix", "Request for Quotation", list_script, view="List")

    for role in ["Purchase Manager", "Purchase Officer"]:
        existing = frappe.get_all(
            "Custom DocPerm",
            filters={"parent": "Request for Quotation", "role": role}
        )
        if not existing:
            frappe.get_doc({
                "doctype": "Custom DocPerm",
                "parent": "Request for Quotation",
                "parenttype": "DocType",
                "parentfield": "permissions",
                "role": role,
                "read": 1, "write": 1, "create": 1,
                "submit": 1, "cancel": 1, "amend": 1,
                "permlevel": 0
            }).insert(ignore_permissions=True)
            print(f"  [DONE] Added DocPerm for {role} on Request for Quotation")


def fix5_auto_refresh():
    print("\n--- Fix 5: Auto UI refresh helper ---")
    script_code = """
frappe.ui.form.on('Material Request', {
    after_save: function(frm) {
        setTimeout(function() {
            if (frm.dashboard && frm.dashboard.refresh) frm.dashboard.refresh();
        }, 800);
    }
});
"""
    upsert_client_script("Orbis MR Auto Refresh", "Material Request", script_code)

    po_script = """
frappe.ui.form.on('Purchase Order', {
    after_save: function(frm) {
        setTimeout(function() {
            if (frm.dashboard && frm.dashboard.refresh) frm.dashboard.refresh();
        }, 800);
    }
});
"""
    upsert_client_script("Orbis PO Auto Refresh", "Purchase Order", po_script)
    print("  [DONE] Auto-refresh helpers installed.")
    print("  NOTE: Server-side changes still require one browser reload to appear.")


def run():
    print("=" * 60)
    print("OrbisERP Step 18: Purchase Module UI Fixes")
    print("=" * 60)

    fix1_material_request_connections()
    fix2_supplier_hide_edit_full()
    fix3_rfq_hide_opportunity()
    fix4_rfq_fix_display()
    fix5_auto_refresh()

    frappe.clear_cache()
    frappe.db.commit()

    print("\n" + "=" * 60)
    print("All 5 Purchase UI fixes applied!")
    print("=" * 60)
    print("\nSummary:")
    print("  1. MR Connections: filtered to PO-chain only")
    print("  2. Supplier: Edit Full button hidden")
    print("  3. RFQ: Opportunity hidden from Get Items From")
    print("  4. RFQ: List display fix + cache cleared")
    print("  5. Auto-refresh helper scripts installed")
    print("\nDo ONE browser reload (Ctrl+Shift+R) to see all changes.")
    return "Done"


if __name__ == "__main__":
    run()
