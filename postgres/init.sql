CREATE TABLE IF NOT EXISTS accounts (
    premise_id VARCHAR(50) PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(30),
    address TEXT
);

CREATE TABLE IF NOT EXISTS invoices (
    invoice_id SERIAL PRIMARY KEY,
    premise_id VARCHAR(50) NOT NULL REFERENCES accounts(premise_id),
    amount DECIMAL(10, 2) NOT NULL CHECK (amount >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'UNPAID',
    due_date DATE NOT NULL
);