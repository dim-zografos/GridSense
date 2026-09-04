from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field


class Account(BaseModel):
    premise_id: str
    customer_name: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None

class AccountDetail(Account):
    outstanding_balance: Decimal

class Invoice(BaseModel):
    invoice_id: int
    premise_id: str
    amount: Decimal
    status: str
    due_date: date

class InvoiceCreate(BaseModel):
    premise_id: str
    amount: Decimal = Field(gt=0)
    status: Literal["UNPAID", "PAID"] = "UNPAID"
    due_date: date