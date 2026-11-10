import os
import json
import csv
from datetime import date, datetime
from decimal import Decimal

from app import app
from database.db import db

EXCLUDED = {"anomaly_records"}

def convert(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value

def export_all():
    os.makedirs("exports/csv", exist_ok=True)
    os.makedirs("exports/json", exist_ok=True)

    total_tables = 0
    total_rows = 0

    for table_name, table in db.metadata.tables.items():
        if table_name in EXCLUDED:
            continue

        rows = db.session.execute(
            db.select(table)
        ).mappings().all()

        records = [
            {key: convert(value) for key, value in row.items()}
            for row in rows
        ]

        csv_path = f"exports/csv/{table_name}.csv"
        json_path = f"exports/json/{table_name}.json"

        with open(csv_path, "w", newline="", encoding="utf-8") as file:
            if records:
                writer = csv.DictWriter(
                    file, fieldnames=list(records[0].keys())
                )
                writer.writeheader()
                writer.writerows(records)
            else:
                writer = csv.writer(file)
                writer.writerow([column.name for column in table.columns])

        with open(json_path, "w", encoding="utf-8") as file:
            json.dump(records, file, indent=2, ensure_ascii=False)

        print(table_name, ":", len(records), "records exported")
        total_tables += 1
        total_rows += len(records)

    print("\nEXPORT COMPLETED")
    print("Tables exported:", total_tables)
    print("Total records exported:", total_rows)
    print("CSV folder: exports/csv")
    print("JSON folder: exports/json")
    print("Anomaly labels excluded from normal exports.")

if __name__ == "__main__":
    with app.app_context():
        export_all()
