import sqlite3

import pytest

from expense_app.models import CATEGORIES, format_amount
from expense_app.repository import ExpenseRepository, StorageError
from expense_app.service import (ExpenseService, ValidationError, month_bounds,
                                 parse_amount, validate_date, validate_id, validate_record)


@pytest.fixture
def repository(tmp_path):
    return ExpenseRepository(tmp_path / "isolated.sqlite3")


@pytest.fixture
def service(repository):
    return ExpenseService(repository)


@pytest.mark.parametrize("value,cents", [("0.01", 1), ("999999.99", 99999999),
    ("0.10", 10), ("0.29", 29), ("12", 1200), ("12.3", 1230), (" 12.30 ", 1230), ("000001", 100)])
def test_amount_exact_valid(value, cents):
    assert parse_amount(value) == cents
    assert parse_amount(format_amount(cents)) == cents


@pytest.mark.parametrize("value", ["", "0", "0.00", "-1", "1.001", "1000000", "1000000.00",
    "1e2", "NaN", "Infinity", "1,000", ".5", "1.", "+1", "１２", "1\n2", None, True, 1.2])
def test_amount_invalid(value):
    with pytest.raises(ValidationError): parse_amount(value)


@pytest.mark.parametrize("day", ["1900-01-01", "2100-12-31", "2000-02-29", "2024-02-29"])
def test_date_valid(day):
    assert validate_date(day) == day


@pytest.mark.parametrize("day", ["1899-12-31", "2101-01-01", "1900-02-29", "2100-02-29",
    "2026-02-30", "2026-13-01", "2026-1-01", "20261001", "", None])
def test_date_invalid(day):
    with pytest.raises(ValidationError): validate_date(day)


@pytest.mark.parametrize("month,start,end", [("2026-02", "2026-02-01", "2026-03-01"),
    ("2024-02", "2024-02-01", "2024-03-01"), ("2026-12", "2026-12-01", "2027-01-01"),
    ("1900-01", "1900-01-01", "1900-02-01"), ("2100-12", "2100-12-01", "2101-01-01")])
def test_month_bounds(month, start, end):
    assert month_bounds(month) == (start, end)


@pytest.mark.parametrize("month", ["2026-00", "2026-13", "2026-1", "1899-12", "2101-01", "", None])
def test_month_invalid(month):
    with pytest.raises(ValidationError): month_bounds(month)


@pytest.mark.parametrize("expense_id", [0, -1, True, 1.2, "1", None, 2**63])
def test_invalid_id(expense_id):
    with pytest.raises(ValidationError): validate_id(expense_id)


@pytest.mark.parametrize("note", ["中文备注", "x' ; DROP TABLE expenses; --", "中文\n制表\t备注", "字" * 200])
def test_notes_preserved_and_sql_safe(service, note):
    identifier = service.add_expense("2026-10-01", "学习", "0.29", note)
    report = service.month_report("2026-10")
    assert report.records[0].id == identifier and report.records[0].note == note
    assert report.total_cents == 29
    assert service.add_expense("2026-10-02", "餐饮", "1.00") > identifier


@pytest.mark.parametrize("category,note", [("无效分类", ""), ("餐饮", "字" * 201),
    ("餐饮", "含\x00空字符"), ("餐饮", "\x1b控制"), ("餐饮", None)])
def test_invalid_record(category, note):
    with pytest.raises(ValidationError): validate_record("2026-10-01", category, "1", note)


def test_crud_persists_between_repository_instances(service, repository):
    first = service.add_expense("2026-10-01", "餐饮", "0.10", "早餐")
    second = service.add_expense("2026-10-02", "交通", "0.20", "车费")
    reopened = ExpenseService(ExpenseRepository(repository.db_path))
    report = reopened.month_report("2026-10")
    assert [r.id for r in report.records] == [second, first]
    assert report.total_cents == 30
    assert report.category_totals["餐饮"] == 10 and report.category_totals["交通"] == 20
    assert set(report.category_totals) == set(CATEGORIES)
    reopened.update_expense(first, "2026-11-01", "学习", "1.23", "  新备注  ")
    assert service.month_report("2026-10").total_cents == 20
    moved = service.month_report("2026-11").records[0]
    assert (moved.amount_cents, moved.note, moved.category) == (123, "新备注", "学习")
    service.delete_expense(first)
    assert reopened.month_report("2026-11").records == ()


def test_month_exact_inclusive_exclusive_bounds_and_order(service):
    service.add_expense("2026-09-30", "其他", "100")
    first = service.add_expense("2026-10-01", "餐饮", "1")
    second = service.add_expense("2026-10-31", "交通", "2")
    third = service.add_expense("2026-10-31", "学习", "3")
    service.add_expense("2026-11-01", "购物", "100")
    report = service.month_report("2026-10")
    assert report.total_cents == 600
    assert [record.id for record in report.records] == [third, second, first]
    service.add_expense("2100-12-31", "其他", "9.99")
    assert service.month_report("2100-12").total_cents == 999


def test_empty_month_and_nonexistent_ids(service):
    report = service.month_report("2026-10")
    assert report.records == () and report.total_cents == 0
    assert all(value == 0 for value in report.category_totals.values())
    with pytest.raises(ValidationError, match="不存在"):
        service.update_expense(999, "2026-10-01", "学习", "1")
    with pytest.raises(ValidationError, match="不存在"): service.delete_expense(999)


def test_repository_failed_constraint_write_rolls_back(repository):
    identifier = repository.add("2026-10-01", "学习", 100, "before")
    with pytest.raises(StorageError): repository.add("2026-10-02", "不存在", 100, "bad")
    with pytest.raises(StorageError): repository.update(identifier, "2026-10-01", "学习", 0, "bad")
    records = repository.list_month("2026-10-01", "2026-11-01")
    assert len(records) == 1 and records[0].note == "before" and records[0].amount_cents == 100
    assert repository.add("2026-10-02", "餐饮", 200, "after") > identifier


def test_multi_statement_transaction_rolls_back(repository):
    with pytest.raises(sqlite3.IntegrityError):
        with repository._connect() as connection:
            connection.execute("INSERT INTO expenses(expense_date,category,amount_cents,note) VALUES ('2026-10-01','餐饮',100,'first')")
            connection.execute("INSERT INTO expenses(expense_date,category,amount_cents,note) VALUES ('2026-10-02','无效',100,'second')")
    assert repository.list_month("2026-10-01", "2026-11-01") == ()


@pytest.mark.parametrize("operation", ["read", "add", "update", "delete"])
def test_storage_errors_wrapped(repository, operation):
    repository.db_path.write_bytes(b"not a sqlite database")
    with pytest.raises(StorageError):
        if operation == "read": repository.list_month("2026-10-01", "2026-11-01")
        elif operation == "add": repository.add("2026-10-01", "餐饮", 100, "")
        elif operation == "update": repository.update(1, "2026-10-01", "餐饮", 100, "")
        else: repository.delete(1)


def test_repository_initialization_invalid_path(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("blocked", encoding="utf-8")
    with pytest.raises(StorageError): ExpenseRepository(blocker / "db.sqlite3")
