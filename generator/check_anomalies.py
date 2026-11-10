from app import app
from database.db import db

with app.app_context():
    rows = db.session.execute(db.text("""
        SELECT entity_type, entity_id, issue_type,
               ground_truth, expected_decision, reason
        FROM anomaly_records ORDER BY id
    """)).mappings().all()

    print("ANOMALY RECORDS:", len(rows))

    table_map = {
        "PurchaseOrder": "purchase_orders",
        "SupplierQuote": "supplier_quotes",
        "Supplier": "suppliers",
        "Budget": "budgets",
        "PurchaseRequest": "purchase_requests"
    }

    for row in rows:
        print("\n", dict(row))
        table = table_map.get(row["entity_type"])
        if table:
            count = db.session.execute(
                db.text(f'SELECT COUNT(*) FROM "{table}" WHERE id=:id'),
                {"id": row["entity_id"]}
            ).scalar()
            print("ENTITY:", "FOUND" if count else "MISSING")
