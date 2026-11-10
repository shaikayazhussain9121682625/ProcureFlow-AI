from app import app
from database.db import db
from database.models import Delivery

with app.app_context():
    fixed = 0

    for delivery in Delivery.query.filter_by(status="PARTIAL").all():
        if delivery.item_quantity <= 1:
            delivery.status = "DELIVERED"
            delivery.received_quantity = delivery.item_quantity
            delivery.notes = (
                "Fully received; changed from partial because "
                "the ordered quantity was one."
            )
            fixed += 1

    db.session.commit()

    print("INVALID PARTIAL RECORDS FIXED:", fixed)
    print("Remaining partial records:",
          Delivery.query.filter_by(status="PARTIAL").count())
