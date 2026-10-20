"""中文桌面界面；输入错误与数据库错误通过对话框可见。"""
from datetime import date

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QDateEdit, QFormLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from .models import CATEGORIES, format_amount
from .repository import StorageError
from .service import ValidationError


class ExpenseWindow(QMainWindow):
    def __init__(self, service):
        super().__init__()
        self.service = service
        self.selected_id = None
        self._records = {}
        self.setWindowTitle("校园消费记账")
        self.resize(1000, 740)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        title = QLabel("校园消费记账")
        title.setStyleSheet("font-size: 26px; font-weight: bold; color: #245d96;")
        layout.addWidget(title)
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("查看月份"))
        self.month_edit = QDateEdit()
        self.month_edit.setDisplayFormat("yyyy-MM")
        self.month_edit.setDateRange(QDate(1900, 1, 1), QDate(2100, 12, 31))
        today = date.today()
        self.month_edit.setDate(QDate(today.year, today.month, 1))
        toolbar.addWidget(self.month_edit)
        self.refresh_button = QPushButton("刷新流水")
        toolbar.addWidget(self.refresh_button)
        toolbar.addStretch()
        self.total_label = QLabel()
        toolbar.addWidget(self.total_label)
        layout.addLayout(toolbar)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["日期", "分类", "金额（元）", "备注", "记录编号"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnHidden(4, True)
        layout.addWidget(self.table)
        self.stats_label = QLabel()
        self.stats_label.setWordWrap(True)
        layout.addWidget(self.stats_label)

        box = QGroupBox("消费记录")
        form = QFormLayout(box)
        self.form_state_label = QLabel("新增模式")
        form.addRow(self.form_state_label)
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDateRange(QDate(1900, 1, 1), QDate(2100, 12, 31))
        self.category_combo = QComboBox()
        self.category_combo.addItems(CATEGORIES)
        self.amount_edit = QLineEdit()
        self.amount_edit.setMaxLength(20)
        self.amount_edit.setPlaceholderText("例如 12.50；范围 0.01～999999.99")
        self.note_edit = QTextEdit()
        self.note_edit.setPlaceholderText("可选，最多 200 个字符")
        self.note_edit.setMaximumHeight(70)
        form.addRow("消费日期", self.date_edit)
        form.addRow("分类", self.category_combo)
        form.addRow("金额（元）", self.amount_edit)
        form.addRow("备注", self.note_edit)
        buttons = QHBoxLayout()
        self.save_button = QPushButton("新增记录")
        self.new_button = QPushButton("取消编辑 / 清空")
        self.delete_button = QPushButton("删除所选记录")
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.new_button)
        buttons.addWidget(self.delete_button)
        form.addRow(buttons)
        layout.addWidget(box)
        self.status_label = QLabel("就绪")
        self.status_label.setWordWrap(True)
        self.status_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status_label)
        self.month_edit.dateChanged.connect(self.month_changed)
        self.refresh_button.clicked.connect(self.refresh)
        self.table.itemSelectionChanged.connect(self.load_selection)
        self.save_button.clicked.connect(self.save_record)
        self.new_button.clicked.connect(self.reset_form)
        self.delete_button.clicked.connect(self.delete_record)
        self.reset_form()
        self.refresh()

    def current_month(self):
        return self.month_edit.date().toString("yyyy-MM")

    def show_error(self, error):
        self.status_label.setText(str(error))
        QMessageBox.warning(self, "操作未完成", str(error))

    def reset_form(self):
        # 清除选择会发出 itemSelectionChanged；暂时屏蔽以避免再次重置表单。
        was_blocked = self.table.blockSignals(True)
        try:
            self.table.clearSelection()
        finally:
            self.table.blockSignals(was_blocked)
        self.selected_id = None
        self.form_state_label.setText("新增模式（选择流水中的一条记录可编辑）")
        self.save_button.setText("新增记录")
        self.delete_button.setEnabled(False)
        month = self.month_edit.date()
        today = date.today()
        if month.year() == today.year and month.month() == today.month:
            self.date_edit.setDate(QDate(today.year, today.month, today.day))
        else:
            self.date_edit.setDate(QDate(month.year(), month.month(), 1))
        self.category_combo.setCurrentIndex(0)
        self.amount_edit.clear()
        self.note_edit.clear()

    def month_changed(self):
        self.refresh()

    def refresh(self) -> bool:
        self.reset_form()
        try:
            report = self.service.month_report(self.current_month())
        except (StorageError, ValidationError) as exc:
            self._records = {}
            self.table.setRowCount(0)
            self.total_label.setText("月总支出：读取失败")
            self.stats_label.setText("分类统计：读取失败")
            self.show_error(exc)
            return False
        self.table.blockSignals(True)
        try:
            self.table.setRowCount(len(report.records))
            self._records = {record.id: record for record in report.records}
            for row, record in enumerate(report.records):
                values = (record.expense_date, record.category, format_amount(record.amount_cents), record.note, str(record.id))
                for column, text in enumerate(values):
                    item = QTableWidgetItem(text)
                    item.setData(Qt.ItemDataRole.UserRole, record.id)
                    self.table.setItem(row, column, item)
        finally:
            self.table.blockSignals(False)
        self.total_label.setText(f"月总支出：¥ {format_amount(report.total_cents)}")
        self.stats_label.setText("分类统计：" + "　".join(f"{category} ¥{format_amount(total)}" for category, total in report.category_totals.items()))
        self.status_label.setText(f"{self.current_month()} 共 {len(report.records)} 条记录；当前为新增模式。")
        return True

    def load_selection(self):
        selected = self.table.selectedItems()
        if not selected:
            self.reset_form()
            return
        record = self._records.get(selected[0].data(Qt.ItemDataRole.UserRole))
        if record is None:
            return
        self.selected_id = record.id
        self.date_edit.setDate(QDate.fromString(record.expense_date, "yyyy-MM-dd"))
        self.category_combo.setCurrentText(record.category)
        self.amount_edit.setText(format_amount(record.amount_cents))
        self.note_edit.setPlainText(record.note)
        self.form_state_label.setText(f"编辑模式 · 记录 #{record.id}")
        self.save_button.setText("保存修改")
        self.delete_button.setEnabled(True)

    def save_record(self):
        day = self.date_edit.date().toString("yyyy-MM-dd")
        args = (day, self.category_combo.currentText(), self.amount_edit.text(), self.note_edit.toPlainText())
        editing = self.selected_id is not None
        try:
            if editing:
                self.service.update_expense(self.selected_id, *args)
            else:
                self.service.add_expense(*args)
        except (StorageError, ValidationError) as exc:
            self.show_error(exc)
            return
        self.month_edit.blockSignals(True)
        self.month_edit.setDate(QDate.fromString(day[:7] + "-01", "yyyy-MM-dd"))
        self.month_edit.blockSignals(False)
        if self.refresh():
            self.status_label.setText("修改已保存。" if editing else "消费记录已新增。")
        else:
            self.status_label.setText(
                f"写入已完成，但刷新失败：{self.status_label.text()} 请点击“刷新流水”重试，无需重复保存。"
            )

    def delete_record(self):
        if self.selected_id is None:
            self.show_error(ValidationError("请先选择一条记录。"))
            return
        expense_id = self.selected_id
        answer = QMessageBox.question(
            self, "确认删除", f"确定永久删除记录 #{expense_id} 吗？此操作不能撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.service.delete_expense(expense_id)
        except (StorageError, ValidationError) as exc:
            self.show_error(exc)
            return
        if self.refresh():
            self.status_label.setText("记录已删除。")
        else:
            self.status_label.setText(
                f"写入已完成，但刷新失败：{self.status_label.text()} 请点击“刷新流水”重试，无需重复删除。"
            )
