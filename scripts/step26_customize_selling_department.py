"""
Step 16: Customize Selling Department for OrbisERP
==================================================
Project Context:
This ERPNext site is customized for a CAR (VEHICLE) SALES business.
Sales reps only need to sell vehicles: select customer, select vehicle/item,
price, payment, and delivery.

This script customizes the Selling Department by hiding non-essential fields
from all relevant parent DocTypes and child tables using Frappe Property Setters:
  - Parent DocTypes: Quotation, Sales Order, Delivery Note, Sales Invoice
  - Child Tables: Quotation Item, Sales Order Item, Delivery Note Item, Sales Invoice Item
  - Auxiliary: Customer, Selling Settings

Field Groups:
  A) Manufacturing / Subcontracting / Production / Barcode Scanning:
     Always hidden because car sales reps sell finished vehicles and do not
     perform subcontracting, shop floor scheduling, or barcode scanning.
  B) International Trade:
     Always hidden because business operations are strictly domestic (Pakistan).
  C) Shipping Rule:
     Controlled by `HIDE_SHIPPING_RULE`. Vehicle transport charges are billed
     directly or included in standard vehicle pricing.
  D) Taxes and Tax Calculation:
     Controlled by `HIDE_TAX`. Car sales reps do not handle complex tax category
     selection, tax withholding, or manual tax tables on customer sales forms.

Safety Rules:
  - Non-destructive: Uses Property Setters (hidden = 1, print_hide = 1).
  - Verifies field existence via meta.has_field() before creating Property Setters.
  - Verifies mandatory status: never hides mandatory (reqd = 1) fields.
  - Idempotent: safe to run multiple times without creating duplicate records.
  - Reversible: provides full rollback() function to restore all standard fields.
"""

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


# ==============================================================================
# CONFIGURATION FLAGS
# ==============================================================================
# Set to False if vehicle transport charges are billed through shipping rules:
HIDE_SHIPPING_RULE = True

# Set to False if tax templates and tax tables need to be restored on sales forms:
HIDE_TAX = True


# ==============================================================================
# FIELD DEFINITIONS BY CATEGORY AND DOCTYPE
# ==============================================================================

# Group A: Always hide (Manufacturing / Subcontracting / Production / Barcode)
ALWAYS_HIDE_FIELDS = {
    "Quotation": [
        ("scan_barcode", "Scan Barcode"),
        ("last_scanned_warehouse", "Last Scanned Warehouse"),
    ],
    "Quotation Item": [],
    "Sales Order": [
        ("is_subcontracted", "Is Subcontracted"),
        ("scan_barcode", "Scan Barcode"),
        ("last_scanned_warehouse", "Last Scanned Warehouse"),
    ],
    "Sales Order Item": [
        ("subcontracted_qty", "Subcontracted Quantity"),
        ("manufacturing_section_section", "Manufacturing Section"),
        ("bom_no", "BOM No"),
        ("production_plan_qty", "Production Plan Qty"),
        ("work_order_qty", "Work Order Qty"),
    ],
    "Delivery Note": [
        ("scan_barcode", "Scan Barcode"),
        ("last_scanned_warehouse", "Last Scanned Warehouse"),
    ],
    "Delivery Note Item": [
        ("barcode", "Barcode"),
    ],
    "Sales Invoice": [
        ("has_subcontracted", "Has Subcontracted"),
        ("scan_barcode", "Scan Barcode"),
        ("last_scanned_warehouse", "Last Scanned Warehouse"),
    ],
    "Sales Invoice Item": [
        ("barcode", "Barcode"),
    ],
    "Selling Settings": [
        ("subcontracting_inward_tab", "Subcontracting Inward Tab"),
    ],
}

# Group B: International trade (domestic car sales only)
INTERNATIONAL_TRADE_FIELDS = {
    "Quotation": [
        ("incoterm", "Incoterm"),
        ("named_place", "Named Place"),
    ],
    "Sales Order": [
        ("incoterm", "Incoterm"),
        ("named_place", "Named Place"),
    ],
    "Delivery Note": [
        ("incoterm", "Incoterm"),
        ("named_place", "Named Place"),
    ],
    "Sales Invoice": [
        ("incoterm", "Incoterm"),
        ("named_place", "Named Place"),
    ],
}

