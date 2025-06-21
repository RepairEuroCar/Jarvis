import datetime  # Added for created_at

import aiosqlite

DATABASE_FILE = "jarvis_data.db"


class Table:
    def __init__(self, name, columns):
        self.name = name
        self.columns = columns

    async def create(self, db):
        column_defs = ", ".join(
            [
                f"{col['name']} {col['type']}"
                f"{' PRIMARY KEY AUTOINCREMENT' if col.get('primary_key') else ''}"
                f"{' NOT NULL' if col.get('not_null') else ''}"
                for col in self.columns
            ]
        )
        await db.execute(
            f"CREATE TABLE IF NOT EXISTS {self.name} ({column_defs})"
        )
        await db.commit()

    async def insert(self, db, data: dict):
        cols = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        # Ensure 'created_at' is set if the table expects it and it's not provided
        if (
            "created_at"
            in [col["name"] for col in self.columns if col.get("not_null")]
            and "created_at" not in data
        ):
            if any(
                col["name"] == "created_at"
                and col["type"].upper() == "DATETIME"
                for col in self.columns
            ):
                data["created_at"] = datetime.datetime.now().isoformat()

        await db.execute(
            f"INSERT INTO {self.name} ({cols}) VALUES ({placeholders})",
            tuple(data.values()),
        )
        await db.commit()
        async with db.execute(f"SELECT last_insert_rowid()") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

    async def select(
        self,
        db,
        where: dict = None,
        limit: int = None,
        columns: list = None,
        order_by: str = None,
    ):
        select_cols = ", ".join(columns) if columns else "*"
        query = f"SELECT {select_cols} FROM {self.name}"
        params = []  # Use list for params

        if where:
            conditions = " AND ".join([f"{key} = ?" for key in where])
            query += f" WHERE {conditions}"
            params.extend(list(where.values()))

        if order_by:
            query += f" ORDER BY {order_by}"  # Be careful with SQL injection if order_by comes from user input

        if limit:
            query += f" LIMIT ?"
            params.append(limit)

        async with db.execute(query, tuple(params)) as cursor:
            columns_desc = [desc[0] for desc in cursor.description]
            return [dict(zip(columns_desc, row)) async for row in cursor]

    async def update(self, db, data: dict, where: dict):
        if not data or not where:
            raise ValueError(
                "Data and where clause cannot be empty for update operation."
            )
        set_clause = ", ".join([f"{key} = ?" for key in data])
        conditions = " AND ".join([f"{key} = ?" for key in where])
        params = tuple(data.values()) + tuple(where.values())
        await db.execute(
            f"UPDATE {self.name} SET {set_clause} WHERE {conditions}", params
        )
        await db.commit()
        # total_changes might not be reliable for selected rows, it's for the connection.
        # For specific feedback, one might need to count rows before/after or use specific SQL.
        # For now, let's return the number of changes in the last operation.
        # This is an attribute of the connection, not the cursor.
        return (
            db.total_changes
        )  # This might reflect total changes on the connection since open, or last commit.
        # For a more precise "rows affected by this statement", it's db specific.
        # aiosqlite's cursor.rowcount is often -1 for non-select.
        # Let's assume for now the user wants to know if *something* changed.

    async def delete(self, db, where: dict):
        if not where:
            raise ValueError(
                "Where clause cannot be empty for delete operation."
            )
        conditions = " AND ".join([f"{key} = ?" for key in where])
        params = tuple(where.values())
        await db.execute(f"DELETE FROM {self.name} WHERE {conditions}", params)
        await db.commit()
        return (
            db.total_changes
        )  # Similar to update, returns total changes on the connection.


async def load_module(jarvis_instance):
    """Loads the SQL interface module and sets up the notes table."""
    print("Loading SQL interface module...")
    if (
        not jarvis_instance.sql_db or jarvis_instance.sql_db._closed
    ):  # Check if connection exists and is open
        jarvis_instance.sql_db = await aiosqlite.connect(DATABASE_FILE)

    jarvis_instance.notes_table = Table(
        "notes",
        [
            {"name": "id", "type": "INTEGER", "primary_key": True},
            {"name": "title", "type": "TEXT", "not_null": True},
            {"name": "content", "type": "TEXT"},
            {
                "name": "created_at",
                "type": "DATETIME",
                "not_null": True,
                "default": "CURRENT_TIMESTAMP",
            },  # Added default
        ],
    )
    await jarvis_instance.notes_table.create(jarvis_instance.sql_db)
    print(
        f"SQL interface module loaded. Database: {DATABASE_FILE}. Available commands: "
        + ", ".join(commands.keys())
    )


async def close_module(jarvis_instance):
    """Closes the database connection when the module is unloaded."""
    if (
        hasattr(jarvis_instance, "sql_db")
        and jarvis_instance.sql_db
        and not jarvis_instance.sql_db._closed
    ):
        await jarvis_instance.sql_db.close()
        jarvis_instance.sql_db = None  # Clear the attribute
        print("SQL interface module connection closed.")


async def add_note_async(jarvis_instance, args: str):
    """Adds a new note. Usage: add_note <title> <content_separated_by_space>"""
    parts = args.split(" ", 1)
    if len(parts) == 2:
        title, content = parts
        # created_at will be handled by table.insert or database default
        note_data = {"title": title, "content": content}
        try:
            note_id = await jarvis_instance.notes_table.insert(
                jarvis_instance.sql_db, note_data
            )
            return f"Note '{title}' added with ID: {note_id}"
        except Exception as e:
            return f"Error adding note: {e}"
    else:
        return "Usage: add_note <title> <content>"


