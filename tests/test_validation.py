from app import app
from database.db import db


def test_database_has_expected_tables():
    with app.app_context():
        assert len(db.metadata.tables) == 16


def test_all_approved_requests_have_purchase_orders():
    with app.app_context():
        missing = db.session.execute(db.text("""
            SELECT COUNT(*)
            FROM purchase_requests r
            WHERE r.status IN ('ORDERED', 'PARTIALLY_DELIVERED', 'COMPLETED')
              AND NOT EXISTS (
                  SELECT 1 FROM purchase_orders p
                  WHERE p.request_id = r.id
              )
        """)).scalar()
        assert missing == 0


def test_purchase_order_totals_match_awarded_quotes():
    with app.app_context():
        mismatches = db.session.execute(db.text("""
            SELECT COUNT(*)
            FROM purchase_orders p
            JOIN supplier_quotes q ON q.id = p.quote_id
            WHERE ABS(p.total_amount - q.total_landed_cost) > 0.01
        """)).scalar()
        assert mismatches == 0


def test_purchase_order_line_arithmetic():
    with app.app_context():
        errors = db.session.execute(db.text("""
            SELECT COUNT(*)
            FROM purchase_order_lines
            WHERE ABS(line_total - quantity * unit_price) > 0.01
        """)).scalar()
        assert errors == 0


def test_po_without_approval_is_labelled_anomaly():
    with app.app_context():
        flagged = db.session.execute(db.text("""
            SELECT COUNT(*) FROM purchase_orders
            WHERE issued_without_approval = 1
        """)).scalar()

        labelled = db.session.execute(db.text("""
            SELECT COUNT(*) FROM anomaly_records
            WHERE issue_type = 'PO_WITHOUT_APPROVAL'
              AND entity_id = 'PO-2026-000001'
        """)).scalar()

        assert flagged == 1
        assert labelled == 1


def test_all_purchase_orders_have_deliveries():
    with app.app_context():
        missing = db.session.execute(db.text("""
            SELECT COUNT(*)
            FROM purchase_orders p
            WHERE NOT EXISTS (
                SELECT 1 FROM deliveries d WHERE d.po_id = p.id
            )
        """)).scalar()
        assert missing == 0
