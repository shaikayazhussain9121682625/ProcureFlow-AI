from datetime import timedelta
from database.db import db
from database.models import PurchaseRequest, RFQ

def create_missing_rfqs():
    requests = (
        PurchaseRequest.query
        .filter_by(status="APPROVED")
        .order_by(PurchaseRequest.id)
        .all()
    )

    created = 0

    try:
        for request in requests:
            existing = RFQ.query.filter_by(request_id=request.id).first()

            if existing:
                continue

            index = RFQ.query.count() + 1
            rfq_id = f"RFQ-2026-{index:06d}"

            db.session.add(RFQ(
                id=rfq_id,
                request_id=request.id,
                created_date=request.request_date,
                closing_date=request.request_date + timedelta(days=7),
                status="OPEN",
                competitive=True,
                exception_reason=None
            ))
            created += 1

        db.session.commit()
        print("MISSING RFQS CREATED:", created)
        print("TOTAL RFQS:", RFQ.query.count())

    except Exception:
        db.session.rollback()
        raise

if __name__ == "__main__":
    from app import app
    with app.app_context():
        create_missing_rfqs()
