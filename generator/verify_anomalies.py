from app import app
from database.db import db

with app.app_context():
    queries = {
        "PO_WITHOUT_APPROVAL": """
            SELECT COUNT(*) FROM purchase_orders p
            JOIN purchase_requests r ON r.id=p.request_id
            WHERE p.issued_without_approval=1
               OR NOT EXISTS (
                   SELECT 1 FROM approvals a
                   WHERE a.request_id=r.id AND a.decision='APPROVED'
               )
        """,
        "EXPIRED_QUOTE": """
            SELECT COUNT(*) FROM supplier_quotes q
            JOIN rfqs r ON r.id=q.rfq_id
            WHERE q.valid_until <= r.closing_date
              AND q.is_awarded=0
        """,
        "NON_CHEAPEST_SUPPLIER": """
            SELECT COUNT(*) FROM purchase_orders p
            JOIN supplier_quotes q ON q.id=p.quote_id
            WHERE q.total_landed_cost > (
                SELECT MIN(q2.total_landed_cost)
                FROM supplier_quotes q2
                WHERE q2.rfq_id=q.rfq_id
                  AND q2.currency=q.currency
                  AND q2.status IN ('RECEIVED','AWARDED')
            )
        """,
        "INACTIVE_SUPPLIER": """
            SELECT COUNT(*) FROM suppliers WHERE is_active=0
        """,
        "BUDGET_OVERRUN": """
            SELECT COUNT(*) FROM budgets
            WHERE reserved_amount + spent_amount > allocated_amount
        """,
        "DUPLICATE_REQUEST": """
            SELECT COUNT(*) FROM purchase_requests
            WHERE duplicate_of_id IS NOT NULL
        """,
        "QUOTE_CURRENCY_MISMATCH": """
            SELECT COUNT(*) FROM supplier_quotes q
            JOIN rfqs f ON f.id=q.rfq_id
            JOIN purchase_requests r ON r.id=f.request_id
            WHERE q.currency != r.currency
        """
    }

    print("ANOMALY VERIFICATION")
    for name, sql in queries.items():
        count = db.session.execute(db.text(sql)).scalar()
        print(f"{name}: {count} genuine matching records")
