from datetime import datetime, timezone
from database.db import db


def utcnow():
    return datetime.now(timezone.utc)


class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.String(30), primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    code = db.Column(db.String(20), nullable=False, unique=True)
    manager_name = db.Column(db.String(120))
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class Requester(db.Model):
    __tablename__ = "requesters"

    id = db.Column(db.String(30), primary_key=True)
    employee_code = db.Column(db.String(30), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    department_id = db.Column(
        db.String(30), db.ForeignKey("departments.id"), nullable=False
    )
    job_title = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class Budget(db.Model):
    __tablename__ = "budgets"

    id = db.Column(db.String(30), primary_key=True)
    department_id = db.Column(
        db.String(30), db.ForeignKey("departments.id"), nullable=False
    )
    fiscal_year = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(80), nullable=False)
    allocated_amount = db.Column(db.Numeric(14, 2), nullable=False)
    reserved_amount = db.Column(db.Numeric(14, 2), default=0, nullable=False)
    spent_amount = db.Column(db.Numeric(14, 2), default=0, nullable=False)
    effective_from = db.Column(db.Date, nullable=False)
    effective_to = db.Column(db.Date)
    status = db.Column(db.String(20), default="ACTIVE", nullable=False)

    __table_args__ = (
        db.CheckConstraint("allocated_amount >= 0"),
        db.CheckConstraint("reserved_amount >= 0"),
        db.CheckConstraint("spent_amount >= 0"),
        db.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'CLOSED')"
        ),
    )


class PurchaseRequest(db.Model):
    __tablename__ = "purchase_requests"

    id = db.Column(db.String(30), primary_key=True)
    requester_id = db.Column(
        db.String(30), db.ForeignKey("requesters.id"), nullable=False
    )
    department_id = db.Column(
        db.String(30), db.ForeignKey("departments.id"), nullable=False
    )
    budget_id = db.Column(
        db.String(30), db.ForeignKey("budgets.id"), nullable=False
    )
    request_date = db.Column(db.Date, nullable=False)
    required_date = db.Column(db.Date, nullable=False)
    category = db.Column(db.String(80), nullable=False)
    estimated_cost = db.Column(db.Numeric(14, 2), nullable=False)
    currency = db.Column(db.String(3), default="INR", nullable=False)
    purpose = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default="DRAFT", nullable=False)
    duplicate_of_id = db.Column(
        db.String(30), db.ForeignKey("purchase_requests.id")
    )
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        db.CheckConstraint("estimated_cost > 0"),
        db.CheckConstraint(
            "status IN ('DRAFT','SUBMITTED','PENDING_APPROVAL',"
            "'APPROVED','REJECTED','RFQ_CREATED','ORDERED',"
            "'PARTIALLY_DELIVERED','COMPLETED','CANCELLED')"
        ),
    )


class RequestLine(db.Model):
    __tablename__ = "request_lines"

    id = db.Column(db.String(30), primary_key=True)
    request_id = db.Column(
        db.String(30),
        db.ForeignKey("purchase_requests.id"),
        nullable=False
    )
    item_name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(80), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit = db.Column(db.String(30), default="unit", nullable=False)
    estimated_unit_price = db.Column(db.Numeric(14, 2), nullable=False)
    estimated_total = db.Column(db.Numeric(14, 2), nullable=False)

    __table_args__ = (
        db.CheckConstraint("quantity > 0"),
        db.CheckConstraint("estimated_unit_price >= 0"),
        db.CheckConstraint("estimated_total >= 0"),
    )


class Supplier(db.Model):
    __tablename__ = "suppliers"

    id = db.Column(db.String(30), primary_key=True)
    supplier_code = db.Column(db.String(30), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(30))
    address = db.Column(db.Text)
    country = db.Column(db.String(80), default="India")
    currency = db.Column(db.String(3), default="INR", nullable=False)
    risk_level = db.Column(
        db.String(20), default="LOW", nullable=False
    )
    risk_score = db.Column(db.Integer, default=10, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        db.CheckConstraint("risk_score >= 0 AND risk_score <= 100"),
        db.CheckConstraint("risk_level IN ('LOW','MEDIUM','HIGH')"),
    )


