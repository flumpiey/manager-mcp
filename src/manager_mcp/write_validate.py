"""Pre-flight validation and persistence diff for hardened writable resources."""

from __future__ import annotations

import copy
from typing import Any

from manager_mcp.writable import WritableResource

_INT_PARTY_KEYS = frozenset({"PaidBy", "Payee", "Payer"})

_RECEIPT_LINE_ALIASES = {
    "SalesInvoice": "AccountsReceivableSalesInvoice",
}
_PAYMENT_LINE_ALIASES = {
    "AccountsPayablePurchaseInvoice": "PurchaseInvoice",
}
_CUSTOM_BUTTON_HEADER_ALIASES = {
    "endpoint": "Endpoint",
    "html": "Html",
    "inactive": "Inactive",
}


def _validate_int_party_keys(resource: WritableResource, fields: dict[str, Any]) -> None:
    for key in _INT_PARTY_KEYS:
        if key not in fields or fields[key] is None:
            continue
        value = fields[key]
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(
                f"{resource.name}: {key} must be int (e.g. 1), not {type(value).__name__}."
            )


def normalize_write_body(
    resource: WritableResource,
    fields: dict[str, Any],
) -> dict[str, Any]:
    """Map legacy MCP field names to Manager-native names before POST/PUT."""
    if not resource.known_keys:
        return fields
    out = copy.deepcopy(fields)
    if resource.name == "receipts":
        line_aliases = _RECEIPT_LINE_ALIASES
    elif resource.name == "payments":
        if "PaidBy" in out and "Payee" not in out:
            out["Payee"] = out.pop("PaidBy")
        elif "PaidBy" in out:
            out.pop("PaidBy", None)
        line_aliases = _PAYMENT_LINE_ALIASES
    elif resource.name == "custom_buttons":
        for old, new in _CUSTOM_BUTTON_HEADER_ALIASES.items():
            if old in out and new not in out:
                out[new] = out.pop(old)
            elif old in out:
                out.pop(old, None)
        if "Text" in out:
            if "Name" not in out and out["Text"]:
                out["Name"] = out["Text"]
            out.pop("Text", None)
        line_aliases = {}
    else:
        line_aliases = {}
    lines = out.get("Lines")
    if isinstance(lines, list) and line_aliases:
        for line in lines:
            if not isinstance(line, dict):
                continue
            for old, new in line_aliases.items():
                if old in line and new not in line:
                    line[new] = line.pop(old)
                elif old in line:
                    line.pop(old, None)
    return out


def validate_write_body(
    resource: WritableResource,
    fields: dict[str, Any],
    *,
    creating: bool,
) -> None:
    """Raise ValueError when body is empty, has unknown keys, or bad types."""
    if not resource.known_keys:
        return
    if not fields:
        raise ValueError(
            f"{resource.name}: empty body rejected. Clone a template via "
            f"get_record then set required fields "
            f"{sorted(resource.required_keys) if resource.required_keys else '(see notes)'}."
        )
    unknown = sorted(set(fields) - resource.known_keys)
    if unknown:
        sample = ", ".join(sorted(resource.known_keys)[:12])
        raise ValueError(
            f"{resource.name}: unknown field(s) {unknown}. "
            f"Manager silently drops wrong names. Known keys include: {sample}, …"
        )
    if creating and resource.required_keys:
        missing = sorted(resource.required_keys - set(fields))
        if missing:
            raise ValueError(
                f"{resource.name}: missing required field(s) {missing}. "
                "Clone get_record template before create."
            )
    _validate_int_party_keys(resource, fields)
    lines = fields.get("Lines")
    if lines is None:
        return
    if not isinstance(lines, list):
        raise ValueError(f"{resource.name}: Lines must be a list.")
    if creating and len(lines) == 0:
        raise ValueError(
            f"{resource.name}: Lines must be non-empty on create "
            "(allocation / AR / AP / bank-charge lines)."
        )
    if not resource.known_line_keys:
        return
    for index, line in enumerate(lines):
        if not isinstance(line, dict):
            raise ValueError(f"{resource.name}: Lines[{index}] must be an object.")
        bad = sorted(set(line) - resource.known_line_keys)
        if bad:
            raise ValueError(
                f"{resource.name}: Lines[{index}] unknown field(s) {bad}. "
                f"Known line keys: {sorted(resource.known_line_keys)}."
            )


def _values_equal(submitted: Any, persisted: Any) -> bool:
    if submitted == persisted:
        return True
    if isinstance(submitted, str) and isinstance(persisted, str):
        if (
            len(submitted) >= 10
            and submitted[:10] == persisted[:10]
            and submitted[:10].count("-") == 2
        ):
            return True
    if isinstance(submitted, (int, float)) and isinstance(persisted, (int, float)):
        return float(submitted) == float(persisted)
    return False


def diff_persisted(
    resource: WritableResource,
    submitted: dict[str, Any],
    persisted: dict[str, Any] | None,
) -> list[str]:
    """Return warnings when submitted known scalars/lines did not stick."""
    if not resource.known_keys or not isinstance(persisted, dict):
        return ["could not verify persistence (no form body returned)"]
    warnings: list[str] = []
    skip = {"Key", "id", "text", "UniqueName", "Lines", "CustomFields", "CustomFields2"}
    for key, value in submitted.items():
        if key in skip or key not in resource.known_keys:
            continue
        if key not in persisted:
            warnings.append(f"{key} missing after save (submitted value may have been dropped)")
            continue
        if not _values_equal(value, persisted.get(key)):
            warnings.append(
                f"{key} differs after save (submitted={value!r}, got={persisted.get(key)!r})"
            )
    if "Lines" not in submitted or not isinstance(submitted["Lines"], list):
        return warnings
    got = persisted.get("Lines")
    if not isinstance(got, list):
        warnings.append("Lines missing after save")
        return warnings
    submitted_lines = submitted["Lines"]
    if len(got) != len(submitted_lines):
        warnings.append(
            f"Lines count differs after save (submitted={len(submitted_lines)}, got={len(got)})"
        )
    if not resource.known_line_keys:
        return warnings
    for index, line in enumerate(submitted_lines):
        if not isinstance(line, dict):
            continue
        got_line = got[index] if index < len(got) and isinstance(got[index], dict) else {}
        for field, value in line.items():
            if field not in resource.known_line_keys:
                continue
            if field not in got_line:
                warnings.append(
                    f"Lines[{index}].{field} missing after save "
                    f"(submitted value may have been dropped)"
                )
                continue
            if not _values_equal(value, got_line.get(field)):
                warnings.append(
                    f"Lines[{index}].{field} differs after save "
                    f"(submitted={value!r}, got={got_line.get(field)!r})"
                )
    return warnings
