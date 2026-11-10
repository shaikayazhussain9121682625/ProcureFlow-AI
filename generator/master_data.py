import random
from faker import Faker

fake = Faker("en_IN")
SEED = 20261022


def generate_departments(count=10):
    departments = []
    names = [
        "Engineering", "Human Resources", "Finance", "Marketing",
        "Operations", "Sales", "IT", "Administration",
        "Procurement", "Legal"
    ]

    for i in range(count):
        name = names[i % len(names)]
        if i >= len(names):
            name = f"{name} {i + 1}"

        departments.append({
            "id": f"DEP-{i + 1:03d}",
            "name": name,
            "code": f"DEPT-{i + 1:03d}",
            "manager_name": fake.name(),
            "is_active": True
        })

    return departments


def generate_requesters(departments, count=300):
    requesters = []

    for i in range(count):
        requesters.append({
            "id": f"REQTR-{i + 1:06d}",
            "employee_code": f"EMP-{i + 1:05d}",
            "name": fake.name(),
            "email": f"employee{i + 1}@example.com",
            "department_id": random.choice(departments)["id"],
            "job_title": random.choice([
                "Software Engineer", "HR Executive", "Accountant",
                "Marketing Executive", "Operations Executive",
                "Business Analyst"
            ]),
            "is_active": True
        })

    return requesters


def generate_budgets(departments, fiscal_year=2026):
    budgets = []
    categories = [
        "IT Equipment", "Software", "Office Supplies",
        "Marketing", "Travel"
    ]

    for department in departments:
        for category in categories:
            budgets.append({
                "id": f"BUD-{department['id']}-{categories.index(category) + 1:02d}",
                "department_id": department["id"],
                "fiscal_year": fiscal_year,
                "category": category,
                "allocated_amount": random.randint(500000, 2000000),
                "reserved_amount": 0,
                "spent_amount": 0,
                "effective_from": fake.date_between(
                    start_date="-1y", end_date="today"
                ),
                "effective_to": fake.date_between(
                    start_date="+300d", end_date="+365d"
                ),
                "status": "ACTIVE"
            })

    return budgets


def seed_master_data():
    from database.db import db
    from database.models import Department, Requester, Budget

    random.seed(SEED)
    Faker.seed(SEED)
    fake.seed_instance(SEED)

    if Department.query.first():
        print("Master data already exists. Skipping insertion.")
        print("Departments:", Department.query.count())
        print("Requesters:", Requester.query.count())
        print("Budgets:", Budget.query.count())
        return

    try:
        department_objects = [
            Department(**item)
            for item in generate_departments(10)
        ]

        db.session.add_all(department_objects)
        db.session.flush()

        department_refs = [
            {"id": item.id}
            for item in department_objects
        ]

        requester_objects = [
            Requester(**item)
            for item in generate_requesters(department_refs, 300)
        ]

        budget_objects = [
            Budget(**item)
            for item in generate_budgets(department_refs, 2026)
        ]

        db.session.add_all(requester_objects)
        db.session.add_all(budget_objects)
        db.session.commit()

        print("MASTER DATA CREATED SUCCESSFULLY")
        print("Departments:", Department.query.count())
        print("Requesters:", Requester.query.count())
        print("Budgets:", Budget.query.count())

    except Exception:
        db.session.rollback()
        raise

