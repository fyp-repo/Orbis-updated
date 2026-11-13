"""
Step 19: Customize Item Form for Automotive Manufacturing
==========================================================
Customizes the Item form to keep it simple, clean, and focused on
finished-car inventory, automotive manufacturing, and sales.

Fields/Tabs to SHOW:
- Details tab:
    Item Code, Item Name, Item Group, Default Unit of Measure,
    Maintain Stock, Allow Sales, Description
- UOM tab:
    UOM conversion details table (uoms)
- Inventory tab:
    Valuation Method, Valuation Rate, Default Material Request Type,
    End of Life, Has Serial No
- Manufacturing tab:
    Include Item In Manufacturing, Default BOM, Is Subcontracted Item
- Quality tab:
    Inspection Required before Delivery
- Connections tab:
    Dashboard links (preserved)

Fields/Tabs to HIDE:
- Details tab:
    disabled, is_fixed_asset, auto_create_assets, is_grouped_asset,
    asset_category, asset_naming_series, allow_alternative_item,
    has_variants, is_purchase_item, is_customer_provided_item,
    over_delivery_receipt_allowance, over_billing_allowance, brand
- Inventory tab:
    weight_per_unit, weight_uom, allow_negative_stock,
    reorder_section, reorder_levels, has_batch_no, create_new_batch,
    batch_number_series, has_expiry_date, shelf_life_in_days,
    retain_sample, sample_quantity
- Purchasing tab:
    purchasing_tab (entire tab hidden)
    purchase_uom, min_order_qty, safety_stock, lead_time_days,
    last_purchase_rate, supplier_items, supplier_details
- Manufacturing tab:
    production_capacity
- Quality tab:
    inspection_required_before_purchase, quality_inspection_template

All changes use standard Frappe Property Setters and a Client Script.
No DocTypes, database columns, or core files are modified or deleted.
"""

import sys
import frappe

def set_field_property(dt, fieldname, prop, val):
    """Create or update a Property Setter on a DocField."""
    existing = frappe.db.get_value(
        "Property Setter",
        {"doc_type": dt, "field_name": fieldname, "property": prop},
        "name"
    )
    if existing:
        doc = frappe.get_doc("Property Setter", existing)
        if str(doc.value) != str(val):
            doc.value = str(val)
            doc.save(ignore_permissions=True)
            print(f"  [UPDATED] {dt}.{fieldname}: {prop} = {val}")
    else:
        doc = frappe.get_doc({
            "doctype": "Property Setter",
            "doc_type": dt,
            "field_name": fieldname,
            "doctype_or_field": "DocField",
            "property": prop,
            "property_type": "Check" if prop in ("hidden", "reqd", "read_only") else "Data",
            "value": str(val)
        })
        doc.insert(ignore_permissions=True)
        print(f"  [CREATED] {dt}.{fieldname}: {prop} = {val}")

def setup_item_property_setters():
    print("\n--- 1. Applying Property Setters to Item Form ---")

    # Fields to explicitly hide (hidden=1)
    fields_to_hide = [
        # Details tab fields
        "disabled",
        "is_fixed_asset",
        "auto_create_assets",
        "is_grouped_asset",
        "asset_category",
        "asset_naming_series",
        "allow_alternative_item",
        "has_variants",
        "is_purchase_item",
        "is_customer_provided_item",
        "over_delivery_receipt_allowance",
        "over_billing_allowance",
        "brand",

        # Inventory tab fields
        "weight_per_unit",
        "weight_uom",
        "allow_negative_stock",
        "reorder_section",
        "reorder_levels",
        "has_batch_no",
        "create_new_batch",
        "batch_number_series",
        "has_expiry_date",
        "shelf_life_in_days",
        "retain_sample",
        "sample_quantity",

        # Purchasing tab
        "purchasing_tab",
        "purchase_uom",
        "min_order_qty",
        "safety_stock",
        "lead_time_days",
        "last_purchase_rate",
        "supplier_details",
        "supplier_items",
        "foreign_trade_details",
        "country_of_origin",
        "customs_tariff_number",

        # Manufacturing tab
        "production_capacity",

        # Quality tab
        "inspection_required_before_purchase",
        "quality_inspection_template",
    ]

    for f in fields_to_hide:
        set_field_property("Item", f, "hidden", "1")

    # Fields to explicitly ensure VISIBLE (hidden=0)
    fields_to_show = [
        # Details
        "item_name",
        "item_group",
        "stock_uom",
        "is_stock_item",
        "is_sales_item",
        "description",

        # Tabs
        "details",
        "uom_tab",
        "inventory_section",
        "manufacturing",
        "quality_tab",
        "dashboard_tab",

        # UOM
        "uoms",

        # Inventory
        "valuation_method",
        "valuation_rate",
        "default_material_request_type",
        "end_of_life",
        "has_serial_no",

        # Manufacturing
        "include_item_in_manufacturing",
        "default_bom",
        "is_sub_contracted_item",

        # Quality
        "inspection_required_before_delivery",
    ]

    for f in fields_to_show:
        set_field_property("Item", f, "hidden", "0")

def setup_item_client_script():
    print("\n--- 2. Setting up Item Form Client Script ---")
    script_name = "Orbis Item Form Simplification"

    # Client script ensures fields and tabs stay cleanly hidden even if dynamic logic runs
    js_code = """frappe.ui.form.on('Item', {
    refresh: function(frm) {
        // Hide non-essential fields in Details
        var details_hide = [
            'disabled', 'is_fixed_asset', 'auto_create_assets', 'is_grouped_asset',
            'asset_category', 'asset_naming_series', 'allow_alternative_item',
            'has_variants', 'is_purchase_item', 'is_customer_provided_item',
            'over_delivery_receipt_allowance', 'over_billing_allowance', 'brand'
        ];
        details_hide.forEach(function(f) {
            frm.toggle_display(f, false);
        });

        // Hide non-essential fields in Inventory
        var inv_hide = [
            'weight_per_unit', 'weight_uom', 'allow_negative_stock',
            'reorder_levels', 'has_batch_no', 'create_new_batch',
            'batch_number_series', 'has_expiry_date', 'shelf_life_in_days',
            'retain_sample', 'sample_quantity'
        ];
        inv_hide.forEach(function(f) {
            frm.toggle_display(f, false);
        });

        // Hide unused tabs
        var tabs_to_hide = ['purchasing_tab', 'variants_section', 'item_tax_section_break', 'pricing_tab', 'accounting'];
        tabs_to_hide.forEach(function(tab) {
            frm.toggle_display(tab, false);
        });

        // Hide unused Manufacturing fields
        frm.toggle_display('production_capacity', false);

        // Hide unused Quality fields
        frm.toggle_display('inspection_required_before_purchase', false);
        frm.toggle_display('quality_inspection_template', false);
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
            "dt": "Item",
            "view": "Form",
            "enabled": 1,
            "script": js_code
        })
        doc.insert(ignore_permissions=True)
        print(f"  [CREATED] Client Script: {script_name}")

def run():
    print("=" * 60)
    print("OrbisERP Step 19: Customize Item Form")
    print("=" * 60)

    setup_item_property_setters()
    setup_item_client_script()

    frappe.clear_cache(doctype="Item")
    frappe.clear_cache()
    frappe.db.commit()

    print("\n" + "=" * 60)
    print("Item Form Customization Applied Successfully!")
    print("=" * 60)
    return "Done"

if __name__ == "__main__":
    frappe.init(site="frontend", sites_path="/home/frappe/frappe-bench/sites")
    frappe.connect()
    run()
    frappe.destroy()

