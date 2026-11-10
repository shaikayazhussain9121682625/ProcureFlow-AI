import random
from datetime import timedelta
from decimal import Decimal

from database.db import db
from database.models import (
    PurchaseRequest, RequestLine, Supplier, RFQ,
    RFQSupplier, SupplierQuote, SupplierQuoteLine
)

SEED = 20261022


def seed_rfqs_and_quotes(count=500):
    if RFQ.query.first():
        print("RFQs already exist. Skipping to prevent duplicates.")
        return

    random.seed(SEED)

    requests = (
        PurchaseRequest.query
        .filter_by(status="APPROVED")
        .order_by(PurchaseRequest.id)
        .limit(count)
        .all()
    )
    suppliers = Supplier.query.filter_by(is_active=True).order_by(Supplier.id).all()

    if len(requests) < count:
        raise ValueError(f"Need {count} approved requests, found {len(requests)}")
    if len(suppliers) < 3:
        raise ValueError("At least 3 active suppliers are required.")

    rfq_count = 0
    quote_count = 0
    quote_line_count = 0
    quote_sequence = 0
    line_sequence = 0
    invitation_sequence = 0

    try:
        for index, request in enumerate(requests, start=1):
            rfq_id = f"RFQ-2026-{index:06d}"
            created_date = request.request_date
            closing_date = created_date + timedelta(days=7)

            rfq = RFQ(
                id=rfq_id,
                request_id=request.id,
                created_date=created_date,
                closing_date=closing_date,
                status="OPEN",
                competitive=True,
                exception_reason=None
            )
            db.session.add(rfq)
            rfq_count += 1

            selected_suppliers = random.sample(suppliers, 3)

            request_lines = (
                RequestLine.query
                .filter_by(request_id=request.id)
                .order_by(RequestLine.id)
                .all()
            )

            if not request_lines:
                raise ValueError(f"No request lines found for {request.id}")

            for supplier in selected_suppliers:
                invitation_sequence += 1
                db.session.add(RFQSupplier(
                    rfq_id=rfq_id,
                    supplier_id=supplier.id,
                    response_status="RESPONDED"
                ))

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
                    quote_line_count += 1

                subtotal = subtotal.quantize(Decimal("0.01"))
                tax = (subtotal * Decimal("0.18")).quantize(Decimal("0.01"))
                shipping = Decimal(str(random.choice([0, 250, 500, 750])))

                total = (subtotal + tax + shipping).quantize(Decimal("0.01"))
                quote_date = created_date + timedelta(days=random.randint(1, 5))
                valid_until = quote_date + timedelta(days=30)

                quote = SupplierQuote(
                    id=quote_id,
                    rfq_id=rfq_id,
                    supplier_id=supplier.id,
                    quote_date=quote_date,
                    valid_until=valid_until,
                    currency="INR",
                    subtotal=subtotal,
                    tax_amount=tax,
                    shipping_cost=shipping,
                    other_cost=Decimal("0.00"),
                    total_landed_cost=total,
                    delivery_days=random.randint(3, 20),
                    status="RECEIVED",
                    is_awarded=False
                )
                db.session.add(quote)
                db.session.add_all(quote_line_records)
                quote_count += 1

        db.session.commit()

        print("\nRFQ AND QUOTE GENERATION SUCCESSFUL")
        print("RFQs created:", rfq_count)
        print("Supplier invitations:", invitation_sequence)
        print("Supplier quotes created:", quote_count)
        print("Quote lines created:", quote_line_count)

    except Exception:
        db.session.rollback()
        raise


if __name__ == "__main__":
    from app import app
    with app.app_context():
        seed_rfqs_and_quotes()