# Group C: Shipping rule fields (active when HIDE_SHIPPING_RULE = True)
SHIPPING_RULE_FIELDS = {
    "Quotation": [
        ("shipping_rule", "Shipping Rule"),
    ],
    "Sales Order": [
        ("shipping_rule", "Shipping Rule"),
    ],
    "Delivery Note": [
        ("shipping_rule", "Shipping Rule"),
    ],
    "Sales Invoice": [
        ("shipping_rule", "Shipping Rule"),
    ],
}

# Group D: Tax fields, tax tables, tax section breaks (active when HIDE_TAX = True)
TAX_FIELDS = {
    "Quotation": [
        ("tax_category", "Tax Category"),
        ("taxes_and_charges", "Sales Taxes and Charges Template"),
        ("taxes", "Sales Taxes and Charges Table"),
        ("base_total_taxes_and_charges", "Total Taxes (Company Currency)"),
        ("total_taxes_and_charges", "Total Taxes and Charges"),
        ("taxes_section", "Taxes and Charges Section Break"),
        ("sec_tax_breakup", "Tax Breakup Section Break"),
        ("other_charges_calculation", "Taxes Calculation Details"),
        ("section_break_36", "Taxes Table Section Break"),
        ("section_break_39", "Taxes Total Section Break"),
    ],
    "Quotation Item": [
        ("item_tax_template", "Item Tax Template"),
        ("item_tax_rate", "Item Tax Rate"),
    ],
    "Sales Order": [
        ("tax_category", "Tax Category"),
        ("taxes_and_charges", "Sales Taxes and Charges Template"),
        ("taxes", "Sales Taxes and Charges Table"),
        ("base_total_taxes_and_charges", "Total Taxes (Company Currency)"),
        ("total_taxes_and_charges", "Total Taxes and Charges"),
        ("taxes_section", "Taxes Section Break"),
        ("sec_tax_breakup", "Tax Breakup Section Break"),
        ("other_charges_calculation", "Taxes Calculation Details"),
        ("section_break_40", "Taxes Table Section Break"),
        ("section_break_43", "Taxes Total Section Break"),
        ("tax_id", "Tax ID"),
    ],
    "Sales Order Item": [
        ("item_tax_template", "Item Tax Template"),
        ("item_tax_rate", "Item Tax Rate"),
    ],
    "Delivery Note": [
        ("tax_category", "Tax Category"),
        ("taxes_and_charges", "Sales Taxes and Charges Template"),
        ("taxes", "Sales Taxes and Charges Table"),
        ("base_total_taxes_and_charges", "Total Taxes (Company Currency)"),
        ("total_taxes_and_charges", "Total Taxes and Charges"),
        ("taxes_section", "Taxes Section Break"),
        ("sec_tax_breakup", "Tax Breakup Section Break"),
        ("other_charges_calculation", "Taxes Calculation Details"),
        ("section_break_41", "Taxes Table Section Break"),
        ("section_break_44", "Taxes Total Section Break"),
        ("tax_id", "Tax ID"),
    ],
    "Delivery Note Item": [
        ("item_tax_template", "Item Tax Template"),
        ("item_tax_rate", "Item Tax Rate"),
    ],
    "Sales Invoice": [
        ("tax_category", "Tax Category"),
        ("taxes_and_charges", "Sales Taxes and Charges Template"),
        ("taxes", "Sales Taxes and Charges Table"),
        ("base_total_taxes_and_charges", "Total Taxes (Company Currency)"),
        ("total_taxes_and_charges", "Total Taxes and Charges"),
        ("taxes_section", "Taxes Section Break"),
        ("sec_tax_breakup", "Tax Breakup Section Break"),
        ("other_charges_calculation", "Taxes Calculation Details"),
        ("section_break_40", "Taxes Table Section Break"),
        ("section_break_43", "Taxes Total Section Break"),
        ("tax_id", "Tax ID"),
        ("company_tax_id", "Company Tax ID"),
        ("section_tax_withholding_entry", "Tax Withholding Entry Section"),
        ("tax_withholding_group", "Tax Withholding Group"),
        ("ignore_tax_withholding_threshold", "Ignore Tax Withholding Threshold"),
        ("override_tax_withholding_entries", "Edit Tax Withholding Entries"),
        ("tax_withholding_entries", "Tax Withholding Entries Table"),
        ("apply_tds", "Consider for Tax Withholding"),
    ],
    "Sales Invoice Item": [
        ("item_tax_template", "Item Tax Template"),
        ("item_tax_rate", "Item Tax Rate"),
        ("tax_withholding_category", "Tax Withholding Category"),
        ("apply_tds", "Consider for Tax Withholding"),
    ],
    "Customer": [
        ("tax_category", "Tax Category"),
    ],
}


