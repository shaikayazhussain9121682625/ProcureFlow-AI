import csv
import os
from app import app
from database.db import db
from sqlalchemy import text

verified_ids = {
    "PO_WITHOUT_APPROVAL": "PO-2026-000001",
    "EXPIRED_QUOTE": "QUO-SUPP-0088-2026-000001",
    "NON_CHEAPEST_SUPPLIER": "PO-2026-001063",
    "INACTIVE_SUPPLIER": "SUP-000001",
    "BUDGET_OVERRUN": "BUD-DEP-001-01",
    "DUPLICATE_REQUEST": "PR-2026-000002",
    "QUOTE_CURRENCY_MISMATCH": "QUO-SUPP-0001-2026-000147"
}

with app.app_context():
    for issue, entity_id in verified_ids.items():
        db.session.execute(text("""
            UPDATE anomaly_records
            SET entity_id = :entity_id
            WHERE issue_type = :issue
        """), {"entity_id": entity_id, "issue": issue})

    db.session.commit()

    rows = db.session.execute(text("""
        SELECT entity_type, entity_id, issue_type,
               ground_truth, expected_decision, reason
        FROM anomaly_records
        ORDER BY id
    """)).mappings().all()

    os.makedirs("exports/ground_truth", exist_ok=True)
    path = "exports/ground_truth/anomaly_ground_truth.csv"

    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows([dict(row) for row in rows])

    print("GROUND TRUTH UPDATED")
    print("Records:", len(rows))
    print("File:", path)
    for row in rows:
        print(row["issue_type"], "->", row["entity_id"])
