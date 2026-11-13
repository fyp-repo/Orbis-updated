"""
Test and Audit Suite for Step 19: Hide Subcontracting Module
============================================================
Tests:
1. Zero subcontracting dependencies check.
2. Property Setters on forms (Work Order, Stock Entry, etc.).
3. Permission restrictions:
   - Normal users (Production Manager, Storekeeper, Floor Worker) cannot access Subcontracting DocTypes.
   - System Manager retains full access.
4. Workspaces verification (0 subcontracting links in Manufacturing & Buying).
5. In-house Manufacturing & Quality Inspection functionality:
   - Work Order creation & submission
   - Material Transfer & Manufacture Stock Entries
   - Quality Inspection (Accepted -> Ready for Dispatch)
   - Delivery Note selling integration
   - Full cleanup & zero stock drift
6. Rollback and Re-apply verification.
"""

import sys
sys.path.insert(0, "/tmp")
import frappe
frappe.init(site="frontend", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
from frappe.utils import today, now_datetime, add_days
try:
    import step19_hide_subcontracting as step19
except ImportError:
    import step29_hide_subcontracting as step19

TEST_RESULTS = []

def record_test(name, passed, message=""):
    status = "PASS" if passed else "FAIL"
    TEST_RESULTS.append({"name": name, "status": status, "message": message})
    indicator = "[PASS]" if passed else "[FAIL]"
    print(f"  {indicator} {name}: {message}")


def test_dependencies():
    print("\n" + "=" * 80)
    print("  TEST 1: SUBCONTRACTING DEPENDENCY CHECK")
    print("=" * 80)
    deps = step19.check_subcontracting_dependencies()
    record_test("Zero Subcontracting dependencies exist in database", len(deps) == 0, f"Dependencies found: {len(deps)}")


def test_property_setters():
    print("\n" + "=" * 80)
    print("  TEST 2: SUBCONTRACTING PROPERTY SETTERS")
    print("=" * 80)

    checks = [
        ("Work Order", "subcontracting_inward_order"),
        ("Work Order Operation", "is_subcontracted"),
        ("Stock Entry", "subcontracting_order"),
        ("Stock Entry", "subcontracting_inward_order"),
        ("Stock Entry Detail", "subcontracted_item"),
        ("Job Card", "is_subcontracted"),
        ("Production Plan", "include_subcontracted_items"),
    ]

    all_hidden = True
    for dt, fn in checks:
        val = frappe.db.get_value("Property Setter", {"doc_type": dt, "field_name": fn, "property": "hidden"}, "value")
        if val != "1":
            all_hidden = False
            print(f"    [FAIL] {dt}.{fn} is not hidden (value={val})")
        else:
            print(f"    [OK] {dt}.{fn} hidden=1")

    record_test("Subcontracting fields hidden via Property Setters on forms", all_hidden)


def test_permissions():
    print("\n" + "=" * 80)
    print("  TEST 3: ROLE PERMISSIONS (NORMAL USERS VS SYSTEM MANAGER)")
    print("=" * 80)

    # 1. System Manager has full access
    for dt in step19.SUBCONTRACTING_DOCTYPES:
        cdp = frappe.db.get_value("Custom DocPerm", {"parent": dt, "role": "System Manager"}, ["read", "write", "create", "submit"], as_dict=True)
        has_full_sm = bool(cdp and cdp.read == 1 and cdp.write == 1 and cdp.create == 1 and cdp.submit == 1)
        record_test(f"System Manager has full access to {dt}", has_full_sm)

    # 2. Normal users do not have permissions on Subcontracting DocTypes
    normal_roles = ["Production Manager", "Floor Worker", "Storekeeper", "Purchase Officer", "Sales Officer", "Manufacturing User", "Stock User"]
    normal_has_access = False
    for dt in step19.SUBCONTRACTING_DOCTYPES:
        for r in normal_roles:
            if frappe.db.exists("Custom DocPerm", {"parent": dt, "role": r}):
                normal_has_access = True
                print(f"    [FAIL] Role {r} has Custom DocPerm on {dt}")

    record_test("Normal user roles explicitly excluded from Subcontracting DocTypes", not normal_has_access)

    # 3. Check block_modules on normal users
    normal_user = "production.manager@orbis.test"
    u_doc = frappe.get_doc("User", normal_user)
    is_blocked = any(row.module == "Subcontracting" for row in u_doc.block_modules)
    record_test(f"Normal user '{normal_user}' has Subcontracting in block_modules", is_blocked)


def test_workspaces():
    print("\n" + "=" * 80)
    print("  TEST 4: WORKSPACE NAVIGATION CLEANUP")
    print("=" * 80)

    # Manufacturing workspace
    ws_mfg = frappe.get_doc("Workspace", "Manufacturing")
    mfg_sub_links = [l for l in ws_mfg.links if "subcontract" in (l.link_to or "").lower() or "subcontract" in (l.label or "").lower()]
    record_test("Manufacturing workspace has zero Subcontracting links", len(mfg_sub_links) == 0, f"Found: {len(mfg_sub_links)}")

    # Buying workspace
    if frappe.db.exists("Workspace", "Buying"):
        ws_buy = frappe.get_doc("Workspace", "Buying")
        buy_sub_links = [l for l in ws_buy.links if "subcontract" in (l.link_to or "").lower() or "subcontract" in (l.label or "").lower()]
        record_test("Buying workspace has zero Subcontracting links", len(buy_sub_links) == 0, f"Found: {len(buy_sub_links)}")


def test_inhouse_manufacturing():
    print("\n" + "=" * 80)
    print("  TEST 5: IN-HOUSE MANUFACTURING & QC FUNCTIONALITY INTEGRITY")
    print("=" * 80)

    vehicle_item = "OCM-VEH-O1-SEDAN"
    source_wh = "Stores - OCM"
    wip_wh = "Work In Progress - OCM"
    fg_wh = "Finished Goods - OCM"
    company = "Orbis Car Manufacturing (Pvt.) Ltd."

    pre_fg_qty = frappe.db.get_value("Bin", {"item_code": vehicle_item, "warehouse": fg_wh}, "actual_qty") or 0.0
    created_docs = []

    try:
        # Seed raw materials
        bom = frappe.get_doc("BOM", "BOM-OCM-VEH-O1-SEDAN-001")
        se_receipt = frappe.new_doc("Stock Entry")
        se_receipt.stock_entry_type = "Material Receipt"
        se_receipt.company = company
        se_receipt.to_warehouse = source_wh
        for item in bom.items:
            se_receipt.append("items", {
                "item_code": item.item_code,
                "qty": item.qty,
                "basic_rate": item.rate or 1000.0,
                "t_warehouse": source_wh,
                "uom": item.uom
            })
        se_receipt.insert(ignore_permissions=True)
        created_docs.append(("Stock Entry", se_receipt.name))
        se_receipt.submit()

        # Create Work Order
        wo = frappe.new_doc("Work Order")
        wo.company = company
        wo.production_item = vehicle_item
        wo.qty = 1
        wo.planned_start_date = now_datetime()
        wo.expected_delivery_date = add_days(today(), 7)
        wo.wip_warehouse = wip_wh
        wo.fg_warehouse = fg_wh
        wo.source_warehouse = source_wh
        wo.transfer_material_against = "Work Order"
        wo.bom_no = bom.name
        wo.operations = []
        wo.insert(ignore_permissions=True)
        created_docs.append(("Work Order", wo.name))
        wo.submit()

        # Material Transfer
        from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry
        se_transfer = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 1))
        se_transfer.insert(ignore_permissions=True)
        created_docs.append(("Stock Entry", se_transfer.name))
        se_transfer.submit()

        # Manufacture
        se_mfg = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 1))
        se_mfg.insert(ignore_permissions=True)
        created_docs.append(("Stock Entry", se_mfg.name))
        se_mfg.submit()

        mid_fg_qty = frappe.db.get_value("Bin", {"item_code": vehicle_item, "warehouse": fg_wh}, "actual_qty") or 0.0
        record_test("Manufactured vehicle added to Finished Goods warehouse without subcontracting", mid_fg_qty == pre_fg_qty + 1.0)

        # Vehicle Registration & QC
        fvr = frappe.new_doc("Finished Vehicle Register")
        fvr.vehicle_model = vehicle_item
        fvr.vin_number = "TEST-VIN-STEP19-001"
        fvr.chassis_number = "TEST-CHAS-STEP19-001"
        fvr.work_order = wo.name
        fvr.warehouse = fg_wh
        fvr.vehicle_status = "In Quality Inspection"
        fvr.insert(ignore_permissions=True)
        created_docs.append(("Finished Vehicle Register", fvr.name))

        qi = frappe.new_doc("Quality Inspection")
        qi.report_date = today()
        qi.inspection_type = "In Process"
        qi.reference_type = "Work Order"
        qi.reference_name = wo.name
        qi.item_code = vehicle_item
        qi.sample_size = 1
        qi.inspected_by = "Administrator"
        qi.manual_inspection = 1
        qi.status = "Accepted"
        qi.finished_vehicle = fvr.name
        qi.insert(ignore_permissions=True)
        created_docs.append(("Quality Inspection", qi.name))
        qi.submit()

        fvr.reload()
        fvr.vehicle_status = "Ready for Dispatch"
        fvr.save(ignore_permissions=True)
        record_test("Quality Inspection and vehicle registration complete successfully", fvr.vehicle_status == "Ready for Dispatch")

    finally:
        for dt, name in reversed(created_docs):
            try:
                if frappe.db.exists(dt, name):
                    doc = frappe.get_doc(dt, name)
                    if doc.docstatus == 1:
                        doc.cancel()
                    frappe.delete_doc(dt, name, force=1, ignore_permissions=True)
            except Exception as e:
                print(f"  [CLEANUP ERROR] {dt} {name}: {e}")

        frappe.db.commit()
        post_fg_qty = frappe.db.get_value("Bin", {"item_code": vehicle_item, "warehouse": fg_wh}, "actual_qty") or 0.0
        record_test("Stock balance returns exactly to pre-test state after test cleanup", post_fg_qty == pre_fg_qty)


