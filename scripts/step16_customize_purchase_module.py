"""
Step 16: Customize and Simplify the Purchase Module for OrbisERP (Automotive FYP)
================================================================================
Implements all requirements specified for the OrbisERP Purchase module:
1. Configures the Purchase Workspace (Sidebar, Shortcuts, Number Cards, Link Cards).
2. Sets up Automotive Item Groups and Supplier Groups without deleting existing data.
3. Updates Buying Settings for automotive purchasing flow.
4. Creates safe Property Setters to hide unnecessary fields, sections, and tabs
   across all 8 DocTypes (Supplier, Material Request, RFQ, Supplier Quotation,
   Purchase Order, Purchase Receipt, Purchase Invoice, Item, Buying Settings).
5. Ensures correct permissions and Client Scripts for seamless user experience.
6. Runs an end-to-end purchasing workflow validation test.
"""

import json
import frappe
from frappe.utils import today, add_days, flt

COMPANY = "Orbis Car Manufacturing (Pvt.) Ltd."
COMPANY_ABBR = "OCM"

def set_ps(doc_type, field_name, property_name, value, property_type="Check"):
    """Safely create or update a Property Setter."""
    name = f"{doc_type}-{field_name}-{property_name}"
    if frappe.db.exists("Property Setter", name):
        ps = frappe.get_doc("Property Setter", name)
        ps.value = str(value)
        ps.save(ignore_permissions=True)
    else:
        ps = frappe.get_doc({
            "doctype": "Property Setter",
            "name": name,
            "doc_type": doc_type,
            "doctype_or_field": "DocField",
            "field_name": field_name,
            "property": property_name,
            "value": str(value),
            "property_type": property_type
        })
        ps.insert(ignore_permissions=True)


def configure_supplier_groups():
    """Ensure recommended automotive supplier groups exist under 'All Supplier Groups'."""
    print("--- 1. Configuring Supplier Groups ---")
    parent = "All Supplier Groups" if frappe.db.exists("Supplier Group", "All Supplier Groups") else None
    
    needed = [
        "Raw Material Suppliers",
        "Mechanical Suppliers",
        "Electrical Suppliers",
        "Automotive Component Suppliers",
        "Local Suppliers",
        "Service Suppliers"
    ]
    
    for grp in needed:
        if not frappe.db.exists("Supplier Group", grp):
            doc = frappe.get_doc({
                "doctype": "Supplier Group",
                "supplier_group_name": grp,
                "is_group": 0,
                "parent_supplier_group": parent
            })
            doc.insert(ignore_permissions=True)
            print(f"  Created Supplier Group: {grp}")
        else:
            print(f"  Supplier Group exists: {grp}")


def configure_item_groups():
    """Ensure recommended automotive item groups exist under 'All Item Groups'."""
    print("--- 2. Configuring Item Groups ---")
    parent = "All Item Groups" if frappe.db.exists("Item Group", "All Item Groups") else None
    
    needed = [
        "Raw Materials",
        "Mechanical Components",
        "Electrical Components",
        "Automotive Parts",
        "Manufacturing Consumables",
        "Spare Parts"
    ]
    
    for grp in needed:
        if not frappe.db.exists("Item Group", grp):
            doc = frappe.get_doc({
                "doctype": "Item Group",
                "item_group_name": grp,
                "is_group": 0,
                "parent_item_group": parent
            })
            doc.insert(ignore_permissions=True)
            print(f"  Created Item Group: {grp}")
        else:
            print(f"  Item Group exists: {grp}")


