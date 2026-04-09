from sqlalchemy import inspect, text


def apply_schema_updates(connection) -> None:
    inspector = inspect(connection)
    table_names = set(inspector.get_table_names())

    if "organisation" in table_names and "organization" not in table_names:
        connection.execute(text("ALTER TABLE organisation RENAME TO organization"))
        inspector = inspect(connection)
        table_names = set(inspector.get_table_names())

    if "mail_addresses" in table_names:
        mail_columns = {
            column["name"] for column in inspector.get_columns("mail_addresses")
        }
        if "organisation_id" in mail_columns and "organization_id" not in mail_columns:
            connection.execute(
                text(
                    "ALTER TABLE mail_addresses "
                    "RENAME COLUMN organisation_id TO organization_id"
                )
            )
            inspector = inspect(connection)
            mail_columns = {
                column["name"] for column in inspector.get_columns("mail_addresses")
            }
    else:
        mail_columns = set()

    if "is_active" not in mail_columns:
        connection.execute(
            text(
                "ALTER TABLE mail_addresses "
                "ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"
            )
        )

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "organisation_id" in user_columns and "organization_id" not in user_columns:
        connection.execute(
            text("ALTER TABLE users RENAME COLUMN organisation_id TO organization_id")
        )
        inspector = inspect(connection)
        user_columns = {column["name"] for column in inspector.get_columns("users")}

    if "first_name" not in user_columns:
        connection.execute(
            text("ALTER TABLE users ADD COLUMN first_name TEXT NOT NULL DEFAULT ''")
        )
    if "last_name" not in user_columns:
        connection.execute(
            text("ALTER TABLE users ADD COLUMN last_name TEXT NOT NULL DEFAULT ''")
        )
    if "email" not in user_columns:
        connection.execute(
            text("ALTER TABLE users ADD COLUMN email TEXT NOT NULL DEFAULT ''")
        )
    if "is_bootstrap_admin" in user_columns and "is_root" not in user_columns:
        connection.execute(
            text("ALTER TABLE users RENAME COLUMN is_bootstrap_admin TO is_root")
        )
        inspector = inspect(connection)
        user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "is_root" not in user_columns:
        connection.execute(
            text("ALTER TABLE users ADD COLUMN is_root BOOLEAN NOT NULL DEFAULT 0")
        )
        user_columns.add("is_root")

    connection.execute(
        text(
            "UPDATE users "
            "SET email = username "
            "WHERE email IS NULL OR TRIM(email) = ''"
        )
    )
    connection.execute(
        text(
            "UPDATE users "
            "SET first_name = username "
            "WHERE first_name IS NULL OR TRIM(first_name) = ''"
        )
    )
    connection.execute(
        text(
            "UPDATE users "
            "SET role = 'root' "
            "WHERE role = 'superadmin'"
        )
    )
    if "ip_addresses" not in table_names:
        connection.execute(
            text(
                "CREATE TABLE ip_addresses ("
                "id INTEGER PRIMARY KEY, "
                "ip_address VARCHAR NOT NULL, "
                "organization_id INTEGER NOT NULL, "
                "is_active BOOLEAN NOT NULL DEFAULT 1, "
                "FOREIGN KEY(organization_id) REFERENCES organization (id)"
                ")"
            )
        )
        connection.execute(
            text("CREATE INDEX ix_ip_addresses_ip_address ON ip_addresses (ip_address)")
        )

    if "audit_log" not in table_names:
        connection.execute(
            text(
                "CREATE TABLE audit_log ("
                "id INTEGER PRIMARY KEY, "
                "entity_type VARCHAR NOT NULL, "
                "entity_id INTEGER, "
                "action VARCHAR NOT NULL, "
                "actor_user_id INTEGER, "
                "actor_email VARCHAR NOT NULL, "
                "organization_id INTEGER, "
                "changes_json TEXT NOT NULL, "
                "rollback_json TEXT, "
                "created_at TIMESTAMP NOT NULL"
                ")"
            )
        )
        connection.execute(
            text("CREATE INDEX ix_audit_log_entity_type ON audit_log (entity_type)")
        )
        connection.execute(
            text("CREATE INDEX ix_audit_log_entity_id ON audit_log (entity_id)")
        )
        connection.execute(text("CREATE INDEX ix_audit_log_action ON audit_log (action)"))
        connection.execute(
            text("CREATE INDEX ix_audit_log_actor_email ON audit_log (actor_email)")
        )
        connection.execute(
            text("CREATE INDEX ix_audit_log_created_at ON audit_log (created_at)")
        )