async def list_notes_async(jarvis_instance, args: str):
    """Lists note IDs and titles. Optional: <limit> (e.g., list_notes 5)"""
    limit = None
    if args:
        try:
            limit = int(args)
        except ValueError:
            return "Invalid limit. Usage: list_notes [number]"

    notes = await jarvis_instance.notes_table.select(
        jarvis_instance.sql_db,
        columns=["id", "title", "created_at"],
        limit=limit,
        order_by="created_at DESC",
    )
    if notes:
        output = "--- Notes ---"
        for note in notes:
            output += f"\nID: {note['id']}, Title: {note['title']} (Created: {note['created_at']})"
        output += "\n-------------"
        return output
    else:
        return "No notes found."


async def view_note_async(jarvis_instance, args: str):
    """Views a note by ID. Usage: view_note <note_id>"""
    try:
        note_id = int(args)
        notes = await jarvis_instance.notes_table.select(
            jarvis_instance.sql_db, where={"id": note_id}
        )
        if notes:
            note = notes[0]
            output = f"--- Note ID: {note['id']} ---"
            output += f"\nTitle: {note['title']}"
            output += f"\nCreated At: {note['created_at']}"
            output += f"\nContent:\n{note['content']}"
            output += "\n----------------------"
            return output
        else:
            return f"Note with ID {note_id} not found."
    except ValueError:
        return "Usage: view_note <note_id> (ID must be a number)"
    except Exception as e:
        return f"Error viewing note: {e}"


async def edit_note_async(jarvis_instance, args: str):
    """Edits a note's title or content. Usage: edit_note <note_id> <title|content> <new_value>"""
    parts = args.split(" ", 2)
    if len(parts) == 3:
        try:
            note_id = int(parts[0])
            field = parts[1].lower()
            new_value = parts[2]
            if field in ["title", "content"]:
                await jarvis_instance.notes_table.update(
                    jarvis_instance.sql_db, {field: new_value}, {"id": note_id}
                )
                # db.total_changes is cumulative for the connection.
                # To check if this specific update worked, we'd need to select or use a more specific row count.
                # For now, if no error, assume it worked if ID exists.
                # A better check: query the note after update or check if 'changes' from update method is > 0.
                # For aiosqlite, after an UPDATE, the cursor.rowcount is usually -1.
                # We can re-fetch the note to confirm.
                # Simpler: check if note exists before update.
                existing_notes = await jarvis_instance.notes_table.select(
                    jarvis_instance.sql_db, where={"id": note_id}, limit=1
                )
                if not existing_notes:
                    return f"Note with ID {note_id} not found."
                return f"Note ID {note_id} '{field}' updated successfully."
            else:
                return "Error: Field must be 'title' or 'content'."
        except ValueError:
            return "Usage: edit_note <note_id> <field> <new_value> (ID must be a number)"
        except Exception as e:
            return f"Error editing note: {e}"
    else:
        return "Usage: edit_note <note_id> <field_to_edit: title|content> <new_value>"


async def delete_note_async(jarvis_instance, args: str):
    """Deletes a note by ID. Usage: delete_note <note_id>"""
    try:
        note_id = int(args)
        # Check if note exists before deleting
        existing_notes = await jarvis_instance.notes_table.select(
            jarvis_instance.sql_db, where={"id": note_id}, limit=1
        )
        if not existing_notes:
            return f"Note with ID {note_id} not found."

        await jarvis_instance.notes_table.delete(
            jarvis_instance.sql_db, {"id": note_id}
        )
        return f"Note ID {note_id} deleted successfully."
    except ValueError:
        return "Usage: delete_note <note_id> (ID must be a number)"
    except Exception as e:
        return f"Error deleting note: {e}"


async def sql_query_async(jarvis_instance, query: str):
    """Executes a raw SQL query. Use with extreme caution. Usage: sql <your_query>"""
    if not query:
        return "Error: SQL query cannot be empty."
    try:
        # For SELECT queries
        if query.strip().upper().startswith("SELECT"):
            async with jarvis_instance.sql_db.execute(query) as cursor:
                results = await cursor.fetchall()
                if results:
                    column_names = [
                        description[0] for description in cursor.description
                    ]
                    # Pretty print JSON might be too much for simple CLI, use basic formatting.
                    output = "--- SQL Query Results ---\n"
                    output += ", ".join(column_names) + "\n"
                    output += "-" * (len(", ".join(column_names))) + "\n"
                    for row in results:
                        output += ", ".join(map(str, row)) + "\n"
                    output += "--- End of Results ---"
                    return output
                else:
                    return "Query executed, no results returned."
        else:  # For INSERT, UPDATE, DELETE, etc.
            cursor = await jarvis_instance.sql_db.execute(query)
            await jarvis_instance.sql_db.commit()
            return f"Query executed successfully. Rows affected: {cursor.rowcount if cursor.rowcount != -1 else 'unknown (use SELECT to verify)'}."

    except aiosqlite.Error as e:
        return f"SQLite error: {e}"
    except Exception as e:
        return f"Error executing SQL query: {e}"


commands = {
    "add_note": add_note_async,
    "list_notes": list_notes_async,
    "view_note": view_note_async,
    "edit_note": edit_note_async,
    "delete_note": delete_note_async,
    "sql": sql_query_async,
}
