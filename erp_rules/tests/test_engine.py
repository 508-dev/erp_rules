import unittest
from unittest.mock import MagicMock, patch
from erp_rules.engine import run_rules
from erp_rules.rules.base import BaseRule


class AlwaysAppliesRule(BaseRule):
    def applies_to(self, doc):
        return True

    def fix(self, doc):
        return ["field: old → new"]


class NeverAppliesRule(BaseRule):
    def applies_to(self, doc):
        return False

    def fix(self, doc):
        return ["should not appear"]


class ExplodingRule(BaseRule):
    def applies_to(self, doc):
        return True

    def fix(self, doc):
        raise RuntimeError("intentional failure")


class TestEngine(unittest.TestCase):
    def _make_doc(self):
        doc = MagicMock()
        doc.doctype = "Sales Invoice"
        doc.name = "SINV-TEST-001"
        return doc

    @patch("erp_rules.engine.frappe")
    def test_notifies_user_when_changes_made(self, mock_frappe):
        mock_frappe.logger.return_value = MagicMock()
        doc = self._make_doc()
        run_rules(doc, [AlwaysAppliesRule()])
        mock_frappe.msgprint.assert_called_once()
        call_args = mock_frappe.msgprint.call_args[0][0]
        self.assertIn("[AlwaysAppliesRule]", call_args)
        self.assertIn("field: old → new", call_args)

    @patch("erp_rules.engine.frappe")
    def test_skips_non_applicable_rules(self, mock_frappe):
        mock_frappe.logger.return_value = MagicMock()
        doc = self._make_doc()
        run_rules(doc, [NeverAppliesRule()])
        mock_frappe.msgprint.assert_not_called()

    @patch("erp_rules.engine.frappe")
    def test_broken_rule_does_not_block_other_rules(self, mock_frappe):
        mock_frappe.logger.return_value = MagicMock()
        doc = self._make_doc()
        run_rules(doc, [ExplodingRule(), AlwaysAppliesRule()])
        mock_frappe.msgprint.assert_called_once()
        call_args = mock_frappe.msgprint.call_args[0][0]
        self.assertIn("[AlwaysAppliesRule]", call_args)

    @patch("erp_rules.engine.frappe")
    def test_broken_rule_logs_error(self, mock_frappe):
        mock_logger = MagicMock()
        mock_frappe.logger.return_value = mock_logger
        doc = self._make_doc()
        run_rules(doc, [ExplodingRule()])
        mock_logger.error.assert_called_once()

    @patch("erp_rules.engine.frappe")
    def test_no_notification_when_no_changes(self, mock_frappe):
        mock_frappe.logger.return_value = MagicMock()
        doc = self._make_doc()
        run_rules(doc, [NeverAppliesRule()])
        mock_frappe.msgprint.assert_not_called()


from erp_rules.checks.base import BLOCK, WARN, BaseCheck, Problem
from erp_rules.engine import run_checks


class WarningCheck(BaseCheck):
    def applies_to(self, doc):
        return True

    def problems(self, doc):
        return [Problem(WARN, "look at this")]


class BlockingCheck(BaseCheck):
    def applies_to(self, doc):
        return True

    def problems(self, doc):
        return [Problem(BLOCK, "fix this first")]


class ExplodingCheck(BaseCheck):
    def applies_to(self, doc):
        return True

    def problems(self, doc):
        raise RuntimeError("intentional failure")


class TestRunChecks(unittest.TestCase):
    def _make_doc(self):
        doc = MagicMock()
        doc.doctype = "Payment Entry"
        doc.name = "PAY-TEST-001"
        return doc

    def _frappe(self, mock_frappe, disabled=None):
        mock_frappe.logger.return_value = MagicMock()
        mock_frappe.conf.get.return_value = disabled

    @patch("erp_rules.engine.frappe")
    def test_warning_is_shown_without_blocking(self, mock_frappe):
        self._frappe(mock_frappe)
        run_checks(self._make_doc(), [WarningCheck()])
        mock_frappe.msgprint.assert_called_once()
        mock_frappe.throw.assert_not_called()

    @patch("erp_rules.engine.frappe")
    def test_block_throws(self, mock_frappe):
        self._frappe(mock_frappe)
        run_checks(self._make_doc(), [BlockingCheck(), WarningCheck()])
        mock_frappe.throw.assert_called_once()
        self.assertIn("fix this first", mock_frappe.throw.call_args[0][0])

    @patch("erp_rules.engine.frappe")
    def test_disabled_check_is_skipped(self, mock_frappe):
        self._frappe(mock_frappe, disabled=["BlockingCheck"])
        run_checks(self._make_doc(), [BlockingCheck()])
        mock_frappe.throw.assert_not_called()

    @patch("erp_rules.engine.frappe")
    def test_broken_check_never_blocks(self, mock_frappe):
        self._frappe(mock_frappe)
        run_checks(self._make_doc(), [ExplodingCheck()])
        mock_frappe.throw.assert_not_called()
        mock_frappe.logger.return_value.error.assert_called_once()
