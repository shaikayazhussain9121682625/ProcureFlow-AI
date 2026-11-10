from app import app
from database.db import db
from sqlalchemy import text

with app.app_context():
    # 1. Flag a PO as an approval exception
    po = db.session.execute(text("""
        SELECT p.id FROM purchase_orders p
        WHERE p.issued_without_approval = 0
        ORDER BY p.id LIMIT 1
    """)).first()
    if po:
        db.session.execute(text("""
            UPDATE purchase_orders
            SET issued_without_approval = 1
            WHERE id = :id
        """), {"id": po[0]})
        print("PO exception created:", po[0])

    # 2. Mark a supplier with no purchase orders inactive
    supplier = db.session.execute(text("""
        SELECT s.id FROM suppliers s
        WHERE s.is_active = 1
          AND NOT EXISTS (
              SELECT 1 FROM purchase_orders p WHERE p.supplier_id = s.id
          )
        ORDER BY s.id LIMIT 1
    """)).first()
    if supplier:
        db.session.execute(text("""
            UPDATE suppliers SET is_active = 0 WHERE id = :id
        """), {"id": supplier[0]})
        print("Inactive supplier created:", supplier[0])
    else:
        print("No unused supplier found; inactive supplier not changed.")

    # 3. Mark a request as a duplicate of another request
    requests = db.session.execute(text("""
        SELECT id FROM purchase_requests
        WHERE duplicate_of_id IS NULL
        ORDER BY id LIMIT 2
    """)).all()
    if len(requests) == 2:
        db.session.execute(text("""
            UPDATE purchase_requests
            SET duplicate_of_id = :original
            WHERE id = :duplicate
        """), {"original": requests[0][0], "duplicate": requests[1][0]})
        print("Duplicate request created:", requests[1][0],
              "duplicates", requests[0][0])

    # 4. Create a budget overrun on a budget record
    budget = db.session.execute(text("""
        SELECT id, reserved_amount, spent_amount
        FROM budgets
        ORDER BY id LIMIT 1
    """)).first()
    if budget:
        actual_usage = float(budget[1] or 0) + float(budget[2] or 0)
        new_allocation = max(0, actual_usage - 1)
        db.session.execute(text("""
            UPDATE budgets
            SET allocated_amount = :amount
            WHERE id = :id
        """), {"amount": new_allocation, "id": budget[0]})
        print("Budget overrun created:", budget[0])

    db.session.commit()
    print("\nFOUR ANOMALY INJECTIONS COMMITTED.")
