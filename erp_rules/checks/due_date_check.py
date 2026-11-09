from frappe.utils import date_diff
from erp_rules.checks.base import WARN, BaseCheck, Problem
from erp_rules.rules.due_date_rule import MIN_DUE_DATE_DAYS


class DueDateCheck(BaseCheck):
    """Warn when a Sales Invoice is due sooner than the standard payment terms.

    Purchase Invoices don't need this: DueDateRule moves their due date out automatically. Client terms
    are sometimes deliberately shorter, so for Sales Invoices this only warns.
    """

    def applies_to(self, doc) -> bool:
        return bool(doc.posting_date and doc.due_date) and not doc.get("is_return")

    def problems(self, doc) -> list[Problem]:
        days = date_diff(doc.due_date, doc.posting_date)
        if days >= MIN_DUE_DATE_DAYS:
            return []
        return [
            Problem(
                WARN,
                f"This invoice is due {days} day{'s' if days != 1 else ''} after its date; our standard terms "
                f"are at least {MIN_DUE_DATE_DAYS} days. Change the due date unless the client agreed to shorter terms.",
            )
        ]
