from app import app
from database.db import db
from database.models import AnomalyRecord, SupplierQuote

with app.app_context():
    expired_label = AnomalyRecord.query.filter_by(
        issue_type="EXPIRED_QUOTE"
    ).first()

    mismatch_label = AnomalyRecord.query.filter_by(
        issue_type="QUOTE_CURRENCY_MISMATCH"
    ).first()

    expired_quote = db.session.get(
        SupplierQuote, expired_label.entity_id
    )
    mismatch_quote = db.session.get(
        SupplierQuote, mismatch_label.entity_id
    )

    if not expired_quote or not mismatch_quote:
        raise ValueError("Anomaly quote reference is missing.")

    expired_rfq = expired_quote.rfq_id
    from database.models import RFQ
    rfq = db.session.get(RFQ, expired_rfq)

    expired_quote.valid_until = rfq.closing_date.replace(
        day=max(1, rfq.closing_date.day - 2)
    )

    mismatch_quote.currency = "USD"

    db.session.commit()

    print("EXPIRED QUOTE CASE CREATED:", expired_quote.id)
    print("Quote validity:", expired_quote.valid_until)
    print("RFQ closing date:", rfq.closing_date)
    print("CURRENCY MISMATCH CASE CREATED:", mismatch_quote.id)
    print("Changed quote currency to:", mismatch_quote.currency)
    print("Both anomaly cases updated.")
