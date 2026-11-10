from collections import Counter
from decimal import Decimal

from app import app
from database.models import (
    RFQ, RFQSupplier, SupplierQuote, SupplierQuoteLine,
    PurchaseRequest, Supplier
)
from database.db import db

with app.app_context():
    rfqs = RFQ.query.all()
    quotes = SupplierQuote.query.all()
    invitations = RFQSupplier.query.all()
    quote_lines = SupplierQuoteLine.query.all()

    quote_line_totals = Counter()
    for line in quote_lines:
        quote_line_totals[line.quote_id] += Decimal(str(line.line_total))

    missing_rfq = sum(
        1 for q in quotes if db.session.get(RFQ, q.rfq_id) is None
    )
    missing_supplier = sum(
        1 for q in quotes if db.session.get(Supplier, q.supplier_id) is None
    )
    missing_request = sum(
        1 for r in rfqs if db.session.get(PurchaseRequest, r.request_id) is None
    )
    wrong_subtotal = sum(
        1 for q in quotes
        if quote_line_totals[q.id].quantize(Decimal("0.01"))
        != Decimal(str(q.subtotal)).quantize(Decimal("0.01"))
    )
    wrong_landed_total = sum(
        1 for q in quotes
        if (
            Decimal(str(q.subtotal))
            + Decimal(str(q.tax_amount))
            + Decimal(str(q.shipping_cost))
            + Decimal(str(q.other_cost))
        ).quantize(Decimal("0.01"))
        != Decimal(str(q.total_landed_cost)).quantize(Decimal("0.01"))
    )

    invitations_per_rfq = Counter(i.rfq_id for i in invitations)
    quotes_per_rfq = Counter(q.rfq_id for q in quotes)

    print("\nRFQ AND QUOTE VALIDATION")
    print("RFQs:", len(rfqs))
    print("Invitations:", len(invitations))
    print("Quotes:", len(quotes))
    print("Quote lines:", len(quote_lines))
    print("RFQs without exactly 3 invitations:", sum(v != 3 for v in invitations_per_rfq.values()))
    print("RFQs without exactly 3 quotes:", sum(v != 3 for v in quotes_per_rfq.values()))
    print("Missing RFQ references:", missing_rfq)
    print("Missing supplier references:", missing_supplier)
    print("Missing purchase request references:", missing_request)
    print("Quote subtotal mismatches:", wrong_subtotal)
    print("Landed total mismatches:", wrong_landed_total)

    if (
        len(rfqs) == 500 and len(quotes) == 1500
        and len(invitations) == 1500
        and not any([
            missing_rfq, missing_supplier, missing_request,
            wrong_subtotal, wrong_landed_total
        ])
        and all(v == 3 for v in invitations_per_rfq.values())
        and all(v == 3 for v in quotes_per_rfq.values())
    ):
        print("\nRESULT: ALL CHECKS PASSED")
    else:
        print("\nRESULT: CHECKS FAILED - we must fix issues before continuing.")
