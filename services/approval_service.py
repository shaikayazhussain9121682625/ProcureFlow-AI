from decimal import Decimal
from datetime import datetime


APPROVAL_LEVELS = [
    (Decimal("50000"), "Department Manager"),
    (Decimal("200000"), "Department Head"),
    (Decimal("999999999999"), "Finance Head"),
]


def get_required_approvers(amount):
    if amount <= Decimal("50000"):
        return APPROVAL_LEVELS[:1]

    if amount <= Decimal("200000"):
        return APPROVAL_LEVELS[:2]

    return APPROVAL_LEVELS


def process_approvals():
    from database.db import db
    from database.models import (
        PurchaseRequest, Budget, Approval
    )

    if Approval.query.first():
        print("Approval records already exist. Skipping.")
        print("Approvals:", Approval.query.count())
        return

    requests = PurchaseRequest.query.order_by(
        PurchaseRequest.request_date,
        PurchaseRequest.id
    ).all()

    budgets = {
        budget.id: budget
        for budget in Budget.query.all()
    }

    approval_number = 1
    approved_count = 0
    rejected_count = 0

    try:
        for request in requests:
            budget = budgets.get(request.budget_id)

            if budget is None:
                raise ValueError(
                    f"Budget missing for request {request.id}"
                )

            amount = Decimal(str(request.estimated_cost))
            reserved = Decimal(str(budget.reserved_amount))
            allocated = Decimal(str(budget.allocated_amount))

            request.status = "PENDING_APPROVAL"

            available = allocated - reserved
            required_approvers = get_required_approvers(amount)

            if amount > available:
                approver_name = "Finance Approval Team"

                approval = Approval(
                    id=f"APR-2026-{approval_number:06d}",
                    request_id=request.id,
                    approver_name=approver_name,
                    approver_role="Finance Head",
                    approval_level=1,
                    decision="REJECTED",
                    threshold_amount=allocated,
                    comments=(
                        f"Rejected: requested amount INR {amount} "
                        f"exceeds available budget INR {available}."
                    ),
                    decided_at=datetime.combine(
                        request.request_date,
                        datetime.min.time()
                    )
                )

                db.session.add(approval)
                approval_number += 1
                request.status = "REJECTED"
                rejected_count += 1
                continue

            for level, (threshold, role) in enumerate(
                required_approvers, start=1
            ):
                approval = Approval(
                    id=f"APR-2026-{approval_number:06d}",
                    request_id=request.id,
                    approver_name=f"{role} - Synthetic",
                    approver_role=role,
                    approval_level=level,
                    decision="APPROVED",
                    threshold_amount=threshold,
                    comments=(
                        "Approved under configured procurement "
                        "approval policy and available budget."
                    ),
                    decided_at=datetime.combine(
                        request.request_date,
                        datetime.min.time()
                    )
                )

                db.session.add(approval)
                approval_number += 1

            budget.reserved_amount = reserved + amount
            request.status = "APPROVED"
            approved_count += 1

        db.session.commit()

        print("APPROVAL WORKFLOW COMPLETED")
        print("Total requests processed:", len(requests))
        print("Approved requests:", approved_count)
        print("Rejected requests:", rejected_count)
        print("Approval records:", Approval.query.count())

    except Exception:
        db.session.rollback()
        raise