def build_active_fields_map():
    """
    Combines all active field definitions based on configuration flags.
    Returns dict: doctype -> list of (fieldname, label, group_name)
    """
    active_map = {}

    def add_group(group_dict, group_name):
        for dt, fields in group_dict.items():
            active_map.setdefault(dt, [])
            for fn, label in fields:
                active_map[dt].append((fn, label, group_name))

    # Always hide manufacturing/barcode & international trade
    add_group(ALWAYS_HIDE_FIELDS, "Manufacturing & Barcode")
    add_group(INTERNATIONAL_TRADE_FIELDS, "International Trade")

    # Conditionally hide shipping rule
    if HIDE_SHIPPING_RULE:
        add_group(SHIPPING_RULE_FIELDS, "Shipping Rule")

    # Conditionally hide taxes
    if HIDE_TAX:
        add_group(TAX_FIELDS, "Taxes & Tax Calculation")

    return active_map


def apply_property_setters():
    """
    Applies Property Setters (hidden=1, print_hide=1) for all configured fields.
    Performs safety checks for field existence and mandatory status.
    """
    print("=" * 80)
    print("  STEP 16: APPLYING SELLING DEPARTMENT CUSTOMIZATIONS (PROPERTY SETTERS)")
    print("=" * 80)
    print(f"  Configuration Flags:")
    print(f"    - HIDE_SHIPPING_RULE : {HIDE_SHIPPING_RULE}")
    print(f"    - HIDE_TAX           : {HIDE_TAX}")
    print("-" * 80)

    active_map = build_active_fields_map()

    summary = {
        "hidden": 0,
        "already_hidden": 0,
        "skipped_not_found": 0,
        "skipped_mandatory": 0,
    }
    modified_doctypes = set()

    for dt, field_tuples in active_map.items():
        if not frappe.db.exists("DocType", dt):
            print(f"  [SKIP] DocType '{dt}' does not exist on this site.")
            summary["skipped_not_found"] += len(field_tuples)
            continue

        meta = frappe.get_meta(dt)

        for fn, lbl, group_name in field_tuples:
            # 1. Existence check via meta.has_field()
            if not meta.has_field(fn):
                print(f"  [SKIP - NOT FOUND] {dt}.{fn} does not exist in meta.")
                summary["skipped_not_found"] += 1
                continue

            field = meta.get_field(fn)

            # 2. Mandatory safety check: Never hide reqd = 1 fields
            if field.reqd:
                print(f"  [WARN - MANDATORY] {dt}.{fn} ({lbl}) is mandatory (reqd=1). Skipping.")
                summary["skipped_mandatory"] += 1
                continue

            # 3. Check if already hidden in current metadata
            already_hidden = bool(field.hidden)

            try:
                # Apply hidden = 1
                make_property_setter(
                    dt,
                    fn,
                    "hidden",
                    1,
                    "Check",
                    for_doctype=False,
                    validate_fields_for_doctype=False,
                    is_system_generated=True,
                )

                # Apply print_hide = 1 (except Tab Break)
                if field.fieldtype != "Tab Break":
                    make_property_setter(
                        dt,
                        fn,
                        "print_hide",
                        1,
                        "Check",
                        for_doctype=False,
                        validate_fields_for_doctype=False,
                        is_system_generated=True,
                    )

                if already_hidden:
                    print(f"  [ALREADY HIDDEN] {dt}.{fn} ({lbl}) [{group_name}]")
                    summary["already_hidden"] += 1
                else:
                    print(f"  [OK - HIDDEN]    {dt}.{fn} ({lbl}) [{group_name}]")
                    summary["hidden"] += 1

                modified_doctypes.add(dt)

            except Exception as e:
                print(f"  [ERROR] Failed to set Property Setter on {dt}.{fn}: {e}")

    frappe.db.commit()
    print("-" * 80)
    print("  SUMMARY:")
    print(f"    - Newly Hidden            : {summary['hidden']}")
    print(f"    - Already Hidden          : {summary['already_hidden']}")
    print(f"    - Skipped (Field Not Found): {summary['skipped_not_found']}")
    print(f"    - Skipped (Mandatory Reqd) : {summary['skipped_mandatory']}")
    print(f"    - Modified DocTypes       : {len(modified_doctypes)}")
    print("=" * 80)

    return modified_doctypes, summary


