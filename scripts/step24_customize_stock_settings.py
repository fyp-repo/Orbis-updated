"""
Step 24: Customize Stock Settings for OrbisERP (Automotive Manufacturing)
========================================================================
Simplifies and cleans up the Stock Settings page according to requirements:

1. Tab Visibility:
   - KEEP: Defaults, Stock Validations, Serial & Batch Item, Quality, Stock Planning, Document Naming
   - HIDE: Stock Reservation, Stock Closing

2. Defaults Tab:
   - Show: item_naming_by, item_group, valuation_method, stock_uom,
           auto_insert_price_list_rate_if_missing, update_existing_price_list_rate,
           update_price_list_based_on, allow_to_edit_stock_uom_qty_for_sales,
           allow_to_edit_stock_uom_qty_for_purchase, allow_to_edit_stock_uom_qty_for_stock_entry,
           allow_uom_with_conversion_rate_defined_in_item

3. Stock Validations Tab:
   - Show: allow_negative_stock, over_delivery_receipt_allowance, mr_qty_allowance,
           over_picking_allowance, show_barcode_field, clean_description_html,
           validate_material_transfer_warehouses
   - Hide: allow_internal_transfer_at_arms_length_price

4. Serial & Batch Item Tab:
   - Show: enable_serial_and_batch_no_for_item, pick_serial_and_batch_based_on,
           use_serial_batch_fields, use_naming_series, naming_series_prefix,
           auto_create_serial_and_batch_bundle_for_outward,
           set_serial_and_batch_bundle_naming_based_on_naming_series
   - Hide: allow_existing_serial_no, disable_serial_no_and_batch_selector,
           allow_negative_stock_for_batch, do_not_use_batchwise_valuation,
           do_not_update_serial_batch_on_creation_of_auto_bundle,
           auto_map_raw_materials_to_finished_goods

5. Quality Tab:
   - Show: allow_to_make_quality_inspection_after_purchase_or_delivery,
           action_if_quality_inspection_is_rejected,
           action_if_quality_inspection_is_not_submitted

6. Stock Planning Tab:
   - Show: auto_indent, reorder_email_notify

7. Document Naming Tab:
   - Show: transaction_naming_html (Item, Stock Entry, Purchase Receipt, Delivery Note,
           Material Request, Pick List, Stock Reconciliation, Serial and Batch Bundle)

Implementation uses standard Property Setters and a complementary Client Script.
No backend logic, records, DocTypes, or core files are modified or deleted.
"""

import os
import frappe

DOC_TYPE = "Stock Settings"

# Fields to hide via Property Setter
FIELDS_TO_HIDE = [
    # Tabs to hide
    "stock_reservation_tab",
    "stock_closing_tab",
    # Sections inside hidden tabs
    "serial_and_batch_reservation_section",
    "control_historical_stock_transactions_section",
    "section_break_kcvr",
    # Stock Validations: hide internal transfer at user-defined rate
    "allow_internal_transfer_at_arms_length_price",
    # Serial & Batch Item: hide these specific options
    "allow_existing_serial_no",
    "disable_serial_no_and_batch_selector",
    "allow_negative_stock_for_batch",
    "do_not_use_batchwise_valuation",
    "do_not_update_serial_batch_on_creation_of_auto_bundle",
    "auto_map_raw_materials_to_finished_goods"
]

# Fields that MUST remain visible (hidden = 0)
FIELDS_TO_SHOW = [
    # Tabs
    "defaults_tab",
    "stock_validations_tab",
    "serial_and_batch_item_settings_tab",
    "quality_tab",
    "stock_planning_tab",
    "document_naming_tab",
    # Defaults
    "item_naming_by",
    "item_group",
    "valuation_method",
    "stock_uom",
    "auto_insert_price_list_rate_if_missing",
    "update_existing_price_list_rate",
    "update_price_list_based_on",
    "allow_to_edit_stock_uom_qty_for_sales",
    "allow_to_edit_stock_uom_qty_for_purchase",
    "allow_to_edit_stock_uom_qty_for_stock_entry",
    "allow_uom_with_conversion_rate_defined_in_item",
    # Stock Validations
    "allow_negative_stock",
    "over_delivery_receipt_allowance",
    "mr_qty_allowance",
    "over_picking_allowance",
    "show_barcode_field",
    "clean_description_html",
    "validate_material_transfer_warehouses",
    # Serial & Batch Item
    "enable_serial_and_batch_no_for_item",
    "pick_serial_and_batch_based_on",
    "use_serial_batch_fields",
    "use_naming_series",
    "auto_create_serial_and_batch_bundle_for_outward",
    "set_serial_and_batch_bundle_naming_based_on_naming_series",
    # Quality
    "allow_to_make_quality_inspection_after_purchase_or_delivery",
    "action_if_quality_inspection_is_rejected",
    "action_if_quality_inspection_is_not_submitted",
    # Stock Planning
    "auto_indent",
    "reorder_email_notify",
    # Document Naming
    "transaction_naming_html"
]

