from flask import Flask, render_template
from sqlalchemy import text
from config import Config
from database.db import db
from database import models

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

def query(sql):
    return db.session.execute(text(sql)).mappings().all()

def count(table):
    return db.session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0

@app.route("/")
@app.route("/dashboard")
def dashboard():
    stats = {
        "requests": count("purchase_requests"),
        "approved": db.session.execute(text("SELECT COUNT(*) FROM purchase_requests WHERE status IN ('APPROVED','RFQ_CREATED','ORDERED','PARTIALLY_DELIVERED','COMPLETED')")).scalar() or 0,
        "orders": count("purchase_orders"), "suppliers": count("suppliers"),
        "rfqs": count("rfqs"), "quotes": count("supplier_quotes"),
        "deliveries": count("deliveries"), "audit_events": count("audit_events"),
        "departments": count("departments"), "requesters": count("requesters"),
        "anomalies": count("anomaly_records")
    }
    recent = query("SELECT id, category, estimated_cost, currency, status, request_date FROM purchase_requests ORDER BY request_date DESC LIMIT 8")
    return render_template("dashboard.html", stats=stats, recent=recent)

@app.route("/requests")
def requests():
    records = query("SELECT id, department_id, category, estimated_cost, currency, request_date, status FROM purchase_requests ORDER BY request_date DESC LIMIT 100")
    return render_template("requests.html", records=records, total=count("purchase_requests"))

@app.route("/approvals")
def approvals():
    records = query("SELECT id, request_id, approver_name, approver_role, approval_level, decision, decided_at FROM approvals ORDER BY id DESC LIMIT 100")
    return render_template("approvals.html", records=records, total=count("approvals"))

@app.route("/suppliers")
def suppliers():
    records = query("SELECT id, supplier_code, name, country, risk_level, risk_score, is_active FROM suppliers ORDER BY name LIMIT 100")
    return render_template("suppliers.html", records=records, total=count("suppliers"))

@app.route("/anomalies")
def anomalies():
    records = query("SELECT entity_type, entity_id, issue_type, expected_decision, reason, detected FROM anomaly_records ORDER BY id")
    return render_template("anomalies.html", records=records, total=count("anomaly_records"))

@app.route("/rfqs")
def rfqs():
    records = query("""
        SELECT r.id, r.request_id, r.created_date, r.closing_date, r.status,
        COUNT(DISTINCT rs.supplier_id) AS invited_suppliers,
        COUNT(DISTINCT q.id) AS received_quotes
        FROM rfqs r
        LEFT JOIN rfq_suppliers rs ON rs.rfq_id = r.id
        LEFT JOIN supplier_quotes q ON q.rfq_id = r.id
        GROUP BY r.id ORDER BY r.created_date DESC LIMIT 100
    """)
    return render_template("rfqs.html", records=records, total=count("rfqs"))

@app.route("/quotes")
def quotes():
    records = query("""
        SELECT q.id, q.rfq_id, s.name AS supplier_name, q.currency,
        q.total_landed_cost, q.delivery_days, q.valid_until, q.status,
        q.is_awarded
        FROM supplier_quotes q
        JOIN suppliers s ON s.id = q.supplier_id
        ORDER BY q.rfq_id, q.total_landed_cost LIMIT 150
    """)
    return render_template("quotes.html", records=records, total=count("supplier_quotes"))

@app.route("/purchase-orders")
def purchase_orders():
    records = query("""
        SELECT p.id, p.request_id, s.name AS supplier_name, p.po_date,
        p.currency, p.total_amount, p.status, p.award_rationale
        FROM purchase_orders p JOIN suppliers s ON s.id = p.supplier_id
        ORDER BY p.po_date DESC LIMIT 100
    """)
    return render_template("purchase_orders.html", records=records, total=count("purchase_orders"))

@app.route("/deliveries")
def deliveries():
    records = query("""
        SELECT d.id, d.po_id, d.delivery_date, d.expected_date,
        d.item_quantity, d.received_quantity, d.status, d.notes
        FROM deliveries d ORDER BY d.delivery_date DESC LIMIT 100
    """)
    return render_template("deliveries.html", records=records, total=count("deliveries"))

@app.route("/audit")
def audit():
    records = query("""
        SELECT id, entity_type, entity_id, event_type, old_value,
        new_value, reason, actor, occurred_at
        FROM audit_events ORDER BY occurred_at DESC LIMIT 150
    """)
    return render_template("audit.html", records=records, total=count("audit_events"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
