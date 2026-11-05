app_name = "erp_rules"
app_title = "ERP Rules"
app_publisher = "508.dev"
app_description = "Server-side rule engine for ERPNext — auto-fills and validates documents before save."
app_email = "admin@508.dev"
app_license = "mit"

after_install = "erp_rules.setup.create_fields"
after_migrate = ["erp_rules.setup.create_fields"]

doc_events = {
    "Sales Invoice": {
        "before_save": "erp_rules.handlers.sales_invoice.before_save",
        "validate": "erp_rules.handlers.sales_invoice.validate",
    },
    "Purchase Invoice": {
        "before_save": "erp_rules.handlers.purchase_invoice.before_save",
        "validate": "erp_rules.handlers.purchase_invoice.validate",
    },
    "Payment Entry": {
        "validate": "erp_rules.handlers.payment_entry.validate",
    },
    "Journal Entry": {
        "validate": "erp_rules.handlers.journal_entry.validate",
    },
}
