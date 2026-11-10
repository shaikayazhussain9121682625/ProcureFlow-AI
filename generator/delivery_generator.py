import random
from datetime import timedelta

from app import app
from database.db import db
from database.models import (
    PurchaseOrder, PurchaseOrderLine, Delivery
)

def generate_deliveries():
    if Delivery.query.first():
        print("Deliveries already exist. Skipping to prevent duplicates.")
        return

    random.seed(20261022)
    purchase_orders = PurchaseOrder.query.order_by(
        PurchaseOrder.id
    ).all()

    created = 0
    partial_count = 0
    delivered_count = 0
    delayed_count = 0
    pending_count = 0
    sequence = 0

    try:
        for po in purchase_orders:
            lines = PurchaseOrderLine.query.filter_by(
                po_id=po.id
            ).all()

            if not lines:
                continue

            ordered_quantity = sum(line.quantity for line in lines)
            expected_date = po.po_date + timedelta(
                days=random.randint(3, 20)
            )

            outcome = random.choices(
                ["DELIVERED", "PARTIAL", "DELAYED", "PENDING"],
                weights=[55, 20, 15, 10],
                k=1
            )[0]

            if outcome == "DELIVERED":
                received_quantity = ordered_quantity
                delivery_date = expected_date + timedelta(
                    days=random.randint(-2, 3)
                )
                notes = "All ordered items received."
                delivered_count += 1
                po.status = "DELIVERED"

            elif outcome == "PARTIAL":
                received_quantity = random.randint(
                    1, ordered_quantity - 1
                ) if ordered_quantity > 1 else 0
                delivery_date = expected_date + timedelta(days=1)
                notes = "Partial delivery received; remaining items pending."
                partial_count += 1
                po.status = "PARTIALLY_DELIVERED"

            elif outcome == "DELAYED":
                received_quantity = 0
                delivery_date = expected_date + timedelta(days=5)
                notes = "Supplier delivery delayed; follow-up required."
                delayed_count += 1
                po.status = "ACKNOWLEDGED"

            else:
                received_quantity = 0
                delivery_date = expected_date
                notes = "Delivery pending supplier confirmation."
                pending_count += 1
                po.status = "ISSUED"

            sequence += 1
            delivery_id = f"DEL-{po.id}-01"

            db.session.add(Delivery(
                id=delivery_id,
                po_id=po.id,
                delivery_date=delivery_date,
                expected_date=expected_date,
                item_quantity=ordered_quantity,
                received_quantity=received_quantity,
                status=outcome,
                notes=notes
            ))
            created += 1

        db.session.commit()

        print("\nDELIVERY GENERATION COMPLETED")
        print("Deliveries created:", created)
        print("Delivered:", delivered_count)
        print("Partial:", partial_count)
        print("Delayed:", delayed_count)
        print("Pending:", pending_count)

    except Exception:
        db.session.rollback()
        raise

if __name__ == "__main__":
    with app.app_context():
        generate_deliveries()
