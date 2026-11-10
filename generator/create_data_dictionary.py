import csv
import os
from app import app
from database.db import db

os.makedirs("docs", exist_ok=True)

with app.app_context():
    output = "docs/data_dictionary.csv"

    with open(output, "w", newline="", encoding="utf-8") as file:
        fields = [
            "table_name", "column_name", "data_type",
            "required", "primary_key", "foreign_key",
            "default_value", "description"
        ]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()

        for table_name, table in db.metadata.tables.items():
            for column in table.columns:
                foreign_keys = [
                    fk.target_fullname for fk in column.foreign_keys
                ]

                writer.writerow({
                    "table_name": table_name,
                    "column_name": column.name,
                    "data_type": str(column.type),
                    "required": not column.nullable,
                    "primary_key": column.primary_key,
                    "foreign_key": "; ".join(foreign_keys),
                    "default_value": str(column.default.arg)
                        if column.default is not None else "",
                    "description": ""
                })

    print("DATA DICTIONARY CREATED")
    print("File:", output)
    print("Tables:", len(db.metadata.tables))
    print("Columns:", sum(
        len(table.columns) for table in db.metadata.tables.values()
    ))
