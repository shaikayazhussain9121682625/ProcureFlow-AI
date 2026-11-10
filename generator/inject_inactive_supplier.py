from app import app
from database.db import db
from sqlalchemy import text

with app.app_context():
    supplier = db.session.execute(text("""
        SELECT id FROM suppliers
        WHERE is_active = 1
        ORDER BY id LIMIT 1
    """)).first()

    if supplier:
        db.session.execute(text("""
            UPDATE suppliers SET is_active = 0 WHERE id = :id
        """), {"id": supplier[0]})
        db.session.commit()
        print("INACTIVE SUPPLIER CREATED:", supplier[0])
    else:
        print("No active supplier available.")
