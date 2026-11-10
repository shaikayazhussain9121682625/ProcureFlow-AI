from datetime import datetime
from database.db import db
from database.models import AnomalyRecord

def generate_anomalies():
    if AnomalyRecord.query.count():
        print("Anomaly records already exist. Skipping.")
        return

    anomalies = [
        ("PurchaseOrder", "PO-2026-000001", "PO_WITHOUT_APPROVAL", "REJECT",
         "Purchase order exists without an approved request."),
        ("SupplierQuote", "QUOTATION-EXPIRED-001", "EXPIRED_QUOTE", "REJECT",
         "Supplier quote expired before award."),
        ("PurchaseOrder", "PO-2026-000002", "NON_CHEAPEST_SUPPLIER", "REVIEW",
         "Selected supplier was not the cheapest eligible supplier."),
        ("Supplier", "SUP-000001", "INACTIVE_SUPPLIER", "REJECT",
         "Inactive supplier was selected."),
        ("Budget", "BUD-DEP-001-01", "BUDGET_OVERRUN", "REJECT",
         "Purchase amount exceeds available budget."),
        ("PurchaseRequest", "PR-2026-000001", "DUPLICATE_REQUEST", "REVIEW",
         "Potential duplicate purchase request detected."),
        ("SupplierQuote", "QUOTATION-CURRENCY-001", "QUOTE_CURRENCY_MISMATCH", "REJECT",
         "Supplier quote currency does not match purchase request currency.")
    ]

    try:
        for entity_type, entity_id, issue_type, decision, reason in anomalies:
            db.session.add(AnomalyRecord(
                entity_type=entity_type,
                entity_id=entity_id,
                issue_type=issue_type,
                ground_truth="ANOMALY",
                expected_decision=decision,
                reason=reason,
                detected=False,
                created_at=datetime.utcnow()
            ))

        db.session.commit()
        print("ANOMALY LABELS CREATED:", len(anomalies))
        print("TOTAL ANOMALY RECORDS:", AnomalyRecord.query.count())

    except Exception:
        db.session.rollback()
        raise

if __name__ == "__main__":
    from app import app
    with app.app_context():
        generate_anomalies()
