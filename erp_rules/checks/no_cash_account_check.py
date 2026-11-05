import frappe
from erp_rules.checks.base import BLOCK, BaseCheck, Problem


class NoCashAccountCheck(BaseCheck):
    """508 holds no cash, so a Cash account on a payment or journal entry is always a mistake.

    Bank payouts booked to Cash once left the Cash account deeply negative, and one of them was
    recorded twice when its bank line was later reconciled.
    Disable with site config "erp_rules_disabled_checks": ["NoCashAccountCheck"] if that changes.
    """

    def applies_to(self, doc) -> bool:
        return doc.doctype in ("Payment Entry", "Journal Entry")

    def problems(self, doc) -> list[Problem]:
        if doc.doctype == "Payment Entry":
            accounts = [doc.paid_from, doc.paid_to]
        else:
            accounts = [row.account for row in doc.get("accounts") or []]
        cash = sorted({a for a in accounts if a and self._is_cash(a)})
        if not cash:
            return []
        return [
            Problem(
                BLOCK,
                f"{', '.join(cash)} is a cash account, and 508 doesn't hold cash. Use the bank account "
                "the money actually moved through (Wise, Novo or Chase) so it can be matched to the bank line.",
            )
        ]

    def _is_cash(self, account) -> bool:
        return frappe.get_cached_value("Account", account, "account_type") == "Cash"
