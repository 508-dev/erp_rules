from erp_rules.engine import run_checks
from erp_rules.checks.no_cash_account_check import NoCashAccountCheck

CHECKS = [NoCashAccountCheck()]


def validate(doc, method):
    run_checks(doc, CHECKS)
