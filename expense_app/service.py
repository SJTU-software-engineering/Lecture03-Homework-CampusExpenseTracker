"""输入校验与月度统计，独立于 Qt。"""
import re
from datetime import date
from decimal import Decimal

from .models import CATEGORIES, MonthReport
from .repository import ExpenseRepository

MIN_DATE = date(1900, 1, 1)
MAX_DATE = date(2100, 12, 31)
MAX_AMOUNT_CENTS = 99_999_999


class ValidationError(Exception):
    """用户可以修正的输入错误。"""


def parse_amount(text: str) -> int:
    if not isinstance(text, str):
        raise ValidationError("金额请输入数字，最多保留两位小数。")
    text = text.strip()
    if not re.fullmatch(r"[0-9]{1,6}(?:\.[0-9]{1,2})?", text):
        raise ValidationError("金额须为 0.01～999999.99 元，最多两位小数，不支持负数或科学计数法。")
    cents = int(Decimal(text) * 100)
    if not 1 <= cents <= MAX_AMOUNT_CENTS:
        raise ValidationError("金额须为 0.01～999999.99 元。")
    return cents


def validate_date(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValidationError("日期格式须为 yyyy-MM-dd。")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError("消费日期无效。") from exc
    if not MIN_DATE <= parsed <= MAX_DATE:
        raise ValidationError("日期须在 1900-01-01 至 2100-12-31 之间。")
    return value


def month_bounds(month: str) -> tuple[str, str]:
    if not isinstance(month, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}", month):
        raise ValidationError("月份格式须为 yyyy-MM。")
    first = validate_date(month + "-01")
    year, number = map(int, month.split("-"))
    following = date(year + (number == 12), 1 if number == 12 else number + 1, 1)
    return first, following.isoformat()


def validate_record(day: str, category: str, amount: str, note: str) -> tuple[str, str, int, str]:
    day = validate_date(day)
    if category not in CATEGORIES:
        raise ValidationError("请选择有效的消费分类。")
    cents = parse_amount(amount)
    if not isinstance(note, str) or len(note) > 200:
        raise ValidationError("备注最多 200 个字符。")
    if any(ord(character) < 32 and character not in "\n\t" for character in note):
        raise ValidationError("备注包含不支持的控制字符。")
    return day, category, cents, note.strip()


def validate_id(expense_id: int) -> None:
    if type(expense_id) is not int or expense_id <= 0 or expense_id > 2**63 - 1:
        raise ValidationError("请先选择一条有效记录。")


class ExpenseService:
    def __init__(self, repository: ExpenseRepository):
        self.repository = repository

    def month_report(self, month: str) -> MonthReport:
        records = self.repository.list_month(*month_bounds(month))
        totals = dict.fromkeys(CATEGORIES, 0)
        for record in records:
            totals[record.category] += record.amount_cents
        return MonthReport(records, sum(totals.values()), totals)

    def add_expense(self, day: str, category: str, amount: str, note: str = "") -> int:
        return self.repository.add(*validate_record(day, category, amount, note))

    def update_expense(self, expense_id: int, day: str, category: str, amount: str, note: str = "") -> None:
        validate_id(expense_id)
        values = validate_record(day, category, amount, note)
        if not self.repository.update(expense_id, *values):
            raise ValidationError("该记录已不存在，请刷新后重试。")

    def delete_expense(self, expense_id: int) -> None:
        validate_id(expense_id)
        if not self.repository.delete(expense_id):
            raise ValidationError("该记录已不存在，请刷新后重试。")
