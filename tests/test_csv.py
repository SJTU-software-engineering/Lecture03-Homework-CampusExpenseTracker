import csv
import os

import pytest
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from expense_app import service as service_module
from expense_app.repository import ExpenseRepository, StorageError
from expense_app.service import ExpenseService, ExportError, ValidationError, filter_records, safe_csv_note
from expense_app.ui import ExpenseWindow


@pytest.fixture
def service(tmp_path):
    instance = ExpenseService(ExpenseRepository(tmp_path / "csv-test.sqlite3"))
    instance.add_expense("2026-10-01", "餐饮", "0.29", '中文,含"引号"\n第二行')
    instance.add_expense("2026-10-02", "学习", "80.00", "=SUM(1,2)")
    instance.add_expense("2026-11-01", "交通", "100", "其他月份")
    instance.set_budget("2026-10", "100")
    return instance


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.reader(handle))


def test_filters_combine_month_category_and_preserve_report(service):
    all_records = service.month_report("2026-10").records
    assert filter_records(all_records) == all_records
    assert filter_records(all_records, "餐饮") == (all_records[1],)
    assert service.filtered_expenses("2026-10", "学习") == (all_records[0],)
    assert service.filtered_expenses("2026-11", "餐饮") == ()
    assert service.filtered_expenses("2026-12") == ()
    with pytest.raises(ValidationError): service.filtered_expenses("2026-10", "无效")
    assert service.month_report("2026-10").total_cents == 8029
    assert service.budget_status("2026-10").level == "near"


@pytest.mark.parametrize("note,expected", [("=1+1", "'=1+1"), ("+SUM(A1)", "'+SUM(A1)"),
    ("-1", "'-1"), ("@SUM(A1)", "'@SUM(A1)"), ("  =1", "'  =1"),
    ("\t+1", "'\t+1"), ("\n@x", "'\n@x"), ("\u3000-1", "'\u3000-1"),
    ("正常中文", "正常中文"), ("", ""), ("备注=说明", "备注=说明"), ("'已有", "'已有")])
def test_formula_guard_including_leading_whitespace(note, expected):
    assert safe_csv_note(note) == expected


def test_csv_bom_chinese_quoting_newlines_amount_and_original_unchanged(service, tmp_path):
    before = service.month_report("2026-10").records
    path = tmp_path / "中文消费.csv"
    assert service.export_csv("2026-10", None, path) == 2
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
    rows = read_csv(path)
    assert rows[0] == ["日期", "分类", "金额（元）", "备注", "记录编号"]
    assert rows[1] == ["2026-10-02", "学习", "80.00", "'=SUM(1,2)", str(before[0].id)]
    assert rows[2] == ["2026-10-01", "餐饮", "0.29", '中文,含"引号"\n第二行', str(before[1].id)]
    assert service.month_report("2026-10").records == before
    assert not list(tmp_path.glob(".expense-export-*.tmp"))


def test_csv_exports_current_category_empty_month_and_overwrites(service, tmp_path):
    path = tmp_path / "filtered.CSV"
    path.write_text("old content", encoding="utf-8")
    assert service.export_csv("2026-10", "餐饮", path) == 1
    assert len(read_csv(path)) == 2 and read_csv(path)[1][1] == "餐饮"
    assert service.export_csv("2026-11", "餐饮", path) == 0
    assert len(read_csv(path)) == 1
    assert service.export_csv("2026-12", None, path) == 0


def test_csv_preserves_legacy_leading_whitespace_note(service, tmp_path):
    identifier = service.repository.add("2026-10-20", "其他", 1, " \t=1+1")
    path = tmp_path / "legacy.csv"
    assert service.export_csv("2026-10", "其他", path) == 1
    assert read_csv(path)[1][3] == "' \t=1+1"
    original = service.month_report("2026-10").records[0]
    assert original.id == identifier and original.note == " \t=1+1"


@pytest.mark.parametrize("bad_name", ["out.txt", "out", "missing/out.csv"])
def test_export_bad_paths(service, tmp_path, bad_name):
    with pytest.raises(ExportError): service.export_csv("2026-10", None, tmp_path / bad_name)
    assert not list(tmp_path.glob(".expense-export-*.tmp"))


