import os
from datetime import date
from decimal import Decimal
import asyncpg

NUM_ACCOUNTS = 100
INVOICE_DUE_DATE = date(2026, 9, 30)

async def seed_postgres():
    print("Seeding PostgreSQL...")
    dsn = os.getenv("POSTGRES_DSN")
    if not dsn:raise RuntimeError("PostgreSQL environment variables are not configured")

    connection = await asyncpg.connect(dsn)

    try:
        async with connection.transaction():

            for i in range(1, NUM_ACCOUNTS + 1):
                premise_id = f"PREM_{10000 + i}"
                amount = Decimal("40.00") + Decimal(i)

                await connection.execute(
                    """
                    INSERT INTO accounts (
                        premise_id,
                        customer_name,
                        email,
                        phone,
                        address
                    )
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (premise_id)
                    DO UPDATE SET
                        customer_name = EXCLUDED.customer_name,
                        email = EXCLUDED.email,
                        phone = EXCLUDED.phone,
                        address = EXCLUDED.address
                    """,
                    premise_id,
                    f"Consumer {i}",
                    f"consumer{i}@example.com",
                    f"+306900{i:06d}",
                    f"Grid Street {i}",
                )

                status = "PAID" if i % 3 == 0 else "UNPAID"

                await connection.execute(
                    """
                    INSERT INTO invoices (
                        premise_id,
                        amount,
                        status,
                        due_date
                    )
                    SELECT
                        $1::varchar,
                        $2::numeric,
                        $3::varchar,
                        $4::date
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM invoices
                        WHERE premise_id = $1::varchar
                          AND due_date = $4::date
                    )
                    """,
                    premise_id,
                    amount,
                    status,
                    INVOICE_DUE_DATE,
                )

        print(f"PostgreSQL seeded successfully: {NUM_ACCOUNTS} accounts with sample invoices")

    finally:
        await connection.close()