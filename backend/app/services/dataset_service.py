from __future__ import annotations

import math
import re
from typing import Any

import numpy as np
import pandas as pd


DATE_NAMES = ("date", "time", "posted", "transaction date", "period")
AMOUNT_NAMES = ("amount", "value", "total", "transaction amount", "net", "debit", "credit")
TYPE_NAMES = ("type", "direction", "transaction type", "kind")
CATEGORY_NAMES = ("category", "description", "merchant", "account", "label")
INCOME_WORDS = {"income", "credit", "deposit", "revenue", "salary", "inflow"}
EXPENSE_WORDS = {"expense", "debit", "withdrawal", "payment", "cost", "outflow"}
MISSING_TOKENS = {"", "na", "n/a", "null", "none", "nan", "-", "–", "—"}


def _missing_mask(series: pd.Series) -> pd.Series:
    tokens = series.astype("string").str.strip().str.casefold()
    return series.isna() | tokens.isin(MISSING_TOKENS).fillna(False)


def normalize_missing_values(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    for column in normalized.columns:
        mask = _missing_mask(normalized[column])
        if mask.any():
            normalized[column] = normalized[column].mask(mask, np.nan)
    return normalized


def missing_value_count(frame: pd.DataFrame) -> int:
    return sum(int(_missing_mask(frame[column]).sum()) for column in frame.columns)


def _column(frame: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    normalized = {re.sub(r"[^a-z0-9 ]", "", str(column).lower()).strip(): column for column in frame.columns}
    for candidate in candidates:
        for key, original in normalized.items():
            if key == candidate or key.endswith(f" {candidate}") or candidate in key:
                return str(original)
    return None


def detect_columns(frame: pd.DataFrame) -> dict[str, str | None]:
    return {
        "date": _column(frame, DATE_NAMES),
        "amount": _column(frame, AMOUNT_NAMES),
        "type": _column(frame, TYPE_NAMES),
        "category": _column(frame, CATEGORY_NAMES),
    }


def _native(value: Any) -> Any:
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return pd.Timestamp(value).isoformat()
    if pd.isna(value):
        return None
    return str(value) if not isinstance(value, (str,)) else value


def frame_records(frame: pd.DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    source = frame if limit is None else frame.head(limit)
    return [{str(key): _native(value) for key, value in row.items()} for row in source.to_dict(orient="records")]


def _money(frame: pd.DataFrame, columns: dict[str, str | None]) -> pd.Series:
    column = columns["amount"]
    if not column:
        return pd.Series(np.nan, index=frame.index, dtype="float64")
    values = frame[column].astype("string").str.strip()
    values = values.mask(values.str.casefold().isin(MISSING_TOKENS))
    return pd.to_numeric(values.str.replace(r"[$,£€\s]", "", regex=True), errors="coerce")


def validation(frame: pd.DataFrame) -> dict[str, Any]:
    columns = detect_columns(frame)
    issues: list[dict[str, Any]] = []
    amount_column = columns["amount"]
    date_column = columns["date"]
    if amount_column:
        amounts = _money(frame, columns)
        raw_nonempty = ~_missing_mask(frame[amount_column])
        for position, index in enumerate(frame.index):
            if raw_nonempty.loc[index] and pd.isna(amounts.loc[index]):
                issues.append({"row": position + 1, "column": amount_column, "message": "Amount is not a valid number.", "value": _native(frame.loc[index, amount_column])})
    if date_column:
        parsed = pd.to_datetime(frame[date_column], errors="coerce", format="mixed")
        raw_nonempty = ~_missing_mask(frame[date_column])
        for position, index in enumerate(frame.index):
            if raw_nonempty.loc[index] and pd.isna(parsed.loc[index]):
                issues.append({"row": position + 1, "column": date_column, "message": "Date could not be recognized.", "value": _native(frame.loc[index, date_column])})
    type_column = columns["type"]
    if amount_column and type_column:
        amounts = _money(frame, columns)
        labels = frame[type_column].astype("string").str.lower().str.strip()
        for position, index in enumerate(frame.index):
            if labels.loc[index] in INCOME_WORDS and pd.notna(amounts.loc[index]) and amounts.loc[index] < 0:
                issues.append({"row": position + 1, "column": amount_column, "message": "Income transactions should not have a negative amount.", "value": _native(frame.loc[index, amount_column])})
    return {"count": len(issues), "issues": issues[:500], "truncated": len(issues) > 500, "detected_columns": columns}


def analysis(frame: pd.DataFrame) -> dict[str, Any]:
    columns = detect_columns(frame)
    amount_col = columns["amount"]
    amounts = _money(frame, columns)
    income = pd.Series(False, index=frame.index)
    expense = pd.Series(False, index=frame.index)
    if columns["type"]:
        labels = frame[columns["type"]].astype("string").str.lower().str.strip()
        income = labels.isin(INCOME_WORDS)
        expense = labels.isin(EXPENSE_WORDS)
    income |= ~expense & ~income & amounts.gt(0)
    expense |= ~expense & ~income & amounts.lt(0)
    total_income = float(amounts[income].abs().sum()) if amount_col else 0.0
    total_expenses = float(amounts[expense].abs().sum()) if amount_col else 0.0
    valid_amounts = amounts.dropna().abs()

    categories: list[dict[str, Any]] = []
    category_col = columns["category"]
    if category_col and amount_col:
        category_values = frame[category_col].fillna("Uncategorized").astype(str).replace("", "Uncategorized")
        income_values = amounts.abs().where(income, 0).mask(amounts.isna())
        expense_values = amounts.abs().where(expense, 0).mask(amounts.isna())
        grouped = pd.DataFrame({"category": category_values, "income": income_values, "expenses": expense_values})
        category_totals = grouped.groupby("category", dropna=False)[["income", "expenses"]].sum(numeric_only=True, min_count=1)
        categories = [{"category": str(name), "income": _native(row["income"]), "expenses": _native(row["expenses"])} for name, row in category_totals.sort_values("income", ascending=False, na_position="last").head(30).iterrows()]

    monthly: list[dict[str, Any]] = []
    if columns["date"] and amount_col:
        dates = pd.to_datetime(frame[columns["date"]], errors="coerce", format="mixed")
        income_values = amounts.abs().where(income, 0).mask(amounts.isna())
        expense_values = amounts.abs().where(expense, 0).mask(amounts.isna())
        grouped = pd.DataFrame({"month": dates.dt.to_period("M").astype("string"), "income": income_values, "expenses": expense_values}).dropna(subset=["month"])
        monthly_totals = grouped.groupby("month").sum(numeric_only=True, min_count=1).sort_index().tail(36)
        monthly = [{"month": str(name), "income": _native(row["income"]), "expenses": _native(row["expenses"])} for name, row in monthly_totals.iterrows()]
    return {
        "total_transactions": int(len(frame)),
        "total_income": total_income,
        "total_expenses": total_expenses,
        "average_transaction": float(valid_amounts.mean()) if len(valid_amounts) else None,
        "missing_values": missing_value_count(frame),
        "missing_amounts": int(_missing_mask(frame[amount_col]).sum()) if amount_col else 0,
        "unknown_amounts": int(amounts.isna().sum()) if amount_col else 0,
        "calculation_note": "Missing and invalid amounts are excluded from totals and averages, not treated as zero.",
        "duplicate_records": int(frame.duplicated().sum()),
        "category_summary": categories,
        "monthly_summary": monthly,
        "detected_columns": columns,
    }


def clean_frame(frame: pd.DataFrame, options: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    cleaned = normalize_missing_values(frame)
    columns = detect_columns(cleaned)
    amount_column = columns["amount"]
    strategy = options["missing_strategy"]
    stats = {
        "missing_strategy": strategy,
        "custom_value": options.get("custom_value") if strategy == "fill_custom" else None,
        "duplicates_removed": 0,
        "rows_removed": 0,
        "dates_standardized": 0,
        "numbers_coerced": 0,
        "missing_values_detected": missing_value_count(cleaned),
        "missing_amounts_detected": int(_missing_mask(cleaned[amount_column]).sum()) if amount_column else 0,
        "missing_values_filled": 0,
        "missing_values_dropped": 0,
        "missing_values_handled": 0,
        "missing_values_remaining": 0,
        "missing_amounts_filled": 0,
        "missing_amounts_dropped": 0,
        "missing_amounts_handled": 0,
        "missing_amounts_remaining": 0,
        "missing_amount_fill_value": None,
    }
    if options["remove_duplicates"]:
        before = len(cleaned)
        cleaned = cleaned.drop_duplicates(keep="first")
        stats["duplicates_removed"] = before - len(cleaned)
    if options["standardize_dates"] and columns["date"]:
        name = columns["date"]
        parsed = pd.to_datetime(cleaned[name], errors="coerce", format="mixed")
        valid = parsed.notna()
        stats["dates_standardized"] = int(valid.sum())
        cleaned[name] = cleaned[name].astype(object)
        cleaned.loc[valid, name] = parsed[valid].dt.strftime("%Y-%m-%d")
    if options["coerce_invalid_numbers"] and columns["amount"]:
        name = columns["amount"]
        before = ~_missing_mask(cleaned[name])
        parsed = _money(cleaned, columns)
        stats["numbers_coerced"] = int((before & parsed.isna()).sum())
        cleaned[name] = parsed

    missing_before_strategy = missing_value_count(cleaned)
    missing_amounts_before_strategy = int(_missing_mask(cleaned[amount_column]).sum()) if amount_column else 0
    stats["missing_values_detected"] += stats["numbers_coerced"]
    stats["missing_amounts_detected"] += stats["numbers_coerced"]
    missing_mask = pd.DataFrame({column: _missing_mask(cleaned[column]) for column in cleaned.columns}, index=cleaned.index)
    missing_amounts_dropped = 0
    amount_fill_value: Any = None

    if strategy == "drop_rows":
        rows_with_missing = missing_mask.any(axis=1)
        stats["rows_removed"] = int(rows_with_missing.sum())
        stats["missing_values_dropped"] = int(missing_mask.where(rows_with_missing, False).to_numpy().sum())
        if amount_column:
            missing_amounts_dropped = int((missing_mask[amount_column] & rows_with_missing).sum())
        cleaned = cleaned.loc[~rows_with_missing]
    elif strategy in {"fill_zero", "fill_mean", "fill_median"}:
        numeric_columns = list(cleaned.select_dtypes(include=["number"]).columns)
        for name in numeric_columns:
            if strategy == "fill_zero":
                fill_value = 0
            elif strategy == "fill_mean":
                fill_value = cleaned[name].mean()
            else:
                fill_value = cleaned[name].median()
            if pd.notna(fill_value):
                cleaned[name] = cleaned[name].fillna(fill_value)
                if name == amount_column:
                    amount_fill_value = float(fill_value)

        # Financial amount columns may be text when numeric coercion is disabled.
        if amount_column and amount_column not in numeric_columns:
            parsed_amounts = _money(cleaned, columns)
            if strategy == "fill_zero":
                fill_value = 0.0
            elif strategy == "fill_mean":
                fill_value = parsed_amounts.mean()
            else:
                fill_value = parsed_amounts.median()
            if pd.notna(fill_value):
                cleaned[amount_column] = cleaned[amount_column].mask(missing_mask[amount_column], float(fill_value))
                amount_fill_value = float(fill_value)

    elif strategy == "fill_mode":
        for name in cleaned.columns:
            missing = missing_mask[name]
            if not missing.any():
                continue
            frequencies = cleaned.loc[~missing, name].value_counts(sort=False, dropna=True)
            if frequencies.empty:
                continue
            fill_value = frequencies.idxmax()
            cleaned[name] = cleaned[name].mask(missing, fill_value)
            if name == amount_column and _finite_number(fill_value) is not None:
                amount_fill_value = float(fill_value)

    elif strategy == "fill_custom":
        custom_value = options.get("custom_value")
        numeric_custom_value: float | None = None
        numeric_columns = set(cleaned.select_dtypes(include=["number"]).columns)
        if amount_column:
            numeric_columns.add(amount_column)
        for name in cleaned.columns:
            missing = missing_mask[name]
            if not missing.any():
                continue
            if name in numeric_columns:
                parsed_custom = pd.to_numeric(custom_value, errors="coerce")
                if pd.isna(parsed_custom) or not math.isfinite(float(parsed_custom)):
                    raise ValueError(f"Custom value must be numeric for the '{name}' column.")
                fill_value = float(parsed_custom)
                if name == amount_column:
                    numeric_custom_value = fill_value
                    amount_fill_value = fill_value
            else:
                fill_value = custom_value
            cleaned[name] = cleaned[name].mask(missing, fill_value)
        if numeric_custom_value is not None:
            stats["custom_numeric_value"] = numeric_custom_value

    if amount_fill_value is not None:
        stats["missing_amount_fill_value"] = amount_fill_value

    missing_after_strategy = missing_value_count(cleaned)
    stats["missing_values_filled"] = max(0, missing_before_strategy - stats["missing_values_dropped"] - missing_after_strategy)
    stats["missing_values_remaining"] = missing_after_strategy
    stats["missing_values_handled"] = stats["missing_values_filled"] + stats["missing_values_dropped"]
    if amount_column:
        stats["missing_amounts_remaining"] = int(_missing_mask(cleaned[amount_column]).sum())
        stats["missing_amounts_dropped"] = missing_amounts_dropped
        stats["missing_amounts_filled"] = max(0, missing_amounts_before_strategy - missing_amounts_dropped - stats["missing_amounts_remaining"])
        stats["missing_amounts_handled"] = stats["missing_amounts_filled"] + stats["missing_amounts_dropped"]
    cleaned = cleaned.reset_index(drop=True)
    return cleaned, stats


def _finite_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None