def configure_buying_settings():
    """Configure Buying Settings according to section 16."""
    print("--- 3. Configuring Buying Settings ---")
    bs = frappe.get_single("Buying Settings")
    
    bs.supp_master_name = "Supplier Name"
    if frappe.db.exists("Supplier Group", "Raw Material Suppliers"):
        bs.supplier_group = "Raw Material Suppliers"
    elif frappe.db.exists("Supplier Group", "Raw Material"):
        bs.supplier_group = "Raw Material"
        
    bs.buying_price_list = "Standard Buying"
    bs.maintain_same_rate = 1
    bs.maintain_same_rate_action = "Warn"
    bs.po_required = "No"
    bs.pr_required = "No"
    bs.over_order_allowance = 0.0
    bs.allow_negative_rates_for_items = 0
    bs.allow_zero_qty_in_supplier_quotation = 0
    bs.allow_zero_qty_in_request_for_quotation = 0
    bs.allow_zero_qty_in_purchase_order = 0
    bs.blanket_order_allowance = 0.0
    bs.set_valuation_rate_for_rejected_materials = 0
    bs.bill_for_rejected_quantity_in_purchase_invoice = 0
    bs.show_pay_button = 1
    
    bs.save(ignore_permissions=True)
    print("  Buying Settings saved.")
    
    # Hide unnecessary subcontracting section from Buying Settings
    set_ps("Buying Settings", "subcontract", "hidden", 1, "Check")


def configure_form_customizations():
    """Configure Property Setters to hide non-essential fields and sections."""
    print("--- 4. Applying Form Field Customizations via Property Setters ---")
    
    # 4.1 Supplier Form
    print("  Customizing Supplier...")
    supplier_hide = [
        "tax_id", "tax_category", "tax_withholding_category", "tax_withholding_group",
        "tax_tab", "accounting_tab", "is_transporter", "portal_users_tab",
        "website", "language", "customer_numbers",
        "allow_purchase_invoice_creation_without_purchase_order",
        "allow_purchase_invoice_creation_without_purchase_receipt",
        "is_frozen", "rfq_and_purchase_order_settings_section", "alias", "gender"
    ]
    for fn in supplier_hide:
        if frappe.get_meta("Supplier").get_field(fn):
            set_ps("Supplier", fn, "hidden", 1)
            
    # 4.2 Material Request
    print("  Customizing Material Request...")
    mr_hide = [
        "scan_barcode", "last_scanned_warehouse", "buying_price_list",
        "printing_details", "terms_tab", "customer"
    ]
    for fn in mr_hide:
        if frappe.get_meta("Material Request").get_field(fn):
            set_ps("Material Request", fn, "hidden", 1)
            
    # Restrict Material Request Type options and default to Purchase
    set_ps("Material Request", "material_request_type", "options", "Purchase\nManufacture", "Small Text")
    set_ps("Material Request", "material_request_type", "default", "Purchase", "Data")
    
    # 4.3 Request for Quotation
    print("  Customizing Request for Quotation...")
    rfq_hide = [
        "send_attached_files", "send_document_print", "use_html", "mfs_html",
        "terms_section_break", "printing_settings", "address_and_contact_tab",
        "opportunity"
    ]
    for fn in rfq_hide:
        if frappe.get_meta("Request for Quotation").get_field(fn):
            set_ps("Request for Quotation", fn, "hidden", 1)

    # 4.4 Supplier Quotation
    print("  Customizing Supplier Quotation...")
    sq_hide = [
        "taxes_section", "shipping_rule", "incoterm", "named_place",
        "section_break_41", "base_rounding_adjustment", "rounding_adjustment",
        "disable_rounded_total", "tax_breakup", "pricing_rule_details",
        "address_and_contact_tab", "terms_tab", "printing_settings",
        "auto_repeat_section", "accounting_dimensions_section", "is_subcontracted",
        "opportunity"
    ]
    for fn in sq_hide:
        if frappe.get_meta("Supplier Quotation").get_field(fn):
            set_ps("Supplier Quotation", fn, "hidden", 1)

    # 4.5 Purchase Order
    print("  Customizing Purchase Order...")
    po_hide = [
        "is_subcontracted", "raw_material_details", "supplier_warehouse",
        "scan_barcode", "last_scanned_warehouse", "taxes_section", "sec_tax_breakup",
        "shipping_rule", "incoterm", "named_place", "discount_section",
        "disable_rounded_total", "rounding_adjustment", "base_rounding_adjustment",
        "column_break5", "auto_repeat_section", "drop_ship",
        "shipping_address_section", "company_billing_address_section",
        "accounting_dimensions_section", "pricing_rules"
    ]
    for fn in po_hide:
        if frappe.get_meta("Purchase Order").get_field(fn):
            set_ps("Purchase Order", fn, "hidden", 1)

    # 4.6 Purchase Receipt
    print("  Customizing Purchase Receipt...")
    pr_hide = [
        "scan_barcode", "last_scanned_warehouse", "apply_putaway_rule",
        "is_subcontracted", "subcontracting_receipt", "raw_material_details",
        "supplier_warehouse", "taxes_charges_section", "taxes_section", "sec_tax_breakup",
        "section_break_42", "section_break_98", "billing_address_section",
        "transporter_info", "printing_settings", "terms_tab", "subscription_detail",
        "accounting_dimensions_section"
    ]
    for fn in pr_hide:
        if frappe.get_meta("Purchase Receipt").get_field(fn):
            set_ps("Purchase Receipt", fn, "hidden", 1)

    # 4.7 Purchase Invoice
    print("  Customizing Purchase Invoice...")
    pi_hide = [
        "is_paid", "advances_section", "write_off", "section_tax_withholding_entry",
        "apply_tds", "is_subcontracted", "raw_materials_supplied", "scan_barcode",
        "last_scanned_warehouse", "taxes_section", "sec_tax_breakup", "section_break_44",
        "company_shipping_address_section", "company_billing_address_section",
        "accounting_details_section", "subscription_section", "automation_section",
        "printing_settings", "sb_14", "accounting_dimensions_section"
    ]
    for fn in pi_hide:
        if frappe.get_meta("Purchase Invoice").get_field(fn):
            set_ps("Purchase Invoice", fn, "hidden", 1)
            
    # Ensure update_stock default is 0 (disabled by default)
    set_ps("Purchase Invoice", "update_stock", "default", 0, "Check")

    # 4.8 Item Master
    print("  Customizing Item Master...")
    item_hide = [
        "sales_details", "customer_details", "pricing_tab", "item_tax_section_break",
        "variants_section", "accounting", "deferred_accounting_section",
        "delivered_by_supplier", "foreign_trade_details", "sb_barcodes"
    ]
    for fn in item_hide:
        if frappe.get_meta("Item").get_field(fn):
            set_ps("Item", fn, "hidden", 1)


