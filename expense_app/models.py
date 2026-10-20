"""不可变领域数据模型。金额始终使用整数分。"""
from dataclasses import dataclass

CATEGORIES = ("餐饮", "交通", "学习", "购物", "娱乐", "其他")


@dataclass(frozen=True)
class Expense:
    id: int
    expense_date: str
    category: str
    amount_cents: int
    note: str


@dataclass(frozen=True)
class MonthReport:
    records: tuple[Expense, ...]
    total_cents: int
    category_totals: dict[str, int]


@dataclass(frozen=True)
class BudgetStatus:
    budget_cents: int | None
    spent_cents: int
    remaining_cents: int | None
    level: str  # unset / normal / near / exhausted / over


def format_amount(cents: int) -> str:
    return f"{cents // 100}.{cents % 100:02d}"
