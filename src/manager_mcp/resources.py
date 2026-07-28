"""Curated Manager.io resource allowlist (collections + report shortcuts)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ResourceDescriptor:
    name: str
    kind: str  # "collection" | "report"
    path: str
    description: str
    supports_form: bool = False
    form_path_template: str | None = None  # e.g. "/customer-form/{key}"
    items_key: str | None = None  # envelope key in list GET responses
    date_params: tuple[str, ...] = field(default_factory=tuple)


# Paths validated against live OpenAPI (desktop /api2, 2026-07-28).
_RESOURCES: dict[str, ResourceDescriptor] = {
    "customers": ResourceDescriptor(
        "customers",
        "collection",
        "/customers",
        "Customers collection (search, page, fetch by key)",
        supports_form=True,
        form_path_template="/customer-form/{key}",
        items_key="customers",
    ),
    "suppliers": ResourceDescriptor(
        "suppliers",
        "collection",
        "/suppliers",
        "Suppliers collection (search, page, fetch by key)",
        supports_form=True,
        form_path_template="/supplier-form/{key}",
        items_key="suppliers",
    ),
    "sales_invoices": ResourceDescriptor(
        "sales_invoices",
        "collection",
        "/sales-invoices",
        "Sales invoices collection",
        supports_form=True,
        form_path_template="/sales-invoice-form/{key}",
        items_key="salesInvoices",
    ),
    "purchase_invoices": ResourceDescriptor(
        "purchase_invoices",
        "collection",
        "/purchase-invoices",
        "Purchase invoices collection",
        supports_form=True,
        form_path_template="/purchase-invoice-form/{key}",
        items_key="purchaseInvoices",
    ),
    "chart_of_accounts": ResourceDescriptor(
        "chart_of_accounts",
        "collection",
        "/chart-of-accounts",
        "Chart of accounts collection (list/search only; no single form endpoint)",
        supports_form=False,
        items_key="chartOfAccounts",
    ),
    "bank_accounts": ResourceDescriptor(
        "bank_accounts",
        "collection",
        "/bank-and-cash-accounts",
        "Bank/cash accounts collection for search and drill-in "
        "(distinct from bank_balances snapshot)",
        supports_form=True,
        form_path_template="/bank-or-cash-account-form/{key}",
        items_key="bankAndCashAccounts",
    ),
    # Reports: Manager "*-form" report builders require POST (writes). v1 uses
    # GET-only equivalents validated live — customers/suppliers AR/AP fields,
    # bank-and-cash list balances, and *-transactions statement feeds.
    "aged_receivables": ResourceDescriptor(
        "aged_receivables",
        "report",
        "/customers",
        "Outstanding customer balances (from customers list; no POST aged-receivables-form)",
        items_key="customers",
    ),
    "aged_payables": ResourceDescriptor(
        "aged_payables",
        "report",
        "/suppliers",
        "Outstanding supplier balances (from suppliers list; no POST aged-payables-form)",
        items_key="suppliers",
    ),
    "bank_balances": ResourceDescriptor(
        "bank_balances",
        "report",
        "/bank-and-cash-accounts",
        "Bank/cash balances snapshot (distinct from bank_accounts collection drill-in)",
        items_key="bankAndCashAccounts",
    ),
    "trial_balance": ResourceDescriptor(
        "trial_balance",
        "report",
        "/trial-balance-transactions",
        "Trial balance snapshot (transactions feed)",
        items_key="trialBalanceTransactions",
        date_params=("fromDate", "toDate"),
    ),
    "profit_and_loss": ResourceDescriptor(
        "profit_and_loss",
        "report",
        "/profit-and-loss-statement-transactions",
        "Profit and loss snapshot (transactions feed)",
        items_key="profitAndLossStatementTransactions",
        date_params=("fromDate", "toDate"),
    ),
    "balance_sheet": ResourceDescriptor(
        "balance_sheet",
        "report",
        "/balance-sheet-transactions",
        "Balance sheet snapshot (transactions feed)",
        items_key="balanceSheetTransactions",
        date_params=("fromDate", "toDate"),
    ),
    "tax_summary": ResourceDescriptor(
        "tax_summary",
        "report",
        "/tax-summary-transactions",
        "Tax summary snapshot (transactions feed)",
        items_key="taxSummaryTransactions",
    ),
}


def resolve(name: str) -> ResourceDescriptor | None:
    return _RESOURCES.get(name)


def all_resources() -> list[ResourceDescriptor]:
    return list(_RESOURCES.values())


def form_path(name: str, key: str) -> str | None:
    desc = resolve(name)
    if desc is None or not desc.supports_form or not desc.form_path_template:
        return None
    return desc.form_path_template.replace("{key}", key)


def extract_items(desc: ResourceDescriptor, body: object) -> list[object]:
    """Unwrap Manager list envelopes into a flat items list."""
    if body is None:
        return []
    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        if desc.items_key and isinstance(body.get(desc.items_key), list):
            return body[desc.items_key]
        if isinstance(body.get("items"), list):
            return body["items"]
    return [body]
