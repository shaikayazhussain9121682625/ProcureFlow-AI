from app import app
from database.db import db
from sqlalchemy import text

with app.app_context():
    # Find an existing PO with a more expensive valid quote
    # from the same RFQ and an active supplier.
    candidate = db.session.execute(text("""
        SELECT
            p.id AS po_id,
            oldq.id AS old_quote_id,
            newq.id AS new_quote_id,
            newq.supplier_id,
            newq.currency,
            newq.subtotal,
            newq.tax_amount,
            newq.shipping_cost,
            newq.total_landed_cost
        FROM purchase_orders p
        JOIN supplier_quotes oldq ON oldq.id = p.quote_id
        JOIN supplier_quotes newq ON newq.rfq_id = oldq.rfq_id
        JOIN suppliers s ON s.id = newq.supplier_id
        JOIN rfqs f ON f.id = newq.rfq_id
        JOIN purchase_requests r ON r.id = f.request_id
        WHERE newq.id != oldq.id
          AND newq.status = 'RECEIVED'
          AND newq.is_awarded = 0
          AND s.is_active = 1
          AND newq.currency = r.currency
          AND newq.quote_date <= f.closing_date
          AND newq.valid_until > f.closing_date
          AND newq.total_landed_cost > oldq.total_landed_cost
        ORDER BY (newq.total_landed_cost - oldq.total_landed_cost) DESC
        LIMIT 1
    """)).mappings().first()

    if not candidate:
        print("No safe alternative quote found. No changes made.")
    else:
        po_id = candidate["po_id"]
        old_quote_id = candidate["old_quote_id"]
        new_quote_id = candidate["new_quote_id"]

        # Preserve the original quote as received.
        db.session.execute(text("""
            UPDATE supplier_quotes
            SET status='RECEIVED', is_awarded=0
            WHERE id=:id
        """), {"id": old_quote_id})

        # Award the more expensive quote.
        db.session.execute(text("""
            UPDATE supplier_quotes
            SET status='AWARDED', is_awarded=1
            WHERE id=:id
        """), {"id": new_quote_id})

        # Update PO to match the newly awarded quote.
        db.session.execute(text("""
            UPDATE purchase_orders
            SET quote_id=:quote_id,
                supplier_id=:supplier_id,
                currency=:currency,
                subtotal=:subtotal,
                tax_amount=:tax,
                shipping_cost=:shipping,
                total_amount=:total,
                award_rationale='Synthetic anomaly: higher-priced valid quote selected for review.'
            WHERE id=:po_id
        """), {
            "quote_id": new_quote_id,
            "supplier_id": candidate["supplier_id"],
            "currency": candidate["currency"],
            "subtotal": candidate["subtotal"],
            "tax": candidate["tax_amount"],
            "shipping": candidate["shipping_cost"],
            "total": candidate["total_landed_cost"],
            "po_id": po_id
        })

        # Rebuild PO lines from the selected quote lines.
        db.session.execute(text("""
            DELETE FROM purchase_order_lines WHERE po_id=:po_id
        """), {"po_id": po_id})

        quote_lines = db.session.execute(text("""
            SELECT id, request_line_id, quantity, unit_price, line_total
            FROM supplier_quote_lines
            WHERE quote_id=:quote_id
        """), {"quote_id": new_quote_id}).mappings().all()

        for index, line in enumerate(quote_lines, start=1):
            db.session.execute(text("""
                INSERT INTO purchase_order_lines
                (id, po_id, quote_line_id, item_name, quantity, unit_price, line_total)
                SELECT :line_id, :po_id, :quote_line_id,
                       rl.item_name, :quantity, :unit_price, :line_total
                FROM request_lines rl
                WHERE rl.id=:request_line_id
            """), {
                "line_id": f"{po_id}-LINE-{index:02d}",
                "po_id": po_id,
                "quote_line_id": line["id"],
                "request_line_id": line["request_line_id"],
                "quantity": line["quantity"],
                "unit_price": line["unit_price"],
                "line_total": line["line_total"]
            })

        db.session.commit()
        print("NON-CHEAPEST SUPPLIER CASE CREATED")
        print("Purchase order:", po_id)
        print("Previous quote:", old_quote_id)
        print("Selected quote:", new_quote_id)
        print("Selected quote is more expensive and its PO lines were synchronized.")
