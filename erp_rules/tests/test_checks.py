import unittest
from unittest.mock import MagicMock, patch

import frappe

from erp_rules.checks.base import BLOCK, WARN
from erp_rules.checks.client_paid_check import ClientPaidCheck
from erp_rules.checks.discount_reason_check import DiscountReasonCheck
from erp_rules.checks.due_date_check import DueDateCheck
from erp_rules.checks.duplicate_payment_check import DuplicatePaymentCheck
from erp_rules.checks.hours_as_quantity_check import HoursAsQuantityCheck
from erp_rules.checks.no_cash_account_check import NoCashAccountCheck


def make_doc(**fields):
    return frappe._dict(fields)


def item(item_code, qty, rate, idx=1):
    return frappe._dict(item_code=item_code, qty=qty, rate=rate, idx=idx)


class TestDiscountReasonCheck(unittest.TestCase):
    def setUp(self):
        self.check = DiscountReasonCheck()

    def test_ignores_drafts(self):
        self.assertFalse(self.check.applies_to(make_doc(docstatus=0, discount_amount=2500)))

    def test_ignores_rounding_sized_discounts(self):
        self.assertFalse(self.check.applies_to(make_doc(docstatus=1, discount_amount=0.45)))

    def test_blocks_discount_without_reason(self):
        doc = make_doc(docstatus=1, discount_amount=2500, discount_reason="  ")
        self.assertTrue(self.check.applies_to(doc))
        problems = self.check.problems(doc)
        self.assertEqual([p.severity for p in problems], [BLOCK])
        self.assertIn("$2,500.00", problems[0].message)

    def test_allows_discount_with_reason(self):
        doc = make_doc(docstatus=1, discount_amount=120, discount_reason="Agreed with client on 5/18 call")
        self.assertEqual(self.check.problems(doc), [])


class TestHoursAsQuantityCheck(unittest.TestCase):
    def setUp(self):
        self.check = HoursAsQuantityCheck()

    def test_ignores_hourly_lines(self):
        doc = make_doc(project="PROJ-1", items=[item("Contract Engineering (Purchasing)", 57, 153)])
        self.assertFalse(self.check.applies_to(doc))

    def test_ignores_other_items(self):
        doc = make_doc(project="PROJ-1", items=[item("Internal Commission", 1, 923.4)])
        self.assertFalse(self.check.applies_to(doc))

    def test_warns_on_lump_sum_for_hourly_project(self):
        doc = make_doc(
            project="PROJ-1", posting_date="2026-06-15",
            items=[item("Contract Engineering (Purchasing)", 1, 8000, idx=2)],
        )
        self.assertTrue(self.check.applies_to(doc))
        with patch.object(HoursAsQuantityCheck, "_project_bills_hourly", return_value=True):
            problems = self.check.problems(doc)
        self.assertEqual([p.severity for p in problems], [WARN])
        self.assertIn("Row 2", problems[0].message)

    def test_quiet_for_retainer_projects(self):
        doc = make_doc(
            project="PROJ-1", posting_date="2026-06-15",
            items=[item("Contract Engineering (Purchasing)", 1, 6375)],
        )
        with patch.object(HoursAsQuantityCheck, "_project_bills_hourly", return_value=False):
            self.assertEqual(self.check.problems(doc), [])


class TestNoCashAccountCheck(unittest.TestCase):
    def setUp(self):
        self.check = NoCashAccountCheck()

    def _account_types(self, mapping):
        return patch(
            "erp_rules.checks.no_cash_account_check.frappe.get_cached_value",
            side_effect=lambda doctype, name, field: mapping.get(name),
        )

    def test_blocks_payment_from_cash(self):
        doc = make_doc(doctype="Payment Entry", paid_from="1110 - Cash - 5", paid_to="2110 - Creditors - 5")
        with self._account_types({"1110 - Cash - 5": "Cash", "2110 - Creditors - 5": "Payable"}):
            problems = self.check.problems(doc)
        self.assertEqual([p.severity for p in problems], [BLOCK])
        self.assertIn("1110 - Cash - 5", problems[0].message)

    def test_allows_bank_payment(self):
        doc = make_doc(doctype="Payment Entry", paid_from="Wise - 5", paid_to="2110 - Creditors - 5")
        with self._account_types({"Wise - 5": "Bank", "2110 - Creditors - 5": "Payable"}):
            self.assertEqual(self.check.problems(doc), [])

    def test_blocks_journal_entry_with_cash_line(self):
        doc = make_doc(
            doctype="Journal Entry",
            accounts=[frappe._dict(account="Novo - 5"), frappe._dict(account="1110 - Cash - 5")],
        )
        with self._account_types({"Novo - 5": "Bank", "1110 - Cash - 5": "Cash"}):
            self.assertEqual(len(self.check.problems(doc)), 1)

    def test_ignores_other_doctypes(self):
        self.assertFalse(self.check.applies_to(make_doc(doctype="Sales Invoice")))


