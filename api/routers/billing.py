from fastapi import APIRouter, HTTPException
from db.postgres import get_pool
from models.postgres import AccountDetail, InvoiceCreate, Invoice


router = APIRouter(prefix="/billing")
@router.get("/account/{premise_id}", response_model=AccountDetail)
async def get_account(premise_id: str):
    pool = get_pool()

    row = await pool.fetchrow(
        """
        SELECT
            a.premise_id,
            a.customer_name,
            a.email,
            a.phone,
            a.address,
            COALESCE(
                SUM(i.amount) FILTER (WHERE i.status = 'UNPAID'),
                0
            ) AS outstanding_balance
        FROM accounts a
        LEFT JOIN invoices i
            ON i.premise_id = a.premise_id
        WHERE a.premise_id = $1
        GROUP BY
            a.premise_id,
            a.customer_name,
            a.email,
            a.phone,
            a.address
        """,
        premise_id
    )

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Account '{premise_id}' not found"
        )

    return dict(row)

@router.post("/invoice", response_model=Invoice, status_code=201)
async def create_invoice(invoice: InvoiceCreate):
    pool = get_pool()

    async with pool.acquire() as connection:
        async with connection.transaction():
            account_exists = await connection.fetchval(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM accounts
                    WHERE premise_id = $1
                )
                """,
                invoice.premise_id
            )

            if not account_exists:
                raise HTTPException(
                    status_code=404,
                    detail=f"Account '{invoice.premise_id}' not found"
                )

            row = await connection.fetchrow(
                """
                INSERT INTO invoices (
                    premise_id,
                    amount,
                    status,
                    due_date
                )
                VALUES ($1, $2, $3, $4)
                RETURNING
                    invoice_id,
                    premise_id,
                    amount,
                    status,
                    due_date
                """,
                invoice.premise_id,
                invoice.amount,
                invoice.status,
                invoice.due_date
            )

    return dict(row)