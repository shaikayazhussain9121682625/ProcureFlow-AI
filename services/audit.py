from datetime import datetime, timezone

from app import app
from database.db import db
from database.models import (
    AuditEvent, PurchaseRequest, RFQ,
    SupplierQuote, PurchaseOrder, Delivery,
    AnomalyRecord
)

def generate_audit_history():
    if AuditEvent.query.first():
        print("Audit events already exist. Skipping.")
        return

    events = []

    def add_event(entity_type, entity_id, event_type, old_value, new_value, reason, actor):
        events.append(AuditEvent(
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            actor=actor,
            occurred_at=datetime.now(timezone.utc)
        ))

    for r in PurchaseRequest.query.all():
        if r.status in ("APPROVED", "REJECTED", "ORDERED",
                        "PARTIALLY_DELIVERED", "COMPLETED"):
            add_event(
                "PurchaseRequest", r.id, "STATUS_CHANGED",
                "SUBMITTED", r.status,
                "Approval workflow outcome", "Procurement System"
            )

    for r in RFQ.query.all():
        add_event(
            "RFQ", r.id, "RFQ_CREATED",
            None, r.status, "RFQ created for purchase request",
            "Procurement System"
        )

    for q in SupplierQuote.query.all():
        add_event(
            "SupplierQuote", q.id, "QUOTE_RECEIVED",
            None, q.status, "Supplier quote recorded",
            "Procurement System"
        )
        if q.is_awarded:
            add_event(
                "SupplierQuote", q.id, "QUOTE_AWARDED",
                "RECEIVED", "AWARDED",
                "Selected through supplier comparison",
                "Procurement System"
            )

    for po in PurchaseOrder.query.all():
        add_event(
            "PurchaseOrder", po.id, "PO_ISSUED",
            None, po.status, po.award_rationale,
            "Procurement System"
        )

    for d in Delivery.query.all():
        add_event(
            "Delivery", d.id, "DELIVERY_RECORDED",
            None, d.status, d.notes,
            "Operations System"
        )

    for a in AnomalyRecord.query.all():
        add_event(
            "AnomalyRecord", str(a.id), "ANOMALY_LABEL_CREATED",
            None, a.issue_type, a.reason,
            "Data Quality System"
        )

    try:
        db.session.add_all(events)
        db.session.commit()
        print("\nAUDIT HISTORY CREATED")
        print("Audit events:", len(events))
        print("Database audit count:", AuditEvent.query.count())
    except Exception:
        db.session.rollback()
        raise

if __name__ == "__main__":
    with app.app_context():
        generate_audit_history()
