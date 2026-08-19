import enum


class Role(str, enum.Enum):
    ADMIN = "admin"
    ACCOUNTANT = "accountant"
    VIEWER = "viewer"


class AccountType(str, enum.Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    INCOME = "income"
    EXPENSE = "expense"


class CfCategory(str, enum.Enum):
    OPERATING = "operating"
    INVESTING = "investing"
    FINANCING = "financing"


class EntryDirection(str, enum.Enum):
    DEBIT = "debit"
    CREDIT = "credit"