class TestDuplicatePaymentCheck(unittest.TestCase):
    def setUp(self):
        self.check = DuplicatePaymentCheck()

    def _payout(self, **overrides):
        fields = dict(
            docstatus=1, name="PAY-NEW", party_type="Supplier", party="Engineer A",
            payment_type="Pay", paid_amount=5000.00, posting_date="2026-10-20", confirm_not_duplicate=0,
        )
        fields.update(overrides)
        return make_doc(**fields)

    def test_blocks_second_identical_payout(self):
        existing = [frappe._dict(name="PAY-OLD", posting_date="2026-10-20")]
        with patch.object(DuplicatePaymentCheck, "_similar_payments", return_value=existing):
            problems = self.check.problems(self._payout())
        self.assertEqual([p.severity for p in problems], [BLOCK])
        self.assertIn("PAY-OLD", problems[0].message)
        self.assertIn("paid to Engineer A", problems[0].message)

    def test_passes_when_no_similar_payment(self):
        with patch.object(DuplicatePaymentCheck, "_similar_payments", return_value=[]):
            self.assertEqual(self.check.problems(self._payout()), [])

    def test_override_skips_the_check(self):
        self.assertFalse(self.check.applies_to(self._payout(confirm_not_duplicate=1)))

    def test_ignores_drafts_and_transfers(self):
        self.assertFalse(self.check.applies_to(self._payout(docstatus=0)))
        self.assertFalse(self.check.applies_to(self._payout(party=None)))


class TestClientPaidCheck(unittest.TestCase):
    def setUp(self):
        self.check = ClientPaidCheck()

    def _payout(self):
        return make_doc(
            docstatus=1, payment_type="Pay", party_type="Supplier", party="Engineer B",
            references=[frappe._dict(reference_doctype="Purchase Invoice", reference_name="PINV-APRIL")],
        )

    def test_warns_when_client_has_not_paid(self):
        bill = frappe._dict(project="PROJ-TEST", posting_date="2026-05-12", timesheet=None)
        unpaid = [frappe._dict(name="SINV-APRIL", grand_total=7000, outstanding_amount=7000)]
        with patch.object(ClientPaidCheck, "_is_engineering_bill", return_value=True), \
                patch.object(ClientPaidCheck, "_unpaid_client_invoices", return_value=unpaid), \
                patch.object(ClientPaidCheck, "_bill", return_value=bill):
            problems = self.check.problems(self._payout())
        self.assertEqual([p.severity for p in problems], [WARN])
        self.assertIn("SINV-APRIL", problems[0].message)

    def test_quiet_when_client_has_paid(self):
        bill = frappe._dict(project="PROJ-TEST", posting_date="2026-05-12", timesheet=None)
        with patch.object(ClientPaidCheck, "_is_engineering_bill", return_value=True), \
                patch.object(ClientPaidCheck, "_unpaid_client_invoices", return_value=[]), \
                patch.object(ClientPaidCheck, "_bill", return_value=bill):
            self.assertEqual(self.check.problems(self._payout()), [])

    def test_skips_referral_and_other_bills(self):
        with patch.object(ClientPaidCheck, "_is_engineering_bill", return_value=False):
            self.assertEqual(self.check.problems(self._payout()), [])

    def test_ignores_receipts(self):
        doc = self._payout()
        doc.payment_type = "Receive"
        self.assertFalse(self.check.applies_to(doc))


class TestDueDateCheck(unittest.TestCase):
    def setUp(self):
        self.check = DueDateCheck()

    def test_warns_when_due_too_soon(self):
        problems = self.check.problems(make_doc(posting_date="2026-11-01", due_date="2026-11-15"))
        self.assertEqual([p.severity for p in problems], [WARN])
        self.assertIn("14 days", problems[0].message)

    def test_same_day_is_singular(self):
        self.assertIn("0 days", self.check.problems(make_doc(posting_date="2026-11-01", due_date="2026-11-01"))[0].message)

    def test_quiet_at_standard_terms(self):
        self.assertEqual(self.check.problems(make_doc(posting_date="2026-11-01", due_date="2026-11-30")), [])

    def test_ignores_credit_notes(self):
        self.assertFalse(self.check.applies_to(make_doc(posting_date="2026-11-01", due_date="2026-11-01", is_return=1)))