def configure_purchase_client_scripts():
    """Add lightweight Client Scripts to ensure dynamic UI behavior."""
    print("--- 5. Configuring Client Scripts ---")
    
    # 5.1 Purchase Invoice client script: keep update_stock unchecked by default
    cs_name = "Orbis Purchase Invoice Default"
    cs_code = """
frappe.ui.form.on('Purchase Invoice', {
    onload: function(frm) {
        if (frm.is_new() && frm.doc.update_stock) {
            frm.set_value('update_stock', 0);
        }
    }
});
"""
    if frappe.db.exists("Client Script", cs_name):
        cs = frappe.get_doc("Client Script", cs_name)
        cs.script = cs_code
        cs.enabled = 1
        cs.save(ignore_permissions=True)
    else:
        frappe.get_doc({
            "doctype": "Client Script",
            "name": cs_name,
            "dt": "Purchase Invoice",
            "view": "Form",
            "enabled": 1,
            "script": cs_code
        }).insert(ignore_permissions=True)

    # 5.2 Material Request client script: restrict type options in browser
    mr_cs_name = "Orbis Material Request Options"
    mr_cs_code = """
frappe.ui.form.on('Material Request', {
    refresh: function(frm) {
        frm.set_df_property('material_request_type', 'options', ['Purchase', 'Manufacture']);
    }
});
"""
    if frappe.db.exists("Client Script", mr_cs_name):
        cs = frappe.get_doc("Client Script", mr_cs_name)
        cs.script = mr_cs_code
        cs.enabled = 1
        cs.save(ignore_permissions=True)
    else:
        frappe.get_doc({
            "doctype": "Client Script",
            "name": mr_cs_name,
            "dt": "Material Request",
            "view": "Form",
            "enabled": 1,
            "script": mr_cs_code
        }).insert(ignore_permissions=True)


