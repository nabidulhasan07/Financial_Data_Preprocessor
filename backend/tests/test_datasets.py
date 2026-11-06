from io import BytesIO

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_csv_upload_clean_validate_analyze_and_export() -> None:
    csv_data = (
        "date,amount,type,category\n"
        "2024-01-02,100,Income,Salary\n"
        "2024-01-03,-25,Expense,Food\n"
        "2024-01-04,,Expense,Food\n"
        "not-a-date,abc,Expense,Food\n"
        "2024-01-02,100,Income,Salary\n"
    )
    uploaded = client.post(
        "/api/datasets",
        files={"file": ("transactions.csv", csv_data, "text/csv")},
    )
    assert uploaded.status_code == 200
    dataset = uploaded.json()
    dataset_id = dataset["dataset_id"]
    assert dataset["row_count"] == 5
    assert dataset["analysis"]["total_income"] == 200
    assert dataset["analysis"]["total_expenses"] == 25
    assert dataset["analysis"]["average_transaction"] == 75
    assert dataset["analysis"]["duplicate_records"] == 1
    assert dataset["analysis"]["missing_values"] == 1
    assert dataset["validation"]["count"] == 2
    assert {item["month"] for item in dataset["analysis"]["monthly_summary"]} == {"2024-01"}
    category_totals = {item["category"]: item for item in dataset["analysis"]["category_summary"]}
    assert category_totals["Salary"]["income"] == 200
    assert category_totals["Food"]["expenses"] == 25

    cleaned = client.post(
        f"/api/datasets/{dataset_id}/clean",
        json={
            "missing_strategy": "fill_zero",
            "remove_duplicates": True,
            "standardize_dates": True,
            "coerce_invalid_numbers": True,
        },
    )
    assert cleaned.status_code == 200
    result = cleaned.json()
    assert result["cleaned"] is True
    assert result["row_count"] == 4
    assert result["cleaning_summary"]["duplicates_removed"] == 1
    assert result["cleaning_summary"]["numbers_coerced"] == 1
    assert result["analysis"]["missing_values"] == 0
    assert result["preview"][0]["date"] == "2024-01-02"

    validation = client.get(f"/api/datasets/{dataset_id}/validation")
    assert validation.status_code == 200
    assert validation.json()["count"] == 1
    analysis = client.get(f"/api/datasets/{dataset_id}/analysis")
    assert analysis.status_code == 200
    assert analysis.json()["total_income"] == 100

    csv_export = client.get(f"/api/datasets/{dataset_id}/export?format=csv")
    assert csv_export.status_code == 200
    assert "transactions_cleaned.csv" in csv_export.headers["content-disposition"]
    assert len(pd.read_csv(BytesIO(csv_export.content))) == 4

    excel_export = client.get(f"/api/datasets/{dataset_id}/export?format=xlsx")
    assert excel_export.status_code == 200
    assert len(pd.read_excel(BytesIO(excel_export.content))) == 4

    report = client.get(f"/api/datasets/{dataset_id}/quality")
    assert report.status_code == 200
    assert report.json()["row_count"] == 4


def test_excel_upload_and_unsupported_format() -> None:
    output = BytesIO()
    pd.DataFrame({"Date": ["2024-04-01"], "Amount": [42], "Type": ["Income"]}).to_excel(output, index=False)
    response = client.post(
        "/api/datasets",
        files={"file": ("ledger.xlsx", output.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 200
    assert response.json()["analysis"]["total_income"] == 42

    rejected = client.post("/api/datasets", files={"file": ("notes.txt", "not data", "text/plain")})
    assert rejected.status_code == 415


def test_negative_income_is_flagged_but_negative_expense_is_allowed() -> None:
    csv_data = "date,amount,type\n2024-02-01,-15,Income\n2024-02-02,-15,Expense\n"
    uploaded = client.post("/api/datasets", files={"file": ("signs.csv", csv_data, "text/csv")})
    assert uploaded.status_code == 200

    issues = uploaded.json()["validation"]["issues"]
    assert len(issues) == 1
    assert issues[0]["row"] == 1
    assert "negative amount" in issues[0]["message"]


def test_txn007_missing_restaurant_amount_all_strategies() -> None:
    csv_data = (
        "transaction_id,date,description,category,type,amount,payment_method\n"
        "TXN001,2026-10-01,Monthly salary,Salary,Income,35000,Bank Transfer\n"
        "TXN002,2026-10-02,Grocery shopping,Groceries,Expense,1850.5,UPI\n"
        "TXN003,2026-10-03,Freelance project,Freelance,Income,5000,Bank Transfer\n"
        "TXN004,2026-10-04,Electricity bill,Utilities,Expense,1250,UPI\n"
        "TXN005,2026-10-05,Bus and metro,Transport,Expense,320,Cash\n"
        "TXN006,2026-10-06,Online course refund,Refund,Income,799,UPI\n"
        "TXN007,2026-10-07,Restaurant,Food,Expense,—,Card\n"
        "TXN008,2026-10-08,Mobile recharge,Utilities,Expense,399,UPI\n"
        "TXN009,2026-10-09,Monthly salary,Salary,Income,35000,Bank Transfer\n"
        "TXN010,2026-10-10,Books,Education,Expense,650,Card\n"
    )
    expected_fills = {
        "keep": None,
        "fill_zero": 0,
        "fill_mean": 80268.5 / 9,
        "fill_median": 1250,
    }

    for strategy, expected_amount in expected_fills.items():
        uploaded = client.post(
            "/api/datasets",
            files={"file": ("dummy_financial_data.csv", csv_data, "text/csv")},
        )
        assert uploaded.status_code == 200
        dataset = uploaded.json()
        assert dataset["analysis"]["missing_values"] == 1
        assert dataset["analysis"]["missing_amounts"] == 1
        assert dataset["analysis"]["unknown_amounts"] == 1
        assert dataset["analysis"]["total_income"] == 75799
        assert dataset["analysis"]["total_expenses"] == 4469.5
        food_summary = next(item for item in dataset["analysis"]["category_summary"] if item["category"] == "Food")
        assert food_summary["expenses"] is None
        assert "not treated as zero" in dataset["analysis"]["calculation_note"]

        cleaned = client.post(
            f"/api/datasets/{dataset['dataset_id']}/clean",
            json={
                "missing_strategy": strategy,
                "remove_duplicates": False,
                "standardize_dates": True,
                "coerce_invalid_numbers": True,
            },
        )
        assert cleaned.status_code == 200
        result = cleaned.json()
        restaurant = next(row for row in result["preview"] if row["transaction_id"] == "TXN007")
        stats = result["cleaning_summary"]
        if expected_amount is None:
            assert restaurant["amount"] is None
            assert stats["missing_amounts_filled"] == 0
            assert stats["missing_amounts_remaining"] == 1
            assert result["analysis"]["unknown_amounts"] == 1
            assert result["analysis"]["total_expenses"] == 4469.5
        else:
            assert restaurant["amount"] == pytest.approx(expected_amount)
            assert stats["missing_amounts_filled"] == 1
            assert stats["missing_amounts_remaining"] == 0
            assert stats["missing_values_handled"] == 1
            assert result["analysis"]["unknown_amounts"] == 0

        assert stats["missing_values_detected"] == 1
        assert stats["missing_values_filled"] == (1 if expected_amount is not None else 0)
