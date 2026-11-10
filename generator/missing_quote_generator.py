import random
from datetime import timedelta
from decimal import Decimal

from app import app
from database.db import db
from database.models import (
    PurchaseRequest, RequestLine, Supplier, RFQ,
    RFQSupplier, SupplierQuote, SupplierQuoteLine
)

def generate_missing_quotes():
    random.seed(20261022)

    suppliers = Supplier.query.filter_by(is_active=True).all()
    if len(suppliers) < 3:
        raise ValueError("At least 3 active suppliers are required.")

    existing_quote_count = SupplierQuote.query.count()
    existing_line_count = SupplierQuoteLine.query.count()

    quote_sequence = existing_quote_count
    line_sequence = existing_line_count
    created_quotes = 0
    created_lines = 0
    created_invitations = 0

    rfqs = RFQ.query.order_by(RFQ.id).all()

    try:
        for rfq in rfqs:
            if SupplierQuote.query.filter_by(rfq_id=rfq.id).first():
                continue

            request = db.session.get(PurchaseRequest, rfq.request_id)
            if not request:
                raise ValueError(f"Missing request for {rfq.id}")

            request_lines = RequestLine.query.filter_by(
                request_id=request.id
            ).all()

            if not request_lines:
                raise ValueError(f"No request lines for {request.id}")

            selected_suppliers = random.sample(suppliers, 3)

            for supplier in selected_suppliers:
                db.session.add(RFQSupplier(
                    rfq_id=rfq.id,
                    supplier_id=supplier.id,
                    response_status="RESPONDED"
                ))
                created_invitations += 1

                quote_sequence += 1
                quote_id = (
                    f"QUO-{supplier.supplier_code}-2026-{quote_sequence:06d}"
                )

                subtotal = Decimal("0.00")
                quote_line_records = []

                for request_line in request_lines:
                    unit_price = (
                        Decimal(str(request_line.estimated_unit_price))
                        * Decimal(str(random.uniform(0.90, 1.15)))
                    ).quantize(Decimal("0.01"))

                    line_total = (
                        unit_price * Decimal(str(request_line.quantity))
                    ).quantize(Decimal("0.01"))

                    subtotal += line_total
                    line_sequence += 1

                    quote_line_records.append(SupplierQuoteLine(
                        id=f"QL-2026-{line_sequence:07d}",
                        quote_id=quote_id,
                        request_line_id=request_line.id,
                        quantity=request_line.quantity,
                        unit_price=unit_price,
                        line_total=line_total
                    ))
                    created_lines += 1

                subtotal = subtotal.quantize(Decimal("0.01"))
                tax = (subtotal * Decimal("0.18")).quantize(Decimal("0.01"))
                shipping = Decimal(str(random.choice([0, 250, 500, 750])))
                total = (subtotal + tax + shipping).quantize(Decimal("0.01"))

                quote_date = rfq.created_date + timedelta(
                    days=random.randint(1, 5)
                )

                db.session.add(SupplierQuote(
                    id=quote_id,
                    rfq_id=rfq.id,
                    supplier_id=supplier.id,
                    quote_date=quote_date,
                    valid_until=quote_date + timedelta(days=30),
                    currency=request.currency,
                    subtotal=subtotal,
                    tax_amount=tax,
                    shipping_cost=shipping,
                    other_cost=Decimal("0.00"),
                    total_landed_cost=total,
                    delivery_days=random.randint(3, 20),
                    status="RECEIVED",
                    is_awarded=False
                ))

                db.session.add_all(quote_line_records)
                created_quotes += 1

        db.session.commit()

        print("\nMISSING RFQ QUOTES GENERATED")
        print("New invitations:", created_invitations)
        print("New quotes:", created_quotes)
        print("New quote lines:", created_lines)
        print("TOTAL RFQs:", RFQ.query.count())
        print("TOTAL quotes:", SupplierQuote.query.count())

    except Exception:
        db.session.rollback()
        raise

if __name__ == "__main__":
    with app.app_context():
        generate_missing_quotes()