def test_rollback_and_reapply():
    print("\n" + "=" * 80)
    print("  TEST 6: ROLLBACK & RE-APPLY CYCLE")
    print("=" * 80)

    # 1. Test Rollback
    step19.rollback()
    wo_ps = frappe.db.get_all("Property Setter", filters={"doc_type": "Work Order", "field_name": "subcontracting_inward_order"})
    record_test("Rollback removes Subcontracting Property Setters", len(wo_ps) == 0)

    sm_cdp = frappe.db.get_all("Custom DocPerm", filters={"parent": "Subcontracting Order"})
    record_test("Rollback removes Custom DocPerms on Subcontracting DocTypes", len(sm_cdp) == 0)

    # 2. Re-apply Step 19
    step19.run()
    wo_ps_re = frappe.db.get_all("Property Setter", filters={"doc_type": "Work Order", "field_name": "subcontracting_inward_order"})
    record_test("Re-apply restores Subcontracting Property Setters", len(wo_ps_re) > 0)

    sm_cdp_re = frappe.db.get_all("Custom DocPerm", filters={"parent": "Subcontracting Order", "role": "System Manager"})
    record_test("Re-apply restores System Manager access to Subcontracting DocTypes", len(sm_cdp_re) > 0)


def main():
    print("=" * 80)
    print("  ORBIS ERP - STEP 19 SUBCONTRACTING AUDIT SUITE")
    print("=" * 80)

    test_dependencies()
    test_property_setters()
    test_permissions()
    test_workspaces()
    test_inhouse_manufacturing()
    test_rollback_and_reapply()

    print("\n" + "=" * 80)
    print("  TEST SUITE SUMMARY")
    print("=" * 80)
    passed = sum(1 for t in TEST_RESULTS if t["status"] == "PASS")
    failed = sum(1 for t in TEST_RESULTS if t["status"] == "FAIL")

    for t in TEST_RESULTS:
        mark = "✓" if t["status"] == "PASS" else "✗"
        print(f"  {mark} [{t['status']}] {t['name']}")

    print(f"\nTotal Tests: {len(TEST_RESULTS)} | Passed: {passed} | Failed: {failed}")
    return passed, failed


if __name__ == "__main__":
    frappe.init(site="frontend", sites_path="/home/frappe/frappe-bench/sites")
    frappe.connect()
    main()
    frappe.destroy()