class RFQ(db.Model):
    __tablename__ = "rfqs"

    id = db.Column(db.String(30), primary_key=True)
    request_id = db.Column(
        db.String(30), db.ForeignKey("purchase_requests.id"),
        nullable=False
    )
    created_date = db.Column(db.Date, nullable=False)
    closing_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default="OPEN", nullable=False)
    competitive = db.Column(db.Boolean, default=True, nullable=False)
    exception_reason = db.Column(db.Text)

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('OPEN','CLOSED','CANCELLED','AWARDED')"
        ),
    )


class RFQSupplier(db.Model):
    """Bridge table: RFQs and suppliers have a many-to-many relationship."""

    __tablename__ = "rfq_suppliers"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    rfq_id = db.Column(
        db.String(30), db.ForeignKey("rfqs.id"), nullable=False
    )
    supplier_id = db.Column(
        db.String(30), db.ForeignKey("suppliers.id"), nullable=False
    )
    invited_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    response_status = db.Column(
        db.String(20), default="INVITED", nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint("rfq_id", "supplier_id"),
    )


class SupplierQuote(db.Model):
    __tablename__ = "supplier_quotes"

    id = db.Column(db.String(60), primary_key=True)
    rfq_id = db.Column(
        db.String(30), db.ForeignKey("rfqs.id"), nullable=False
    )
    supplier_id = db.Column(
        db.String(30), db.ForeignKey("suppliers.id"), nullable=False
    )
    quote_date = db.Column(db.Date, nullable=False)
    valid_until = db.Column(db.Date, nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    subtotal = db.Column(db.Numeric(14, 2), nullable=False)
    tax_amount = db.Column(db.Numeric(14, 2), default=0, nullable=False)
    shipping_cost = db.Column(db.Numeric(14, 2), default=0, nullable=False)
    other_cost = db.Column(db.Numeric(14, 2), default=0, nullable=False)
    total_landed_cost = db.Column(db.Numeric(14, 2), nullable=False)
    delivery_days = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default="RECEIVED", nullable=False)
    is_awarded = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (
        db.CheckConstraint("subtotal >= 0"),
        db.CheckConstraint("tax_amount >= 0"),
        db.CheckConstraint("shipping_cost >= 0"),
        db.CheckConstraint("other_cost >= 0"),
        db.CheckConstraint("total_landed_cost >= 0"),
        db.CheckConstraint("delivery_days >= 0"),
        db.CheckConstraint(
            "status IN ('RECEIVED','EXPIRED','REJECTED','AWARDED')"
        ),
    )


class SupplierQuoteLine(db.Model):
    """Supporting table for individual items in supplier quotations."""

    __tablename__ = "supplier_quote_lines"

    id = db.Column(db.String(40), primary_key=True)
    quote_id = db.Column(
        db.String(60), db.ForeignKey("supplier_quotes.id"),
        nullable=False
    )
    request_line_id = db.Column(
        db.String(30), db.ForeignKey("request_lines.id"),
        nullable=False
    )
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(14, 2), nullable=False)
    line_total = db.Column(db.Numeric(14, 2), nullable=False)

    __table_args__ = (
        db.CheckConstraint("quantity > 0"),
        db.CheckConstraint("unit_price >= 0"),
        db.CheckConstraint("line_total >= 0"),
    )


class Approval(db.Model):
    __tablename__ = "approvals"

    id = db.Column(db.String(30), primary_key=True)
    request_id = db.Column(
        db.String(30), db.ForeignKey("purchase_requests.id"),
        nullable=False
    )
    approver_name = db.Column(db.String(120), nullable=False)
    approver_role = db.Column(db.String(80), nullable=False)
    approval_level = db.Column(db.Integer, nullable=False)
    decision = db.Column(
        db.String(20), default="PENDING", nullable=False
    )
    threshold_amount = db.Column(db.Numeric(14, 2), nullable=False)
    comments = db.Column(db.Text)
    decided_at = db.Column(db.DateTime(timezone=True))

    __table_args__ = (
        db.CheckConstraint("approval_level > 0"),
        db.CheckConstraint(
            "decision IN ('PENDING','APPROVED','REJECTED','CHANGES_REQUESTED')"
        ),
    )


