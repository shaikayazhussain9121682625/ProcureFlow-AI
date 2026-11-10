from app import app
from database.db import db

checks = []
errors = []

def check(label, sql, expected=0):
    value = db.session.execute(db.text(sql)).scalar()
    checks.append((label, value))
    if value != expected:
        errors.append(f"{label}: found {value}, expected {expected}")

with app.app_context():
    check(
        "Approved requests without purchase orders",
        """
        SELECT COUNT(*) FROM purchase_requests r
        WHERE r.status = 'APPROVED'
        AND NOT EXISTS (
            SELECT 1 FROM purchase_orders p WHERE p.request_id = r.id
        )
        """
    )

    check(
        "Purchase orders linked to non-approved requests",
        """
        SELECT COUNT(*) FROM purchase_orders p
        JOIN purchase_requests r ON r.id = p.request_id
        WHERE r.status NOT IN ('ORDERED','PARTIALLY_DELIVERED','COMPLETED')
        """
    )

    check(
        "Purchase order total differs from awarded quote",
        """
        SELECT COUNT(*) FROM purchase_orders p
        JOIN supplier_quotes q ON q.id = p.quote_id
        WHERE ABS(p.total_amount - q.total_landed_cost) > 0.01
        """
    )

    check(
        "Purchase order line total arithmetic errors",
        """
        SELECT COUNT(*) FROM purchase_order_lines
        WHERE ABS(line_total - (quantity * unit_price)) > 0.01
        """
    )

    check(
        "Purchase order lines differ from awarded quote lines",
        """
        SELECT COUNT(*) FROM purchase_orders p
        WHERE ABS(
            (SELECT COALESCE(SUM(pol.line_total), 0)
             FROM purchase_order_lines pol WHERE pol.po_id = p.id)
            -
            (SELECT COALESCE(SUM(ql.line_total), 0)
             FROM supplier_quote_lines ql WHERE ql.quote_id = p.quote_id)
        ) > 0.01
        """
    )

    check(
        "Purchase orders issued without approval flag",
        """
        SELECT COUNT(*) FROM purchase_orders
        WHERE issued_without_approval = 1
        """
    )

    print("PROCUREMENT BUSINESS RULE CHECKS")
    for label, value in checks:
        print(f"{label}: {value}")

    print("\nTOTAL CHECKS:", len(checks))
    if errors:
        print("RESULT: FAILED")
        for error in errors:
            print("ERROR:", error)
    else:
        print("RESULT: PASSED")