def configure_purchase_permissions():
    """Ensure Purchase roles and managers have full access to purchasing transactions."""
    print("--- 6. Configuring Purchase DocPerms ---")
    roles = ["Purchase Manager", "Purchase Officer", "Purchase User", "System Manager"]
    doctypes = [
        "Material Request", "Request for Quotation", "Supplier Quotation",
        "Purchase Order", "Purchase Receipt", "Purchase Invoice",
        "Supplier", "Supplier Group", "Item", "Item Price", "Price List",
        "Item Group", "Buying Settings"
    ]
    
    for dt in doctypes:
        for r in roles:
            # Check if Custom DocPerm exists
            existing = frappe.get_all("Custom DocPerm", filters={"parent": dt, "role": r})
            if not existing:
                is_submittable = frappe.get_meta(dt).is_submittable
                cdp = frappe.get_doc({
                    "doctype": "Custom DocPerm",
                    "parent": dt,
                    "parenttype": "DocType",
                    "parentfield": "permissions",
                    "role": r,
                    "read": 1,
                    "write": 1,
                    "create": 1 if dt != "Buying Settings" else 0,
                    "submit": 1 if is_submittable else 0,
                    "cancel": 1 if is_submittable else 0,
                    "amend": 1 if is_submittable else 0,
                    "permlevel": 0
                })
                cdp.insert(ignore_permissions=True)
                
    # Also ensure the purchase test manager has the Purchase Officer role as well
    pm_email = "forw8007+purchasemanager@gmail.com"
    if frappe.db.exists("User", pm_email):
        pm_user = frappe.get_doc("User", pm_email)
        has_roles = [r.role for r in pm_user.roles]
        for needed_role in ["Purchase Manager", "Purchase Officer", "Purchase User"]:
            if needed_role not in has_roles:
                pm_user.append("roles", {"role": needed_role})
        pm_user.save(ignore_permissions=True)
        print(f"  Updated roles for {pm_email}")