def set_property_setter(doc_type, field_name, property_name, value, property_type="Check"):
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


def configure_property_setters():
    print("--- 1. Setting Property Setters for Stock Settings ---")
    for f in FIELDS_TO_HIDE:
        set_property_setter(DOC_TYPE, f, "hidden", 1, "Check")
        print(f"  [HIDE] {f}")

    for f in FIELDS_TO_SHOW:
        set_property_setter(DOC_TYPE, f, "hidden", 0, "Check")
        print(f"  [SHOW] {f}")


CLIENT_SCRIPT_NAME = "Orbis Stock Settings Customization"

CLIENT_SCRIPT_CONTENT = """// OrbisERP: Clean and professional Stock Settings UI
frappe.ui.form.on("Stock Settings", {
    refresh(frm) {
        // Hide specified tabs
        frm.set_df_property("stock_reservation_tab", "hidden", 1);
        frm.set_df_property("stock_closing_tab", "hidden", 1);

        // Hide specific sections inside hidden tabs
        frm.set_df_property("serial_and_batch_reservation_section", "hidden", 1);
        frm.set_df_property("control_historical_stock_transactions_section", "hidden", 1);
        frm.set_df_property("section_break_kcvr", "hidden", 1);

        // Stock Validations tab
        frm.set_df_property("allow_internal_transfer_at_arms_length_price", "hidden", 1);

        // Serial & Batch Item tab
        frm.set_df_property("allow_existing_serial_no", "hidden", 1);
        frm.set_df_property("disable_serial_no_and_batch_selector", "hidden", 1);
        frm.set_df_property("allow_negative_stock_for_batch", "hidden", 1);
        frm.set_df_property("do_not_use_batchwise_valuation", "hidden", 1);
        frm.set_df_property("do_not_update_serial_batch_on_creation_of_auto_bundle", "hidden", 1);
        frm.set_df_property("auto_map_raw_materials_to_finished_goods", "hidden", 1);

        // Ensure kept tabs are visible
        frm.set_df_property("defaults_tab", "hidden", 0);
        frm.set_df_property("stock_validations_tab", "hidden", 0);
        frm.set_df_property("serial_and_batch_item_settings_tab", "hidden", 0);
        frm.set_df_property("quality_tab", "hidden", 0);
        frm.set_df_property("stock_planning_tab", "hidden", 0);
        frm.set_df_property("document_naming_tab", "hidden", 0);
    }
});
"""

def configure_client_script():
    print("--- 2. Setting Client Script for Stock Settings ---")
    if frappe.db.exists("Client Script", CLIENT_SCRIPT_NAME):
        doc = frappe.get_doc("Client Script", CLIENT_SCRIPT_NAME)
        doc.script = CLIENT_SCRIPT_CONTENT
        doc.enabled = 1
        doc.save(ignore_permissions=True)
        print(f"  Updated Client Script: {CLIENT_SCRIPT_NAME}")
    else:
        doc = frappe.get_doc({
            "doctype": "Client Script",
            "name": CLIENT_SCRIPT_NAME,
            "dt": DOC_TYPE,
            "view": "Form",
            "script": CLIENT_SCRIPT_CONTENT,
            "enabled": 1,
        })
        doc.insert(ignore_permissions=True)
        print(f"  Created Client Script: {CLIENT_SCRIPT_NAME}")


def run():
    os.makedirs("/home/frappe/logs", exist_ok=True)
    os.chdir("/home/frappe/frappe-bench/sites")
    if not frappe.db:
        frappe.init(site="frontend", sites_path="/home/frappe/frappe-bench/sites")
        frappe.connect()

    configure_property_setters()
    configure_client_script()

    frappe.db.commit()

    # Clear caches
    try:
        frappe.clear_cache(doctype=DOC_TYPE)
        frappe.cache().delete_key("bootinfo")
    except Exception as e:
        print(f"Cache clear note: {e}")

    print("\n[Step 24 Complete] Stock Settings customized successfully.")
    return "[Step 24 Complete]"

if __name__ == "__main__":
    run()
    frappe.destroy()
