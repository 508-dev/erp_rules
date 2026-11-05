import frappe
from frappe.utils import add_days, flt
from erp_rules.checks.base import WARN, BaseCheck, Problem, money

HOURLY_ITEMS = {"Contract Engineering (Sales)", "Contract Engineering (Purchasing)"}
LUMP_SUM_RATE = 300  # an hourly rate above this is almost certainly a whole month entered as one line
LOOKBACK_DAYS = 90  # a project counts as hourly if it was invoiced by the hour this recently


class HoursAsQuantityCheck(BaseCheck):
    """Hourly work should be entered as hours × rate, not as one lump-sum line.

    Lump sums make it impossible to compare the hours billed to the client with the hours
    paid to the engineer, which is how hours billed twice on a client invoice once went unnoticed.
    """

    def applies_to(self, doc) -> bool:
        return bool(doc.get("project")) and bool(self._lump_sum_lines(doc))

    def problems(self, doc) -> list[Problem]:
        if not self._project_bills_hourly(doc.project, doc.posting_date):
            return []
        return [
            Problem(
                WARN,
                f"Row {item.idx}: {item.item_code} is entered as 1 × {money(item.rate)}. Project "
                f"{doc.project} is billed by the hour, so enter the hours as Quantity and the hourly "
                "rate as Rate. Otherwise billed and paid hours can't be compared.",
            )
            for item in self._lump_sum_lines(doc)
        ]

    def _lump_sum_lines(self, doc):
        return [
            item
            for item in doc.get("items") or []
            if item.item_code in HOURLY_ITEMS and flt(item.qty) == 1 and flt(item.rate) > LUMP_SUM_RATE
        ]

    def _project_bills_hourly(self, project, posting_date) -> bool:
        return bool(
            frappe.db.sql(
                """
                select 1 from `tabSales Invoice Item` i
                join `tabSales Invoice` s on s.name = i.parent
                where s.docstatus = 1 and s.project = %s and s.posting_date >= %s
                  and i.item_code = 'Contract Engineering (Sales)' and i.qty > 1
                limit 1
                """,
                (project, add_days(posting_date, -LOOKBACK_DAYS)),
            )
        )