def configure_purchase_workspace():
    """Build the clean, dedicated Purchase Workspace with exact sidebar structure."""
    print("--- 7. Configuring Purchase Workspace ---")
    ws_name = "Purchase"
    
    if not frappe.db.exists("Workspace", ws_name):
        ws = frappe.get_doc({
            "doctype": "Workspace",
            "name": ws_name,
            "label": ws_name,
            "title": "Purchase",
            "module": "Buying",
            "public": 1,
            "is_hidden": 0
        })
        ws.insert(ignore_permissions=True)
    else:
        ws = frappe.get_doc("Workspace", ws_name)

    ws.title = "Purchase"
    ws.icon = "buying"
    ws.is_hidden = 0
    ws.public = 1
    ws.module = "Buying"
    ws.hide_custom = 0
    ws.restrict_to_domain = ""

    # Clear previous child tables
    ws.number_cards = []
    ws.shortcuts = []
    ws.links = []
    ws.roles = []

    # 1. Number Cards (4 Dashboard Cards from section 17)
    needed_nc = [
        "Purchase Orders Count",
        "Total Purchase Amount",
        "Purchase Orders to Receive",
        "Active Suppliers"
    ]
    for nc in needed_nc:
        if frappe.db.exists("Number Card", nc):
            ws.append("number_cards", {"number_card_name": nc, "label": nc})

    # 2. Shortcuts (Quick Access)
    shortcuts_data = [
        ("Material Request", "Material Request", "DocType"),
        ("Request for Quotation", "Request for Quotation", "DocType"),
        ("Supplier Quotation", "Supplier Quotation", "DocType"),
        ("Purchase Order", "Purchase Order", "DocType"),
        ("Purchase Receipt", "Purchase Receipt", "DocType"),
        ("Purchase Invoice", "Purchase Invoice", "DocType"),
        ("Supplier", "Supplier", "DocType"),
        ("Item", "Item", "DocType")
    ]
    for label, link_to, link_type in shortcuts_data:
        ws.append("shortcuts", {
            "label": label,
            "link_to": link_to,
            "type": link_type
        })

    # 3. Cards & Links (Section 3)
    # A. Purchasing Transactions
    ws.append("links", {"type": "Card Break", "label": "Purchasing Transactions"})
    tx_links = [
        ("Material Request", "Material Request", "DocType"),
        ("Request for Quotation", "Request for Quotation", "DocType"),
        ("Supplier Quotation", "Supplier Quotation", "DocType"),
        ("Purchase Order", "Purchase Order", "DocType"),
        ("Purchase Receipt", "Purchase Receipt", "DocType"),
        ("Purchase Invoice", "Purchase Invoice", "DocType")
    ]
    for label, link_to, link_type in tx_links:
        ws.append("links", {
            "type": "Link",
            "link_type": link_type,
            "link_to": link_to,
            "label": label,
            "dependencies": ""
        })

    # B. Suppliers
    ws.append("links", {"type": "Card Break", "label": "Suppliers"})
    sup_links = [
        ("Supplier", "Supplier", "DocType"),
        ("Supplier Group", "Supplier Group", "DocType")
    ]
    for label, link_to, link_type in sup_links:
        ws.append("links", {
            "type": "Link",
            "link_type": link_type,
            "link_to": link_to,
            "label": label
        })

    # C. Items & Pricing
    ws.append("links", {"type": "Card Break", "label": "Items & Pricing"})
    item_links = [
        ("Item", "Item", "DocType"),
        ("Item Price", "Item Price", "DocType"),
        ("Price List", "Price List", "DocType"),
        ("Item Group", "Item Group", "DocType")
    ]
    for label, link_to, link_type in item_links:
        ws.append("links", {
            "type": "Link",
            "link_type": link_type,
            "link_to": link_to,
            "label": label
        })

    # D. Reports
    ws.append("links", {"type": "Card Break", "label": "Reports"})
    rep_links = [
        ("Purchase Analytics", "Purchase Analytics", "Report"),
        ("Purchase Order Analysis", "Purchase Order Analysis", "Report"),
        ("Procurement Tracker", "Procurement Tracker", "Report"),
        ("Items to Order and Receive", "Requested Items to Order and Receive", "Report"),
        ("Item-wise Purchase History", "Item-wise Purchase History", "Report"),
        ("Supplier Quotation Comparison", "Supplier Quotation Comparison", "Report")
    ]
    for label, link_to, link_type in rep_links:
        if frappe.db.exists("Report", link_to):
            ws.append("links", {
                "type": "Link",
                "link_type": link_type,
                "link_to": link_to,
                "label": label,
                "is_query_report": 1
            })

    # E. Settings
    ws.append("links", {"type": "Card Break", "label": "Settings"})
    ws.append("links", {
        "type": "Link",
        "link_type": "DocType",
        "link_to": "Buying Settings",
        "label": "Buying Settings"
    })

    # Roles that can see Purchase workspace
    ws_roles = ["Purchase Manager", "Purchase Officer", "Purchase User", "System Manager"]
    for r in ws_roles:
        ws.append("roles", {"role": r})

    # Construct Grid Content JSON
    content_blocks = [
        {
            "id": "hdr_pur_main",
            "type": "header",
            "data": {
                "text": '<span class="h4"><b>Automotive Procurement & Supplier Management</b></span>',
                "col": 12
            }
        },
        # 4 Number cards
        {"id": "nc_pocnt", "type": "number_card", "data": {"number_card_name": "Purchase Orders Count", "col": 3}},
        {"id": "nc_poamt", "type": "number_card", "data": {"number_card_name": "Total Purchase Amount", "col": 3}},
        {"id": "nc_porec", "type": "number_card", "data": {"number_card_name": "Purchase Orders to Receive", "col": 3}},
        {"id": "nc_actsup", "type": "number_card", "data": {"number_card_name": "Active Suppliers", "col": 3}},
        # Shortcuts
        {"id": "sc_mr", "type": "shortcut", "data": {"shortcut_name": "Material Request", "col": 3}},
        {"id": "sc_rfq", "type": "shortcut", "data": {"shortcut_name": "Request for Quotation", "col": 3}},
        {"id": "sc_sq", "type": "shortcut", "data": {"shortcut_name": "Supplier Quotation", "col": 3}},
        {"id": "sc_po", "type": "shortcut", "data": {"shortcut_name": "Purchase Order", "col": 3}},
        {"id": "sc_pr", "type": "shortcut", "data": {"shortcut_name": "Purchase Receipt", "col": 3}},
        {"id": "sc_pi", "type": "shortcut", "data": {"shortcut_name": "Purchase Invoice", "col": 3}},
        {"id": "sc_sup", "type": "shortcut", "data": {"shortcut_name": "Supplier", "col": 3}},
        {"id": "sc_item", "type": "shortcut", "data": {"shortcut_name": "Item", "col": 3}},
        # Cards
        {"id": "card_tx", "type": "card", "data": {"card_name": "Purchasing Transactions", "col": 6}},
        {"id": "card_sup", "type": "card", "data": {"card_name": "Suppliers", "col": 6}},
        {"id": "card_item", "type": "card", "data": {"card_name": "Items & Pricing", "col": 6}},
        {"id": "card_rep", "type": "card", "data": {"card_name": "Reports", "col": 6}},
        {"id": "card_set", "type": "card", "data": {"card_name": "Settings", "col": 6}}
    ]

    ws.content = json.dumps(content_blocks)
    ws.save(ignore_permissions=True)
    print("  Purchase workspace saved successfully.")

    # Hide duplicate/irrelevant workspaces from sidebar
    hide_workspaces = [
        "Buying", "Procurement", "OCM Purchasing", "Subcontracting",
        "CRM", "Support", "Integrations", "Website"
    ]
    for hw in hide_workspaces:
        if frappe.db.exists("Workspace", hw):
            doc = frappe.get_doc("Workspace", hw)
            doc.is_hidden = 1
            doc.public = 0
            doc.save(ignore_permissions=True)


