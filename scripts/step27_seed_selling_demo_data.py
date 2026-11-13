"""Create five fictional Selling customers, draft Quotations, and linked draft Sales Orders.

Safe to rerun: existing demo customers and matching demo quotations are reused.
The quotations and Sales Orders remain drafts and are never submitted, so this script
does not post stock ledger or general ledger entries.
"""

import json
from pathlib import Path

import frappe
from frappe.utils import add_days, nowdate


DATA_FILE = Path(__file__).with_name("selling_demo_customers_and_quotations.json")
if not DATA_FILE.exists():
    DATA_FILE = Path("/tmp/selling_demo_customers_and_quotations.json")



def _required_record(doctype, name):
    if not frappe.db.exists(doctype, name):
        frappe.throw(f"Required {doctype} '{name}' is missing; no demo records were created.")
    return frappe.get_doc(doctype, name)


def _customer_for(data):
    name = frappe.db.get_value("Customer", {"customer_name": data["customer_name"]}, "name")
    if name:
        return frappe.get_doc("Customer", name), False

    customer = frappe.new_doc("Customer")
    customer.customer_name = data["customer_name"]
    customer.customer_type = "Company"
    customer.customer_group = "Commercial"
    customer.territory = "Pakistan"
    customer.email_id = data["email_id"]
    customer.default_currency = "PKR"
    if frappe.get_meta("Customer").has_field("default_price_list"):
        customer.default_price_list = "Standard Selling"
    customer.insert(ignore_permissions=True)
    return customer, True


def _address_for(customer, data):
    address_name = frappe.db.get_value(
        "Address",
        {"address_title": customer.customer_name, "address_type": "Billing"},
        "name",
    )
    if address_name:
        address = frappe.get_doc("Address", address_name)
    else:
        address = frappe.new_doc("Address")
        address.address_title = customer.customer_name
        address.address_type = "Billing"
        address.address_line1 = f"Demo business address - {data['city']}"
        address.city = data["city"]
        address.country = "Pakistan"
        address.email_id = data["email_id"]
        address.is_primary_address = 1
        address.append("links", {"link_doctype": "Customer", "link_name": customer.name})
        address.insert(ignore_permissions=True)

    customer.customer_primary_address = address.name
    customer.save(ignore_permissions=True)
    return address


def _quotation_for(customer, address, item, config):
    title = f"DEMO - Quote - {customer.customer_name.removeprefix('DEMO - ')}"
    existing = frappe.get_all(
        "Quotation",
        filters={"party_name": customer.name, "title": title},
        fields=["name", "docstatus", "status"],
        limit_page_length=1,
    )
    if existing:
        quotation = frappe.get_doc("Quotation", existing[0].name)
        if quotation.docstatus == 0 and not quotation.customer_address:
            quotation.customer_address = address.name
            quotation.save(ignore_permissions=True)
        return quotation, False

    quotation = frappe.new_doc("Quotation")
    quotation.quotation_to = "Customer"
    quotation.party_name = customer.name
    quotation.company = config["company"]
    quotation.order_type = "Sales"
    quotation.transaction_date = nowdate()
    quotation.valid_till = add_days(nowdate(), int(config["quote_valid_days"]))
    quotation.currency = config["currency"]
    quotation.selling_price_list = config["selling_price_list"]
    quotation.price_list_currency = config["currency"]
    quotation.conversion_rate = 1
    quotation.plc_conversion_rate = 1
    quotation.taxes_and_charges = config["sales_taxes_and_charges"]
    quotation.customer_address = address.name
    quotation.title = title
    quotation.append(
        "items",
        {
            "item_code": item.name,
            "item_name": item.item_name,
            "description": f"{item.item_name} - demo vehicle quotation",
            "qty": config["quantity"],
            "uom": item.stock_uom,
            "rate": config["expected_unit_rate"],
            "warehouse": config["warehouse"],
        },
    )
    quotation.set_missing_values()
    quotation.calculate_taxes_and_totals()
    quotation.insert(ignore_permissions=True)
    if quotation.docstatus != 0:
        frappe.throw(f"Quotation {quotation.name} was not left as a draft.")
    return quotation, True


def _sales_order_for(customer, quotation, config):
    existing_name = frappe.db.get_value(
        "Sales Order Item", {"prevdoc_docname": quotation.name}, "parent"
    )
    if existing_name:
        return frappe.get_doc("Sales Order", existing_name), False

    from frappe.model.mapper import get_mapped_doc

    def set_missing_values(source, target):
        target.customer = customer.name
        target.customer_name = customer.customer_name
        target.flags.ignore_permissions = True
        target.run_method("set_missing_values")
        target.delivery_date = add_days(nowdate(), int(config["sales_order_delivery_days"]))
        for row in target.items:
            row.delivery_date = target.delivery_date
        target.run_method("calculate_taxes_and_totals")

    # Use ERPNext's mapper and field maps, while allowing a draft Quotation as the source.
    # ERPNext's standard button requires a submitted Quotation, which would turn this demo
    # data into an issued offer. These draft orders keep the source links without submitting it.
    sales_order = get_mapped_doc(
        "Quotation",
        quotation.name,
        {
            "Quotation": {
                "doctype": "Sales Order",
                "field_no_map": ["payment_terms_template"],
            },
            "Quotation Item": {
                "doctype": "Sales Order Item",
                "field_map": {"parent": "prevdoc_docname", "name": "quotation_item"},
            },
            "Sales Taxes and Charges": {
                "doctype": "Sales Taxes and Charges",
                "reset_value": True,
            },
            "Sales Team": {"doctype": "Sales Team", "add_if_empty": True},
        },
        None,
        set_missing_values,
        ignore_permissions=True,
    )
    sales_order.transaction_date = nowdate()
    sales_order.delivery_date = add_days(nowdate(), int(config["sales_order_delivery_days"]))
    for row in sales_order.items:
        row.delivery_date = sales_order.delivery_date
    sales_order.flags.ignore_permissions = True
    sales_order.insert(ignore_permissions=True)
    if sales_order.docstatus != 0:
        frappe.throw(f"Sales Order {sales_order.name} was not left as a draft.")
    return sales_order, True


