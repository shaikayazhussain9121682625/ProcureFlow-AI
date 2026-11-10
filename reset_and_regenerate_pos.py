from app import app
from database.db import db
from database.models import (
    PurchaseOrder, PurchaseOrderLine, SupplierQuote,
    PurchaseRequest, RFQ
)
from services.procurement_service import award_and_create_purchase_orders

with app.app_context():
    existing_pos = PurchaseOrder.query.all()
    affected_request_ids = [po.request_id for po in existing_pos]
    affected_quote_ids = [po.quote_id for po in existing_pos]

    for po in existing_pos:
        PurchaseOrderLine.query.filter_by(po_id=po.id).delete()

    for quote_id in affected_quote_ids:
        quote = db.session.get(SupplierQuote, quote_id)
        if quote:
            quote.is_awarded = False
            quote.status = "RECEIVED"

    for request_id in affected_request_ids:
        request = db.session.get(PurchaseRequest, request_id)
        if request:
            request.status = "APPROVED"

    for request_id in affected_request_ids:
        rfq = RFQ.query.filter_by(request_id=request_id).first()
        if rfq:
            rfq.status = "OPEN"

    PurchaseOrder.query.delete()
    db.session.commit()

    print("Previous test awards reset successfully.")
    award_and_create_purchase_orders()
