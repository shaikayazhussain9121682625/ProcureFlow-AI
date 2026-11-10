import random
from faker import Faker

fake = Faker("en_IN")
SEED = 20261022

def generate_suppliers(count=120):
    suppliers = []
    currencies = ["INR", "USD", "EUR"]

    for i in range(count):
        risk_level = random.choices(
            ["LOW", "MEDIUM", "HIGH"],
            weights=[65, 25, 10]
        )[0]

        risk_score = {
            "LOW": random.randint(0, 30),
            "MEDIUM": random.randint(31, 65),
            "HIGH": random.randint(66, 100)
        }[risk_level]

        suppliers.append({
            "id": f"SUP-{i + 1:06d}",
            "supplier_code": f"SUPP-{i + 1:04d}",
            "name": f"{fake.company()} {i + 1}",
            "email": f"supplier{i + 1}@example.com",
            "phone": fake.phone_number()[:30],
            "address": fake.address(),
            "country": "India",
            "currency": "INR",
            "risk_level": risk_level,
            "risk_score": risk_score,
            "is_active": True
        })

    return suppliers


def seed_suppliers():
    from database.db import db
    from database.models import Supplier

    if Supplier.query.first():
        print("Suppliers already exist. Skipping insertion.")
        print("Suppliers:", Supplier.query.count())
        return

    random.seed(SEED)
    Faker.seed(SEED)
    fake.seed_instance(SEED)

    try:
        supplier_data = generate_suppliers(120)
        supplier_objects = [
            Supplier(**item) for item in supplier_data
        ]

        db.session.add_all(supplier_objects)
        db.session.commit()

        print("SUPPLIERS CREATED SUCCESSFULLY")
        print("Total suppliers:", Supplier.query.count())
        print(
            "Active suppliers:",
            Supplier.query.filter_by(is_active=True).count()
        )
        print("Risk distribution:")

        for level in ["LOW", "MEDIUM", "HIGH"]:
            print(
                level,
                Supplier.query.filter_by(risk_level=level).count()
            )

    except Exception:
        db.session.rollback()
        raise
