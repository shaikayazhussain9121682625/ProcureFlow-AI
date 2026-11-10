from datetime import date
from decimal import Decimal

from database.db import db
from database.models import (
    PurchaseRequest, RequestLine, Supplier, SupplierQuote,
    SupplierQuoteLine, PurchaseOrder, PurchaseOrderLine, RFQ
)


def award_and_create_purchase_orders():
    if PurchaseOrder.query.first():
        print("Purchase orders already exist. Reset them before regenerating.")
        return

    approved_requests = (
        PurchaseRequest.query
        .filter_by(status="APPROVED")
        .order_by(PurchaseRequest.id)
        .all()
    )

    po_count = 0
    skipped_count = 0
    po_line_sequence = 0

    try:
        for request in approved_requests:
            rfq = RFQ.query.filter_by(request_id=request.id).first()

            if rfq is None:
                skipped_count += 1
                continue

            quotes = SupplierQuote.query.filter_by(
                rfq_id=rfq.id, status="RECEIVED"
            ).all()

            eligible = []

            for quote in quotes:
                supplier = db.session.get(Supplier, quote.supplier_id)

                if supplier is None or not supplier.is_active:
                    continue
                if quote.currency != request.currency:
                    continue
                if quote.quote_date > rfq.closing_date:
                    continue
                if quote.valid_until < rfq.closing_date:
                    continue

                eligible.append((quote, supplier))

            if not eligible:
                skipped_count += 1
                continue

            eligible.sort(
                key=lambda pair: (
                    Decimal(str(pair[0].total_landed_cost)),
                    pair[0].delivery_days,
                    pair[1].risk_score,
                    pair[1].id
                )
            )

            winning_quote, winning_supplier = eligible[0]

            rationale = (
                "Selected the lowest total landed cost among eligible "
                "quotes valid at RFQ closing. Delivery time and supplier "
                f"risk were tie-breakers. Supplier risk: "
                f"{winning_supplier.risk_level} "
                f"({winning_supplier.risk_score}/100); "
                f"delivery: {winning_quote.delivery_days} days."
            )

            po_id = f"PO-2026-{po_count + 1:06d}"

            db.session.add(PurchaseOrder(
                id=po_id,
                request_id=request.id,
                quote_id=winning_quote.id,
                supplier_id=winning_supplier.id,
                po_date=rfq.closing_date,
                currency=winning_quote.currency,
                subtotal=winning_quote.subtotal,
                tax_amount=winning_quote.tax_amount,
                shipping_cost=winning_quote.shipping_cost,
                total_amount=winning_quote.total_landed_cost,
                status="ISSUED",
                award_rationale=rationale,
                issued_without_approval=False
            ))

            winning_quote.is_awarded = True
            winning_quote.status = "AWARDED"
            rfq.status = "AWARDED"

            winning_lines = SupplierQuoteLine.query.filter_by(
                quote_id=winning_quote.id
            ).all()

            for quote_line in winning_lines:
                request_line = db.session.get(
                    RequestLine, quote_line.request_line_id
                )
                if request_line is None:
                    raise ValueError(
                        f"Missing request line: {quote_line.request_line_id}"
                    )

                po_line_sequence += 1
                db.session.add(PurchaseOrderLine(
                    id=f"POL-2026-{po_line_sequence:07d}",
                    po_id=po_id,
                    quote_line_id=quote_line.id,
                    item_name=request_line.item_name,
                    quantity=quote_line.quantity,
                    unit_price=quote_line.unit_price,
                    line_total=quote_line.line_total
                ))

            request.status = "ORDERED"
            po_count += 1

        db.session.commit()

        print("\nPURCHASE ORDER GENERATION COMPLETED")
        print("Purchase orders created:", po_count)
        print("Approved requests skipped:", skipped_count)
        print("Purchase order lines:", po_line_sequence)

    except Exception:
        db.session.rollback()
        raise


if __name__ == "__main__":
    from app import app
    with app.app_context():
        award_and_create_purchase_orders()