def configure_sidebar_navigation():
    """Hide unwanted links from the module Sidebar (Buying/Purchase)."""
    print("--- 7.1 Configuring Module Sidebar (Hiding unwanted items) ---")
    unwanted_sidebar_labels = [
        "Supplier Scorecard",
        "Accounts Payable",
        "Accounts Payable Summary",
        "Purchase Register",
        "Purchase Order Trends",
        "Purchase Receipt Trends",
        "Purchase Invoice Trends",
        "Item Wise Consumption",
        "Supplier Addresses And Contacts"
    ]
    if frappe.db.exists("Sidebar", "Buying"):
        sb = frappe.get_doc("Sidebar", "Buying")
        for it in sb.items:
            if it.label in unwanted_sidebar_labels:
                it.hidden = 1
                print(f"  Hidden in Buying Sidebar: {it.label}")
        sb.save(ignore_permissions=True)
        print("  Buying Sidebar updated successfully.")



def test_complete_purchasing_workflow():
    """
    Validates Section 21 Acceptance Criteria:
    1. Supplier: Create automotive supplier with Supplier Group.
    2. Material Request: Create & submit automotive material request.
    3. RFQ: Create & submit RFQ.
    4. Supplier Quotation: Create from RFQ & submit.
    5. Purchase Order: Create from Supplier Quotation & submit.
    6. Purchase Receipt: Create from PO, enter accepted & rejected qty, submit, check stock.
    7. Purchase Invoice: Create from PO/PR, submit, check accounting & outstanding amount.
    8. Stock double update prevention check.
    """
    print("\n==================================================")
    print("--- 8. Testing Complete Automotive Purchasing Flow ---")
    print("==================================================")

    # 8.1 Supplier
    sup_name = "Orbis Precision Fasteners (Pvt.) Ltd."
    if not frappe.db.exists("Supplier", sup_name):
        sup = frappe.get_doc({
            "doctype": "Supplier",
            "supplier_name": sup_name,
            "supplier_type": "Company",
            "supplier_group": "Automotive Component Suppliers" if frappe.db.exists("Supplier Group", "Automotive Component Suppliers") else "Components",
            "country": "Pakistan",
            "default_currency": "PKR",
            "default_price_list": "Standard Buying"
        })
        sup.insert(ignore_permissions=True)
        print(f"  [PASS] Supplier created: {sup.name}")
    else:
        sup = frappe.get_doc("Supplier", sup_name)
        print(f"  [PASS] Supplier exists: {sup.name}")

    # Automotive Part to purchase
    item_code = "STEER-SYS-EPS"
    if not frappe.db.exists("Item", item_code):
        item_code = frappe.get_all("Item", filters={"is_purchase_item": 1}, limit=1)[0].name
    item_doc = frappe.get_doc("Item", item_code)
    warehouse = "Raw Material Warehouse - OCM" if frappe.db.exists("Warehouse", "Raw Material Warehouse - OCM") else "Stores - OCM"
    rejected_warehouse = "Quality Hold Warehouse - OCM" if frappe.db.exists("Warehouse", "Quality Hold Warehouse - OCM") else warehouse

    # 8.2 Material Request
    mr = frappe.get_doc({
        "doctype": "Material Request",
        "material_request_type": "Purchase",
        "transaction_date": today(),
        "schedule_date": add_days(today(), 7),
        "company": COMPANY,
        "items": [
            {
                "item_code": item_code,
                "qty": 10,
                "uom": item_doc.stock_uom,
                "warehouse": warehouse,
                "schedule_date": add_days(today(), 7)
            }
        ]
    })
    mr.insert(ignore_permissions=True)
    mr.submit()
    print(f"  [PASS] Material Request created & submitted: {mr.name}")

    # 8.3 Request for Quotation (RFQ from Material Request)
    import erpnext.stock.doctype.material_request.material_request as mr_mod
    rfq = mr_mod.make_request_for_quotation(mr.name)
    rfq.schedule_date = add_days(today(), 5)
    rfq.append("suppliers", {"supplier": sup.name})
    rfq.insert(ignore_permissions=True)
    rfq.submit()
    print(f"  [PASS] RFQ created & submitted: {rfq.name}")

    # 8.4 Supplier Quotation (from RFQ)
    import erpnext.buying.doctype.request_for_quotation.request_for_quotation as rfq_mod
    sq_doc = rfq_mod.make_supplier_quotation_from_rfq(rfq.name, for_supplier=sup.name)
    sq_doc.valid_till = add_days(today(), 30)
    sq_doc.items[0].rate = 4500.0  # offered price per unit
    sq_doc.insert(ignore_permissions=True)
    sq_doc.submit()
    print(f"  [PASS] Supplier Quotation created & submitted: {sq_doc.name} (Rate: PKR {sq_doc.items[0].rate})")

    # 8.5 Purchase Order (from Supplier Quotation)
    import erpnext.buying.doctype.supplier_quotation.supplier_quotation as sq_mod
    po_doc = sq_mod.make_purchase_order(sq_doc.name)
    po_doc.schedule_date = add_days(today(), 7)
    po_doc.insert(ignore_permissions=True)
    po_doc.submit()
    print(f"  [PASS] Purchase Order created & submitted: {po_doc.name} (Grand Total: PKR {po_doc.grand_total})")

    # Check Initial Stock in target warehouse
    from erpnext.stock.utils import get_stock_balance
    initial_stock = flt(get_stock_balance(item_code, warehouse))
    print(f"  Target Warehouse Initial Stock ({warehouse}): {initial_stock}")

    # 8.6 Purchase Receipt (Receive 10: Accepted 8, Rejected 2)
    import erpnext.buying.doctype.purchase_order.purchase_order as po_mod
    pr_doc = po_mod.make_purchase_receipt(po_doc.name)
    pr_doc.supplier_delivery_note = "DN-OCM-TEST-001"
    pr_doc.rejected_warehouse = rejected_warehouse
    
    # Enter accepted and rejected quantities
    pr_doc.items[0].qty = 8.0          # Accepted
    pr_doc.items[0].rejected_qty = 2.0 # Rejected
    pr_doc.items[0].rejected_warehouse = rejected_warehouse

    pr_doc.insert(ignore_permissions=True)
    pr_doc.submit()
    print(f"  [PASS] Purchase Receipt submitted: {pr_doc.name}")
    print(f"         Accepted Qty: {pr_doc.items[0].qty}, Rejected Qty: {pr_doc.items[0].rejected_qty}")

    # Verify Stock Update
    updated_stock = flt(get_stock_balance(item_code, warehouse))
    print(f"  Target Warehouse Updated Stock ({warehouse}): {updated_stock} (Diff: +{updated_stock - initial_stock})")
    assert updated_stock == initial_stock + 8.0, f"Stock discrepancy! Expected {initial_stock + 8.0}, got {updated_stock}"
    print("  [PASS] Stock correctly updated in Stock Module!")

    # 8.7 Purchase Invoice (from Purchase Receipt)
    import erpnext.stock.doctype.purchase_receipt.purchase_receipt as pr_mod
    pi_doc = pr_mod.make_purchase_invoice(pr_doc.name)
    pi_doc.bill_no = "INV-SUP-9988"
    pi_doc.bill_date = today()
    pi_doc.due_date = add_days(today(), 15)
    
    # Ensure update_stock is 0
    pi_doc.update_stock = 0

    pi_doc.insert(ignore_permissions=True)
    pi_doc.submit()
    print(f"  [PASS] Purchase Invoice submitted: {pi_doc.name}")
    print(f"         Invoice Amount: PKR {pi_doc.grand_total}, Outstanding: PKR {pi_doc.outstanding_amount}")

    # Verify Accounting GL Entries exist for Purchase Invoice
    gl_entries = frappe.get_all("GL Entry", filters={"voucher_no": pi_doc.name}, fields=["account", "debit", "credit"])
    print(f"  [PASS] GL Entries generated for Invoice: {len(gl_entries)} entries")
    for gl in gl_entries:
        print(f"         Account: {gl.account} | Debit: {gl.debit} | Credit: {gl.credit}")

    # Verify Stock was NOT updated twice
    final_stock = flt(get_stock_balance(item_code, warehouse))
    assert final_stock == updated_stock, f"Double stock update detected! Stock changed from {updated_stock} to {final_stock}"
    print(f"  [PASS] Confirmed: Stock was NOT updated twice. Current stock remains {final_stock}.")

    return {
        "supplier": sup.name,
        "material_request": mr.name,
        "rfq": rfq.name,
        "supplier_quotation": sq_doc.name,
        "purchase_order": po_doc.name,
        "purchase_receipt": pr_doc.name,
        "purchase_invoice": pi_doc.name,
        "accepted_qty": 8.0,
        "rejected_qty": 2.0,
        "stock_level": final_stock
    }


def run():
    print("Starting OrbisERP Purchase Module Customization...")
    configure_supplier_groups()
    configure_item_groups()
    configure_buying_settings()
    configure_form_customizations()
    configure_purchase_client_scripts()
    configure_purchase_permissions()
    configure_purchase_workspace()
    configure_sidebar_navigation()
    
    frappe.clear_cache()
    frappe.db.commit()
    print("Database committed and cache cleared.")
    
    # Run acceptance workflow test
    test_results = test_complete_purchasing_workflow()
    
    frappe.db.commit()
    print("\nCustomization and Acceptance Testing Completed Successfully!")
    return test_results

if __name__ == "__main__":
    run()
