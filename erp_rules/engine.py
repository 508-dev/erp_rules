import frappe
from erp_rules.checks.base import BLOCK, BaseCheck
from erp_rules.rules.base import BaseRule


def run_rules(doc, rules: list[BaseRule]) -> None:
    messages = _collect_changes(doc, rules)
    if messages:
        frappe.msgprint(
            "<br>".join(messages),
            alert=True,
            indicator="blue",
        )


def _collect_changes(doc, rules: list[BaseRule]) -> list[str]:
    logger = frappe.logger("erp_rules", allow_site=True)
    messages = []

    for rule in rules:
        if not rule.applies_to(doc):
            continue
        try:
            changes = rule.fix(doc)
        except Exception:
            logger.error(
                f"[erp-rules] {doc.doctype} {doc.name} — {rule.__class__.__name__} failed",
                exc_info=True,
            )
            continue
        if changes:
            rule_name = rule.__class__.__name__
            logger.info(
                f"[erp-rules] {doc.doctype} {doc.name} — {rule_name}: {changes}"
            )
            messages.append(f"[{rule_name}] " + "; ".join(changes))

    return messages


def run_checks(doc, checks: list[BaseCheck]) -> None:
    """Warn about or block problems found by checks.

    Checks listed in site config "erp_rules_disabled_checks" are skipped. A check that raises is
    logged and skipped, so a broken check never stops anyone from working.
    """
    warnings, blocks = _collect_problems(doc, checks)
    if warnings:
        frappe.msgprint("<br><br>".join(warnings), title="Please double-check", indicator="orange")
    if blocks:
        frappe.throw("<br><br>".join(blocks), title="Can't save this yet")


def _collect_problems(doc, checks: list[BaseCheck]) -> tuple[list[str], list[str]]:
    logger = frappe.logger("erp_rules", allow_site=True)
    disabled = set(frappe.conf.get("erp_rules_disabled_checks") or [])
    warnings, blocks = [], []

    for check in checks:
        check_name = check.__class__.__name__
        if check_name in disabled or not check.applies_to(doc):
            continue
        try:
            problems = check.problems(doc)
        except Exception:
            logger.error(
                f"[erp-rules] {doc.doctype} {doc.name} — {check_name} failed",
                exc_info=True,
            )
            continue
        for problem in problems:
            logger.info(
                f"[erp-rules] {doc.doctype} {doc.name} — {check_name} ({problem.severity}): {problem.message}"
            )
            (blocks if problem.severity == BLOCK else warnings).append(problem.message)

    return warnings, blocks