def _configure_selling_sidebar():
    from frappe.desk.doctype.custom_sidebar.custom_sidebar import add_site_sidebar_item

    add_site_sidebar_item(
        "Selling",
        {"type": "Section Break", "label": "Customers & Quotations", "icon": "users"},
    )
    for item in [
        {"type": "Link", "label": "Quotations", "link_type": "DocType", "link_to": "Quotation", "icon": "file-text"},
        {"type": "Link", "label": "Sales Orders", "link_type": "DocType", "link_to": "Sales Order", "icon": "file-check"},
        {"type": "Link", "label": "Customers", "link_type": "DocType", "link_to": "Customer", "icon": "users"},
    ]:
        add_site_sidebar_item("Selling", item)


def run():
    with DATA_FILE.open("r", encoding="utf-8") as data_file:
        config = json.load(data_file)

    if len(config.get("customers", [])) != 5:
        frappe.throw("The Selling demo data file must contain exactly five customers.")

    company = _required_record("Company", config["company"])
    price_list = _required_record("Price List", config["selling_price_list"])
    tax_template = _required_record("Sales Taxes and Charges Template", config["sales_taxes_and_charges"])
    _required_record("Warehouse", config["warehouse"])
    _required_record("Customer Group", "Commercial")
    _required_record("Territory", "Pakistan")

    item_code = config["item_code"]
    if not frappe.db.exists("Item", item_code):
        item_doc = frappe.new_doc("Item")
        item_doc.item_code = item_code
        item_doc.item_name = f"Orbis Executive Sedan Model {item_code}"
        item_doc.item_group = "Finished Cars"
        item_doc.stock_uom = "Nos"
        item_doc.is_stock_item = 1
        item_doc.is_sales_item = 1
        item_doc.valuation_rate = 4000000
        item_doc.default_warehouse = config["warehouse"]
        item_doc.insert(ignore_permissions=True)
        print(f"Created Item: {item_code}")

    item = _required_record("Item", item_code)

    if tax_template.company != company.name:
        frappe.throw(f"Tax template '{tax_template.name}' does not belong to '{company.name}'.")
    if price_list.currency != config["currency"]:
        frappe.throw(f"Price list '{price_list.name}' is not in {config['currency']}.")
    if not item.is_sales_item:
        frappe.throw(f"Item '{item.name}' is not enabled as a sales item.")

    price_filter = {
        "item_code": item.name,
        "price_list": price_list.name,
        "selling": 1,
        "currency": config["currency"],
    }
    configured_rate = frappe.db.get_value("Item Price", price_filter, "price_list_rate")
    if configured_rate is None:
        ip = frappe.new_doc("Item Price")
        ip.item_code = item.name
        ip.price_list = price_list.name
        ip.price_list_rate = float(config["expected_unit_rate"])
        ip.currency = config["currency"]
        ip.selling = 1
        ip.insert(ignore_permissions=True)
        print(f"Created Item Price for {item.name}: {config['expected_unit_rate']}")
        configured_rate = float(config["expected_unit_rate"])
    elif float(configured_rate) != float(config["expected_unit_rate"]):
        frappe.db.set_value("Item Price", {"item_code": item.name, "price_list": price_list.name}, "price_list_rate", float(config["expected_unit_rate"]))
        configured_rate = float(config["expected_unit_rate"])


    created_customers = 0
    created_quotations = 0
    created_sales_orders = 0
    results = []
    try:
        _configure_selling_sidebar()
        for customer_data in config["customers"]:
            customer, customer_created = _customer_for(customer_data)
            address = _address_for(customer, customer_data)
            quotation, quotation_created = _quotation_for(customer, address, item, config)
            sales_order, sales_order_created = _sales_order_for(customer, quotation, config)
            created_customers += int(customer_created)
            created_quotations += int(quotation_created)
            created_sales_orders += int(sales_order_created)
            results.append(
                {
                    "customer": customer.customer_name,
                    "quotation": quotation.name,
                    "status": quotation.status,
                    "docstatus": quotation.docstatus,
                    "currency": quotation.currency,
                    "grand_total": quotation.grand_total,
                    "sales_order": sales_order.name,
                    "sales_order_status": sales_order.status,
                    "sales_order_docstatus": sales_order.docstatus,
                    "sales_order_grand_total": sales_order.grand_total,
                }
            )
        frappe.db.commit()
        frappe.clear_cache()
    except Exception:
        frappe.db.rollback()
        raise

    print(
        f"Created {created_customers} customer(s), {created_quotations} draft quotation(s), "
        f"and {created_sales_orders} draft Sales Order(s)."
    )
    for result in results:
        print(
            f"{result['customer']} | {result['quotation']} | {result['status']} "
            f"(docstatus={result['docstatus']}) | {result['currency']} {result['grand_total']:,.2f} "
            f"| {result['sales_order']} | {result['sales_order_status']} "
            f"(docstatus={result['sales_order_docstatus']}) | "
            f"{result['currency']} {result['sales_order_grand_total']:,.2f}"
        )
    print("No Quotation or Sales Order was submitted; no stock or GL entries were posted.")
    return f"Prepared {len(results)} customer quotations and Sales Orders in Selling."


if __name__ == "__main__":
    frappe.init(site="frontend", sites_path="/home/frappe/frappe-bench/sites")
    frappe.connect()
    run()
    frappe.destroy()