class PurchaseOrder(db.Model):
    __tablename__ = "purchase_orders"

    id = db.Column(db.String(30), primary_key=True)
    request_id = db.Column(
        db.String(30), db.ForeignKey("purchase_requests.id"),
        nullable=False
    )
    quote_id = db.Column(
        db.String(60), db.ForeignKey("supplier_quotes.id"),
        nullable=False
    )
    supplier_id = db.Column(
        db.String(30), db.ForeignKey("suppliers.id"),
        nullable=False
    )
    po_date = db.Column(db.Date, nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    subtotal = db.Column(db.Numeric(14, 2), nullable=False)
    tax_amount = db.Column(db.Numeric(14, 2), default=0, nullable=False)
    shipping_cost = db.Column(db.Numeric(14, 2), default=0, nullable=False)
    total_amount = db.Column(db.Numeric(14, 2), nullable=False)
    status = db.Column(db.String(30), default="DRAFT", nullable=False)
    award_rationale = db.Column(db.Text)
    issued_without_approval = db.Column(
        db.Boolean, default=False, nullable=False
    )

    __table_args__ = (
        db.CheckConstraint("total_amount >= 0"),
        db.CheckConstraint(
            "status IN ('DRAFT','ISSUED','ACKNOWLEDGED','PARTIALLY_DELIVERED',"
            "'DELIVERED','CANCELLED')"
        ),
    )


class PurchaseOrderLine(db.Model):
    """Supporting table for individual items in a purchase order."""

    __tablename__ = "purchase_order_lines"

    id = db.Column(db.String(40), primary_key=True)
    po_id = db.Column(
        db.String(30), db.ForeignKey("purchase_orders.id"),
        nullable=False
    )
    quote_line_id = db.Column(
        db.String(40), db.ForeignKey("supplier_quote_lines.id"),
        nullable=False
    )
    item_name = db.Column(db.String(150), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(14, 2), nullable=False)
    line_total = db.Column(db.Numeric(14, 2), nullable=False)

    __table_args__ = (
        db.CheckConstraint("quantity > 0"),
        db.CheckConstraint("unit_price >= 0"),
        db.CheckConstraint("line_total >= 0"),
    )


class Delivery(db.Model):
    __tablename__ = "deliveries"

    id = db.Column(db.String(60), primary_key=True)
    po_id = db.Column(
        db.String(30), db.ForeignKey("purchase_orders.id"),
        nullable=False
    )
    delivery_date = db.Column(db.Date, nullable=False)
    expected_date = db.Column(db.Date, nullable=False)
    item_quantity = db.Column(db.Integer, nullable=False)
    received_quantity = db.Column(db.Integer, default=0, nullable=False)
    status = db.Column(db.String(20), default="PENDING", nullable=False)
    notes = db.Column(db.Text)

    __table_args__ = (
        db.CheckConstraint("item_quantity > 0"),
        db.CheckConstraint("received_quantity >= 0"),
        db.CheckConstraint(
            "status IN ('PENDING','PARTIAL','DELIVERED','DELAYED','REJECTED')"
        ),
    )


class AuditEvent(db.Model):
    """Append-only history of business state changes."""

    __tablename__ = "audit_events"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.String(60), nullable=False)
    event_type = db.Column(db.String(80), nullable=False)
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    reason = db.Column(db.Text)
    actor = db.Column(db.String(120))
    occurred_at = db.Column(db.DateTime(timezone=True), default=utcnow,
                            nullable=False)


class AnomalyRecord(db.Model):
    """Separate known anomaly labels; never use as normal input features."""

    __tablename__ = "anomaly_records"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.String(60), nullable=False)
    issue_type = db.Column(db.String(80), nullable=False)
    ground_truth = db.Column(db.String(20), nullable=False)
    expected_decision = db.Column(db.String(120), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    detected = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow,
                           nullable=False)
