from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from flask import render_template, request, redirect, url_for, flash
from database.db import db
from sqlalchemy.exc import IntegrityError
from database.models import (
    Department, Requester, Budget, PurchaseRequest,
    RequestLine, Approval, AuditEvent
)

def register_ui_routes(app):

    @app.route("/requests/create", methods=["GET", "POST"])
    def create_request():
        requesters = Requester.query.filter_by(is_active=True).all()
        budgets = Budget.query.filter_by(status="ACTIVE").all()

        if request.method == "POST":
            try:
                requester = db.session.get(Requester, request.form.get("requester_id"))
                budget = db.session.get(Budget, request.form.get("budget_id"))
                category = request.form.get("category", "").strip()
                purpose = request.form.get("purpose", "").strip()
                item = request.form.get("item_name", "").strip()
                quantity = int(request.form.get("quantity", "1"))
                cost = Decimal(request.form.get("estimated_cost", "0"))

                if not requester or not budget:
                    raise ValueError("Select a valid requester and budget.")
                if requester.department_id != budget.department_id:
                    raise ValueError("Requester and budget departments must match.")
                if not category or not purpose or not item:
                    raise ValueError("Complete all required fields.")
                if quantity <= 0 or cost <= 0:
                    raise ValueError("Quantity and cost must be positive.")
                if budget.category != category:
                    raise ValueError("Choose a budget matching the selected category.")

                available = (
                    Decimal(str(budget.allocated_amount))
                    - Decimal(str(budget.reserved_amount))
                    - Decimal(str(budget.spent_amount))
                )
                if cost > available:
                    raise ValueError(f"Insufficient budget. Available: INR {available}")

                # Generate IDs using the highest numeric suffix, not alphabetical order.
                existing_pr_numbers = [
                    int(row.id.rsplit("-", 1)[-1])
                    for row in PurchaseRequest.query.all()
                    if row.id.startswith("PR-2026-")
                ]
                number = max(existing_pr_numbers, default=0) + 1
                pr_id = f"PR-2026-{number:06d}"

                existing_line_numbers = [
                    int(row.id.rsplit("-", 1)[-1])
                    for row in RequestLine.query.all()
                    if row.id.startswith("RL-2026-")
                ]
                line_number = max(existing_line_numbers, default=0) + 1

                required_date = date.fromisoformat(request.form.get("required_date"))

                pr = PurchaseRequest(
                    id=pr_id,
                    requester_id=requester.id,
                    department_id=requester.department_id,
                    budget_id=budget.id,
                    request_date=date.today(),
                    required_date=required_date,
                    category=category,
                    estimated_cost=cost,
                    currency="INR",
                    purpose=purpose,
                    status="SUBMITTED"
                )
                db.session.add(pr)
                db.session.add(RequestLine(
                    id=f"RL-2026-{line_number:07d}",
                    request_id=pr_id,
                    item_name=item,
                    description=purpose,
                    category=category,
                    quantity=quantity,
                    unit="unit",
                    estimated_unit_price=cost / quantity,
                    estimated_total=cost
                ))
                db.session.add(AuditEvent(
                    entity_type="PurchaseRequest",
                    entity_id=pr_id,
                    event_type="REQUEST_SUBMITTED",
                    new_value="SUBMITTED",
                    reason="Submitted through ProcureFlow AI interface",
                    actor=requester.name
                ))
                db.session.commit()
                flash(f"Request {pr_id} submitted successfully.", "success")
                return redirect(url_for("requests"))
            except (ValueError, InvalidOperation, TypeError, IntegrityError) as exc:
                db.session.rollback()
                flash(str(exc), "error")

        categories = ["IT Equipment", "Marketing", "Office Supplies", "Software", "Travel"]

        return render_template(
            "create_request.html",
            requesters=requesters,
            budgets=budgets,
            categories=categories
        )

    @app.route("/requests/<request_id>/decision", methods=["POST"])
    def request_decision(request_id):
        pr = db.session.get(PurchaseRequest, request_id)
        if not pr:
            flash("Request not found.", "error")
            return redirect(url_for("approvals"))

        if pr.status not in ("SUBMITTED", "PENDING_APPROVAL"):
            flash("This request has already been processed.", "error")
            return redirect(url_for("approvals"))

        decision = request.form.get("decision")
        comments = request.form.get("comments", "").strip()
        budget = db.session.get(Budget, pr.budget_id)

        if decision not in ("APPROVED", "REJECTED"):
            flash("Invalid approval decision.", "error")
            return redirect(url_for("approvals"))

        amount = Decimal(str(pr.estimated_cost))
        available = (
            Decimal(str(budget.allocated_amount))
            - Decimal(str(budget.reserved_amount))
            - Decimal(str(budget.spent_amount))
        )

        if decision == "APPROVED" and amount > available:
            flash("Approval blocked: insufficient available budget.", "error")
            return redirect(url_for("approvals"))

        if decision == "APPROVED":
            if amount <= Decimal("50000"):
                roles = ["Department Manager"]
            elif amount <= Decimal("200000"):
                roles = ["Department Manager", "Department Head"]
            else:
                roles = ["Department Manager", "Department Head", "Finance Head"]

            budget.reserved_amount = Decimal(str(budget.reserved_amount)) + amount
            pr.status = "APPROVED"
        else:
            roles = ["Department Manager"]
            pr.status = "REJECTED"

        existing_approval_numbers = [
            int(row.id.rsplit("-", 1)[-1])
            for row in Approval.query.all()
            if row.id.startswith("APR-2026-")
        ]
        approval_number = max(existing_approval_numbers, default=0) + 1

        for level, role in enumerate(roles, start=1):
            db.session.add(Approval(
                id=f"APR-2026-{approval_number:06d}",
                request_id=pr.id,
                approver_name="Procurement Admin",
                approver_role=role,
                approval_level=level,
                decision=decision,
                threshold_amount=amount,
                comments=comments or f"{decision} through ProcureFlow AI",
                decided_at=datetime.now()
            ))
            approval_number += 1

        db.session.add(AuditEvent(
            entity_type="PurchaseRequest",
            entity_id=pr.id,
            event_type=f"REQUEST_{decision}",
            old_value="SUBMITTED",
            new_value=pr.status,
            reason=comments or "Decision recorded through application",
            actor="Procurement Admin"
        ))
        db.session.commit()
        flash(f"{pr.id} {decision.lower()} successfully.", "success")
        return redirect(url_for("approvals"))
