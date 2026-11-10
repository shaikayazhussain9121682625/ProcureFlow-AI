from app import app
from database.db import db
import os

os.makedirs("exports/sql", exist_ok=True)

with app.app_context():
    raw = db.engine.raw_connection()
    try:
        connection = raw.driver_connection
        output_path = "exports/sql/procureflow_seed.sql"

        with open(output_path, "w", encoding="utf-8") as file:
            file.write("-- ProcureFlow SQLite database export\n")
            file.write("-- Generated from the current database\n\n")
            for statement in connection.iterdump():
                file.write(statement + "\n")

        print("SQL EXPORT COMPLETED")
        print("File:", output_path)
        print("Size:", os.path.getsize(output_path), "bytes")
    finally:
        raw.close()
