import frappe
from frappe.utils import add_days, flt
from erp_rules.checks.base import BLOCK, BaseCheck, Problem, money

WINDOW_DAYS = 7


class DuplicatePaymentCheck(BaseCheck):
    """Stop a second payment of the same amount to or from the same party within a week.

    An engineer's payout was once recorded twice: once by hand, and again when its bank line was
    reconciled with "create payment" instead of being matched to the first one.
    """

    def applies_to(self, doc) -> bool:
        return (
            doc.docstatus == 1
            and bool(doc.party)
            and flt(doc.paid_amount) > 0
            and not doc.get("confirm_not_duplicate")
        )

    def problems(self, doc) -> list[Problem]:
        matches = self._similar_payments(doc)
        if not matches:
            return []
        first = matches[0]
        direction = "paid to" if doc.payment_type == "Pay" else "received from"
        return [
            Problem(
                BLOCK,
                f"{first.name} already records {money(doc.paid_amount)} {direction} {doc.party} on "
                f"{first.posting_date}. If this is the same money, reconcile the bank line to {first.name} "
                "instead of creating a new payment. If it really is a second payment, tick "
                "“Not a duplicate” and submit again.",
            )
        ]

    def _similar_payments(self, doc):
        return frappe.get_all(
            "Payment Entry",
            filters={
                "docstatus": 1,
                "name": ["!=", doc.name],
                "party_type": doc.party_type,
                "party": doc.party,
                "payment_type": doc.payment_type,
                "paid_amount": flt(doc.paid_amount),
                "posting_date": [
                    "between",
                    [add_days(doc.posting_date, -WINDOW_DAYS), add_days(doc.posting_date, WINDOW_DAYS)],
                ],
            },
            fields=["name", "posting_date"],
            order_by="posting_date",
        )
