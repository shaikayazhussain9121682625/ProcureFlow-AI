from app import app
from database.db import db
from database.models import AnomalyRecord, SupplierQuote

with app.app_context():
    expired = (
        SupplierQuote.query
        .filter(SupplierQuote.valid_until < db.func.date('now'))
        .first()
    )

    currency_quote = (
        SupplierQuote.query
        .order_by(SupplierQuote.id)
        .first()
    )

    if not expired or not currency_quote:
        raise ValueError("Could not find suitable quote records.")

    expired_label = AnomalyRecord.query.filter_by(
        issue_type="EXPIRED_QUOTE"
    ).first()

    currency_label = AnomalyRecord.query.filter_by(
        issue_type="QUOTE_CURRENCY_MISMATCH"
    ).first()

    expired_label.entity_id = expired.id
    currency_label.entity_id = currency_quote.id

    db.session.commit()

    print("EXPIRED QUOTE REFERENCE:", expired.id)
    print("CURRENCY MISMATCH REFERENCE:", currency_quote.id)
    print("References updated successfully.")
