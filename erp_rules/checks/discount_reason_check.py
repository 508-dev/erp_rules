from frappe.utils import flt
from erp_rules.checks.base import BLOCK, BaseCheck, Problem, money

MIN_DISCOUNT = 1.0  # ignore rounding-sized discounts


class DiscountReasonCheck(BaseCheck):
    """A Sales Invoice discount needs a written reason before it is submitted.

    An invoice once carried a large discount for an overpayment that never happened;
    a required reason makes someone state what a discount is for.
    """

    def applies_to(self, doc) -> bool:
        return doc.docstatus == 1 and abs(flt(doc.discount_amount)) >= MIN_DISCOUNT

    def problems(self, doc) -> list[Problem]:
        if (doc.get("discount_reason") or "").strip():
            return []
        return [
            Problem(
                BLOCK,
                f"This invoice has a {money(doc.discount_amount)} discount. Fill in Discount Reason "
                "(who agreed to it and why) before submitting.",
            )
        ]
