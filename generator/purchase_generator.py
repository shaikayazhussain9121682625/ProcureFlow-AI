import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from faker import Faker

fake = Faker("en_IN")
SEED = 20261022

CATEGORIES = [
    "IT Equipment",
    "Software",
    "Office Supplies",
    "Marketing",
    "Travel"
]

ITEMS = {
    "IT Equipment": ["Laptop", "Monitor", "Keyboard", "Mouse", "Printer"],
    "Software": ["Software License", "Cloud Subscription", "Security License"],
    "Office Supplies": ["Paper", "Pens", "Notebooks", "Printer Ink"],
    "Marketing": ["Brochure Printing", "Banner", "Digital Campaign"],
    "Travel": ["Flight Ticket", "Hotel Booking", "Travel Allowance"]
}


def generate_purchase_requests(requesters, budgets, count=1200):
    random.seed(SEED)
    Faker.seed(SEED)
    fake.seed_instance(SEED)

    requests = []
    lines = []
    line_number = 1
    budgets_by_department = {}

    for budget in budgets:
        budgets_by_department.setdefault(
            budget.department_id, {}
        )[budget.category] = budget

    for index in range(1, count + 1):
        requester = random.choice(requesters)
        department_id = requester.department_id

        available_categories = [
            category for category in CATEGORIES
            if category in budgets_by_department.get(department_id, {})
        ]

        category = random.choice(available_categories)
        budget = budgets_by_department[department_id][category]

        request_date = date(2026, 1, 1) + timedelta(
            days=random.randint(0, 313)
        )
        required_date = request_date + timedelta(
            days=random.randint(7, 60)
        )

        request_line_data = []

        for _ in range(random.randint(1, 3)):
            quantity = random.randint(1, 5)
            unit_price = Decimal(str(round(random.uniform(500, 8000), 2)))
            line_total = (unit_price * quantity).quantize(
                Decimal("0.01")
            )

            request_line_data.append({
                "id": f"RL-2026-{line_number:06d}",
                "request_id": f"PR-2026-{index:06d}",
                "item_name": random.choice(ITEMS[category]),
                "description": fake.sentence(),
                "category": category,
                "quantity": quantity,
                "unit": "pieces",
                "estimated_unit_price": unit_price,
                "estimated_total": line_total
            })

            line_number += 1

        estimated_cost = sum(
            (line["estimated_total"] for line in request_line_data),
            Decimal("0.00")
        )

        requests.append({
            "id": f"PR-2026-{index:06d}",
            "requester_id": requester.id,
            "department_id": department_id,
            "budget_id": budget.id,
            "request_date": request_date,
            "required_date": required_date,
            "category": category,
            "estimated_cost": estimated_cost,
            "currency": "INR",
            "purpose": fake.sentence(nb_words=12),
            "status": "SUBMITTED",
            "duplicate_of_id": None,
            "created_at": datetime.combine(
                request_date, datetime.min.time()
            )
        })

        lines.extend(request_line_data)

    return requests, lines


def seed_purchase_requests():
    from database.db import db
    from database.models import (
        Requester, Budget, PurchaseRequest, RequestLine
    )

    if PurchaseRequest.query.first():
        print("Purchase requests already exist. Skipping insertion.")
        print("Requests:", PurchaseRequest.query.count())
        print("Request lines:", RequestLine.query.count())
        return

    try:
        requesters = Requester.query.filter_by(is_active=True).all()
        budgets = Budget.query.filter_by(status="ACTIVE").all()

        if not requesters or not budgets:
            raise ValueError("Requesters or active budgets are missing.")

        request_data, line_data = generate_purchase_requests(
            requesters, budgets, 1200
        )

        request_objects = [
            PurchaseRequest(**item) for item in request_data
        ]

        line_objects = [
            RequestLine(**item) for item in line_data
        ]

        db.session.add_all(request_objects)
        db.session.flush()

        db.session.add_all(line_objects)
        db.session.commit()

        print("PURCHASE REQUESTS CREATED SUCCESSFULLY")
        print("Purchase requests:", PurchaseRequest.query.count())
        print("Request lines:", RequestLine.query.count())

    except Exception:
        db.session.rollback()
        raise
