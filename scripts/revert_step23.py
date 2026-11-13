import frappe, os
os.makedirs("/home/frappe/logs", exist_ok=True)
os.chdir("/home/frappe/frappe-bench/sites")
frappe.init(site="frontend", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()

if frappe.db.exists("Client Script", "orbis-dn-hide-create"):
    frappe.delete_doc("Client Script", "orbis-dn-hide-create", ignore_permissions=True)
    frappe.db.commit()
    print("Deleted Client Script: orbis-dn-hide-create")
else:
    print("Client Script not found, already removed.")

try:
    frappe.clear_cache(doctype="Delivery Note")
    frappe.cache().delete_key("bootinfo")
except Exception as e:
    print(f"Cache clear notice: {e}")

frappe.destroy()
print("Revert complete: Create button and all sub-options restored.")
