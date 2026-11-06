from erp_rules.engine import run_checks
from erp_rules.checks.client_paid_check import ClientPaidCheck
from erp_rules.checks.duplicate_payment_check import DuplicatePaymentCheck
from erp_rules.checks.no_cash_account_check import NoCashAccountCheck

CHECKS = [NoCashAccountCheck(), DuplicatePaymentCheck(), ClientPaidCheck()]


def validate(doc, method):
    run_checks(doc, CHECKS)
