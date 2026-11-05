import frappe
from frappe.utils import add_days
from erp_rules.checks.base import WARN, BaseCheck, Problem, money

ENGINEERING_ITEM = "Contract Engineering (Purchasing)"
SAME_PERIOD_DAYS = 10  # client invoices issued up to this long after the engineer's bill cover the same work


class ClientPaidCheck(BaseCheck):
    """Warn when paying an engineer for work the client hasn't paid for yet.

    When the engineer is paid first, the client's later payment for that month is easy to mistake for a
    duplicate; that once led to a client being credited for an overpayment that never happened.
    Fronting a payout is sometimes fine, so this only warns.
    """

    def applies_to(self, doc) -> bool:
        return (
            doc.docstatus == 1
            and doc.payment_type == "Pay"
            and doc.party_type == "Supplier"
            and any(ref.reference_doctype == "Purchase Invoice" for ref in doc.get("references") or [])
        )

    def problems(self, doc) -> list[Problem]:
        problems = []
        for ref in doc.references:
            if ref.reference_doctype != "Purchase Invoice" or not self._is_engineering_bill(ref.reference_name):
                continue
            bill = self._bill(ref.reference_name)
            if not bill or not bill.project:
                continue
            unpaid = self._unpaid_client_invoices(bill)
            if unpaid:
                listing = ", ".join(
                    f"{si.name} ({money(si.outstanding_amount)} of {money(si.grand_total)} unpaid)" for si in unpaid
                )
                problems.append(
                    Problem(
                        WARN,
                        f"{ref.reference_name} is for project {bill.project}, but the client hasn't paid "
                        f"{listing} yet. Paying now means 508 fronts this payout; when the client's payment "
                        "arrives, apply it to that invoice rather than treating it as a duplicate.",
                    )
                )
        return problems

    def _bill(self, purchase_invoice):
        return frappe.db.get_value(
            "Purchase Invoice", purchase_invoice, ["project", "posting_date", "timesheet"], as_dict=True
        )

    def _is_engineering_bill(self, purchase_invoice) -> bool:
        return bool(
            frappe.db.exists("Purchase Invoice Item", {"parent": purchase_invoice, "item_code": ENGINEERING_ITEM})
        )

    def _unpaid_client_invoices(self, bill):
        # Prefer the exact invoice(s) that billed this bill's timesheet; otherwise use the project's
        # invoices issued up to the end of the same billing period.
        filters = {"docstatus": 1, "outstanding_amount": [">", 0.009]}
        billed_by = []
        if bill.timesheet:
            billed_by = frappe.get_all(
                "Timesheet Detail",
                filters={"parent": bill.timesheet, "sales_invoice": ["is", "set"]},
                pluck="sales_invoice",
                distinct=True,
            )
        if billed_by:
            filters["name"] = ["in", billed_by]
        else:
            filters["project"] = bill.project
            filters["posting_date"] = ["<=", add_days(bill.posting_date, SAME_PERIOD_DAYS)]
        return frappe.get_all(
            "Sales Invoice",
            filters=filters,
            fields=["name", "grand_total", "outstanding_amount"],
            order_by="posting_date",
        )
