from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

# Fields the checks rely on. Created on install and refreshed on every migrate.
CUSTOM_FIELDS = {
    "Sales Invoice": [
        {
            "fieldname": "discount_reason",
            "label": "Discount Reason",
            "fieldtype": "Small Text",
            "insert_after": "discount_amount",
            "depends_on": "eval:doc.discount_amount || doc.additional_discount_percentage",
            "description": "Required to submit an invoice with a discount: who agreed to it and why.",
            "module": "ERP Rules",
        }
    ],
    "Payment Entry": [
        {
            "fieldname": "confirm_not_duplicate",
            "label": "Not a duplicate",
            "fieldtype": "Check",
            "insert_after": "reference_date",
            "description": "Tick only when another payment of the same amount to the same party "
            "within a week really is a separate payment.",
            "module": "ERP Rules",
        }
    ],
}


def create_fields():
    create_custom_fields(CUSTOM_FIELDS, update=True)