def verify_customizations():
    """
    Verifies that all active target fields evaluate to hidden=1 in DocType metadata.
    """
    print("\n" + "=" * 80)
    print("  VERIFYING SELLING DEPARTMENT FIELD VISIBILITY")
    print("=" * 80)

    active_map = build_active_fields_map()
    all_ok = True
    verified_count = 0

    for dt, field_tuples in active_map.items():
        if not frappe.db.exists("DocType", dt):
            continue

        meta = frappe.get_meta(dt)
        for fn, lbl, group_name in field_tuples:
            if not meta.has_field(fn):
                continue

            field = meta.get_field(fn)
            if field.reqd:
                continue

            is_hidden = bool(field.hidden)
            status = "[HIDDEN]" if is_hidden else "[VISIBLE - FAIL]"
            print(f"  {status:<16} {dt}.{fn} ({lbl}) -> hidden={field.hidden}")
            verified_count += 1
            if not is_hidden:
                all_ok = False

    print(f"\n  Verified {verified_count} field visibility statuses.")
    return all_ok


def rollback():
    """
    Rollback function: removes every Property Setter created or managed by this script.
    Restores default ERPNext field visibility across all Selling forms.
    """
    print("=" * 80)
    print("  STEP 16: ROLLING BACK SELLING DEPARTMENT CUSTOMIZATIONS")
    print("=" * 80)

    # Gather all fields from all groups regardless of current flag settings
    all_groups = [
        ALWAYS_HIDE_FIELDS,
        INTERNATIONAL_TRADE_FIELDS,
        SHIPPING_RULE_FIELDS,
        TAX_FIELDS,
    ]

    all_targets = {}
    for g in all_groups:
        for dt, fields in g.items():
            all_targets.setdefault(dt, set())
            for fn, _ in fields:
                all_targets[dt].add(fn)

    removed_count = 0
    affected_doctypes = set()

    for dt, field_names in all_targets.items():
        for fn in field_names:
            # Query Property Setters matching doc_type and field_name for hidden and print_hide
            ps_records = frappe.get_all(
                "Property Setter",
                filters={
                    "doc_type": dt,
                    "field_name": fn,
                    "property": ["in", ["hidden", "print_hide"]],
                },
                fields=["name", "property", "value"],
            )

            for ps in ps_records:
                try:
                    frappe.delete_doc("Property Setter", ps.name, ignore_permissions=True)
                    removed_count += 1
                    affected_doctypes.add(dt)
                    print(f"  [REMOVED] Property Setter: {ps.name} ({ps.property}={ps.value})")
                except Exception as e:
                    print(f"  [ERROR] Failed to remove Property Setter {ps.name}: {e}")

    frappe.db.commit()
    clear_caches()

    print("\n" + "=" * 80)
    print(f"  ROLLBACK COMPLETE: Removed {removed_count} Property Setters across {len(affected_doctypes)} DocTypes.")
    print("  All standard Selling forms restored to original ERPNext visibility.")
    print("=" * 80)
    return f"Rollback complete: removed {removed_count} Property Setters."


def clear_caches():
    """Flushes site and metadata caches."""
    print("\n" + "=" * 80)
    print("  CLEARING CACHES & REBUILDING METADATA")
    print("=" * 80)
    frappe.clear_cache()
    print("  Cache cleared successfully.")


def main():
    """Main execution entry point."""
    modified, summary = apply_property_setters()
    clear_caches()
    success = verify_customizations()
    print("\n" + "=" * 80)
    if success:
        print("  STEP 16 COMPLETE: SELLING DEPARTMENT CUSTOMIZATIONS APPLIED & VERIFIED")
    else:
        print("  STEP 16 WARNING: SOME FIELDS MAY NOT BE HIDDEN PROPERLY")
    print("=" * 80)
    return f"Modified {len(modified)} DocTypes successfully. Hidden: {summary['hidden']}, Already Hidden: {summary['already_hidden']}."


def run():
    """Standard bench execute / run_script.ps1 entry point."""
    return main()


if __name__ == "__main__":
    frappe.init(site="frontend", sites_path="/home/frappe/frappe-bench/sites")
    frappe.connect()
    main()
    frappe.destroy()
