# erp-rules

A server-side rule engine for [ERPNext](https://erpnext.com/) / [Frappe](https://frappeframework.com/).

Automatically corrects common data entry errors on documents before they are saved — so problems are prevented rather than caught after the fact.

---

## What it does

Each rule is an independent class that inspects a document and returns a list of changes it made. The engine runs all applicable rules on `before_save`, logs every change, and shows a summary notification to the user.

**Built-in rules:**

| Rule | Applies to | What it fixes |
|------|-----------|---------------|
| `CostCenterRule` | Sales Invoice, Purchase Invoice | Sets invoice-level `cost_center`: follows the Project's Default Cost Center if set; falls back to the company's "Projects" cost center if the project has none configured; sets "Main" if no project is assigned |
| `LineItemSyncRule` | Sales Invoice, Purchase Invoice | Ensures all line items match the invoice-level `project` and `cost_center` |
| `DueDateRule` | Purchase Invoice | Enforces a minimum gap between `posting_date` and `due_date` |

**Built-in checks.** A check never changes the document. It either warns (the save goes ahead with a message) or blocks (the save stops until the problem is fixed). Checks run on `validate`.

| Check | Applies to | Severity | What it catches |
|-------|-----------|----------|-----------------|
| `DiscountReasonCheck` | Sales Invoice (on submit) | Block | A discount of $1 or more with no **Discount Reason** filled in |
| `HoursAsQuantityCheck` | Sales Invoice, Purchase Invoice | Warn | An hourly item entered as one lump sum (qty 1, rate over $300) on a project that was invoiced by the hour in the last 90 days |
| `NoCashAccountCheck` | Payment Entry, Journal Entry | Block | Any use of a Cash-type account; 508 holds no cash |
| `DuplicatePaymentCheck` | Payment Entry (on submit) | Block | Another submitted payment with the same party, direction and amount within 7 days, unless **Not a duplicate** is ticked |
| `DueDateCheck` | Sales Invoice | Warn | Due less than 29 days after the invoice date (Purchase Invoices are moved out automatically by `DueDateRule`) |
| `ClientPaidCheck` | Payment Entry (on submit) | Warn | Paying an engineer's bill while the project's client invoice for that period is unpaid |

The checks rely on two custom fields, created on install and on every `migrate`: `Sales Invoice.discount_reason` and `Payment Entry.confirm_not_duplicate`.

---

## Architecture

```
erp_rules/
├── engine.py            # Runs rules and checks, handles errors, notifies user
├── setup.py             # Custom fields the checks rely on
├── handlers/            # Frappe doc_event entry points — declare which rules and checks apply
│   ├── sales_invoice.py
│   ├── purchase_invoice.py
│   ├── payment_entry.py
│   └── journal_entry.py
├── checks/
│   ├── base.py          # BaseCheck abstract class, Problem, WARN / BLOCK
│   ├── discount_reason_check.py
│   ├── due_date_check.py
│   ├── hours_as_quantity_check.py
│   ├── no_cash_account_check.py
│   ├── duplicate_payment_check.py
│   └── client_paid_check.py
├── rules/
│   ├── base.py          # BaseRule abstract class
│   ├── cost_center_rule.py
│   ├── line_item_sync_rule.py
│   └── due_date_rule.py
└── tests/
```

### Adding a new rule

1. Create `erp_rules/rules/my_rule.py` implementing `BaseRule`:

```python
from erp_rules.rules.base import BaseRule

class MyRule(BaseRule):
    def applies_to(self, doc) -> bool:
        return bool(doc.some_field)

    def fix(self, doc) -> list[str]:
        # mutate doc, return list of human-readable change descriptions
        return ["some_field: old → new"]
```

2. Add it to the relevant handler's `RULES` list.

That's it — no changes to existing code.

### Adding a new check

Create `erp_rules/checks/my_check.py` implementing `BaseCheck`, then add it to the relevant handler's `CHECKS` list:

```python
from erp_rules.checks.base import WARN, BaseCheck, Problem

class MyCheck(BaseCheck):
    def applies_to(self, doc) -> bool:
        return doc.docstatus == 1

    def problems(self, doc) -> list[Problem]:
        return [Problem(WARN, "Explain what looks wrong and what to do about it.")]
```

---

## Installation

```bash
bench get-app erp_rules <repo-url>
bench --site <your-site> install-app erp_rules
bench --site <your-site> migrate
```

---

## Configuration

**`DueDateRule` minimum days** — edit `rules/due_date_rule.py`:

```python
MIN_DUE_DATE_DAYS = 29  # change to suit your billing policy
```

**Disabling a rule for a doctype** — remove it from the relevant handler's `RULES` list.

**Disabling a check** without a code change: list its class name in site config.

```bash
bench --site <your-site> set-config -p erp_rules_disabled_checks '["NoCashAccountCheck"]'
```

---

## Error handling

If a rule or check raises an exception, the engine logs the error and continues — a broken rule or check never blocks a save. Only a check that deliberately reports a `BLOCK` problem stops one. All errors appear in the Frappe error log under the `erp_rules` logger.

---

## Running tests

Tests use `unittest` with `unittest.mock` and run inside the Frappe bench environment.

```bash
bench --site <your-site> run-tests --app erp_rules
```

---

## License

MIT — see [license.txt](license.txt).
