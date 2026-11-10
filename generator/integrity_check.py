from app import app
from database.db import db

errors = []
checks = 0

with app.app_context():
    connection = db.engine.connect()

    try:
        for table_name, table in db.metadata.tables.items():
            # Primary-key NULL and duplicate checks
            primary_keys = list(table.primary_key.columns)

            for column in primary_keys:
                null_count = connection.execute(
                    db.text(
                        f'SELECT COUNT(*) FROM "{table_name}" '
                        f'WHERE "{column.name}" IS NULL'
                    )
                ).scalar()

                duplicate_count = connection.execute(
                    db.text(
                        f'SELECT COUNT(*) FROM ('
                        f'SELECT "{column.name}" FROM "{table_name}" '
                        f'GROUP BY "{column.name}" HAVING COUNT(*) > 1)'
                    )
                ).scalar()

                checks += 2

                if null_count:
                    errors.append(
                        f"{table_name}.{column.name}: {null_count} NULL primary keys"
                    )

                if duplicate_count:
                    errors.append(
                        f"{table_name}.{column.name}: {duplicate_count} duplicate primary keys"
                    )

            # Foreign-key integrity checks
            for column in table.columns:
                for fk in column.foreign_keys:
                    parent_table, parent_column = fk.target_fullname.split(".")

                    broken_count = connection.execute(
                        db.text(
                            f'SELECT COUNT(*) FROM "{table_name}" child '
                            f'WHERE child."{column.name}" IS NOT NULL '
                            f'AND NOT EXISTS ('
                            f'SELECT 1 FROM "{parent_table}" parent '
                            f'WHERE parent."{parent_column}" = child."{column.name}")'
                        )
                    ).scalar()

                    checks += 1

                    if broken_count:
                        errors.append(
                            f"{table_name}.{column.name}: "
                            f"{broken_count} broken references to "
                            f"{parent_table}.{parent_column}"
                        )

        print("INTEGRITY CHECKS:", checks)

        if errors:
            print("\nVALIDATION FAILED")
            for error in errors:
                print("ERROR:", error)
        else:
            print("RESULT: PASSED")
            print("No NULL/duplicate primary keys or broken foreign keys found.")

    finally:
        connection.close()