@pytest.mark.parametrize("failure_point", ["replace", "fsync", "writer"])
def test_atomic_failure_preserves_original_and_cleans_temp(service, tmp_path, monkeypatch, failure_point):
    path = tmp_path / "existing.csv"
    original = b"existing file must survive unchanged"
    path.write_bytes(original)
    def failure(*args, **kwargs):
        if failure_point == "writer": raise csv.Error("injected writer error")
        raise OSError("injected disk error")
    if failure_point == "writer": monkeypatch.setattr(service_module.csv, "writer", failure)
    else: monkeypatch.setattr(service_module.os, failure_point, failure)
    with pytest.raises(ExportError): service.export_csv("2026-10", None, path)
    assert path.read_bytes() == original
    assert not list(tmp_path.glob(".expense-export-*.tmp"))
    assert service.month_report("2026-10").total_cents == 8029


@pytest.mark.parametrize("alias", [False, True])
def test_csv_database_and_hardlink_alias_never_overwritten(tmp_path, alias):
    database = tmp_path / "database.csv"
    instance = ExpenseService(ExpenseRepository(database))
    instance.add_expense("2026-10-01", "学习", "1", "保留")
    target = tmp_path / "alias.csv" if alias else database
    if alias: os.link(database, target)
    before = database.read_bytes()
    with pytest.raises(ExportError, match="数据库"): instance.export_csv("2026-10", None, target)
    assert database.read_bytes() == before
    assert instance.month_report("2026-10").total_cents == 100
    assert not list(tmp_path.glob(".expense-export-*.tmp"))


@pytest.fixture
def window(app, dialogs, service):
    widget = ExpenseWindow(service)
    widget.month_edit.setDate(QDate(2026, 10, 1))
    widget.show()
    app.processEvents()
    yield widget
    widget.close()
    widget.deleteLater()
    app.processEvents()


def test_ui_filter_resets_selection_but_budget_remains_whole_month(window):
    assert window.table.rowCount() == 2
    window.table.selectRow(0)
    assert window.selected_id is not None
    window.filter_combo.setCurrentText("餐饮")
    assert window.table.rowCount() == 1 and window.table.item(0, 1).text() == "餐饮"
    assert window.selected_id is None and window.amount_edit.text() == "" and not window.delete_button.isEnabled()
    assert "0.29" in window.filtered_total_label.text() and "80.29" in window.total_label.text()
    assert "80.29" in window.budget_label.text() and "接近" in window.budget_warning_label.text()
    window.filter_combo.setCurrentText("娱乐")
    assert window.table.rowCount() == 0 and "80.29" in window.budget_label.text()
    window.month_edit.setDate(QDate(2026, 11, 1))
    assert window.table.rowCount() == 0 and "100.00" in window.total_label.text()
    window.filter_combo.setCurrentIndex(0)
    assert window.table.rowCount() == 1 and "未设置" in window.budget_label.text()


def test_ui_export_cancel_never_calls_export(window, monkeypatch):
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args, **kwargs: ("", ""))
    def forbidden(*args): pytest.fail("cancelled export wrote a file")
    monkeypatch.setattr(window.service, "export_csv", forbidden)
    old_status = window.status_label.text()
    window.export_button.click()
    assert window.status_label.text() == old_status


@pytest.mark.parametrize("confirm", [False, True])
def test_ui_export_existing_file_confirmation(window, tmp_path, monkeypatch, confirm):
    path = tmp_path / "existing.csv"
    path.write_bytes(b"unchanged")
    window.filter_combo.setCurrentText("餐饮")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(path), ""))
    questions = []
    def answer(*args):
        questions.append(args)
        return QMessageBox.StandardButton.Yes if confirm else QMessageBox.StandardButton.No
    monkeypatch.setattr(QMessageBox, "question", answer)
    window.export_button.click()
    assert len(questions) == 1 and questions[0][-1] == QMessageBox.StandardButton.No
    if confirm:
        assert len(read_csv(path)) == 2 and read_csv(path)[1][1] == "餐饮"
        assert "1 条" in window.status_label.text()
    else: assert path.read_bytes() == b"unchanged"


def test_ui_empty_export_produces_header_and_clear_status(window, tmp_path, monkeypatch):
    path = tmp_path / "empty.csv"
    window.filter_combo.setCurrentText("娱乐")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(path), ""))
    window.export_button.click()
    assert len(read_csv(path)) == 1
    assert "0 条" in window.status_label.text() and "仅包含表头" in window.status_label.text()


@pytest.mark.parametrize("error", [ExportError("写出错误测试"), StorageError("读取错误测试"),
                                 ValidationError("范围错误测试"), OSError("路径错误测试")])
def test_ui_export_errors_are_visible(window, tmp_path, dialogs, monkeypatch, error):
    path = tmp_path / "out.csv"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(path), ""))
    def failure(*args): raise error
    monkeypatch.setattr(window.service, "export_csv", failure)
    window.export_button.click()
    assert dialogs[-1] == str(error) and window.status_label.text() == str(error)
    assert not path.exists()
