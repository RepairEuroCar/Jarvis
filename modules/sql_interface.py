"""SQLite interface module for Jarvis."""

import asyncio
import datetime
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiosqlite

logger = logging.getLogger(__name__)

DATABASE_FILE = "jarvis_data.db"


class Table:
    """ORM-like interface for SQLite tables."""
    
    def __init__(self, name: str, columns: List[Dict[str, Any]]) -> None:
        self.name = name
        self.columns = columns
        self._lock = asyncio.Lock()

    async def create(self, db: aiosqlite.Connection) -> None:
        """Create the table if it doesn't exist."""
        column_defs = ", ".join(
            f"{col['name']} {col['type']}"
            f"{' PRIMARY KEY AUTOINCREMENT' if col.get('primary_key') else ''}"
            f"{' NOT NULL' if col.get('not_null') else ''}"
            for col in self.columns
        )
        
        async with self._lock:
            await db.execute(
                f"CREATE TABLE IF NOT EXISTS {self.name} ({column_defs})"
            )
            await db.commit()

    async def insert(self, db: aiosqlite.Connection, data: Dict) -> Union[int, None]:
        """Insert data into the table."""
        cols = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        
        # Ensure created_at is set if required
        if ("created_at" in [col["name"] for col in self.columns 
            if col.get("not_null")] and "created_at" not in data):
            if any(
                col["name"] == "created_at" and col["type"].upper() == "DATETIME"
                for col in self.columns
            ):
                data["created_at"] = datetime.datetime.now().isoformat()

        async with self._lock:
            await db.execute(
                f"INSERT INTO {self.name} ({cols}) VALUES ({placeholders})",
                tuple(data.values()),
            )
            await db.commit()
            
            async with db.execute("SELECT last_insert_rowid()") as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def select(
        self,
        db: aiosqlite.Connection,
        where: Optional[Dict] = None,
        limit: Optional[int] = None,
        columns: Optional[List[str]] = None,
        order_by: Optional[str] = None,
    ) -> List[Dict]:
        """Select data from the table."""
        select_cols = ", ".join(columns) if columns else "*"
        query = f"SELECT {select_cols} FROM {self.name}"
        params = []
        
        if where:
            conditions = " AND ".join([f"{key} = ?" for key in where])
            query += f" WHERE {conditions}"
            params.extend(list(where.values()))
            
        if order_by:
            query += f" ORDER BY {order_by}"
            
        if limit:
            query += " LIMIT ?"
            params.append(limit)

        async with self._lock:
            async with db.execute(query, tuple(params)) as cursor:
                columns_desc = [desc[0] for desc in cursor.description]
                return [
                    dict(zip(columns_desc, row)) 
                    async for row in cursor
                ]

    async def update(
        self, 
        db: aiosqlite.Connection, 
        data: Dict, 
        where: Dict
    ) -> int:
        """Update records in the table."""
        if not data or not where:
            raise ValueError(
                "Data and where clause cannot be empty for update operation."
            )
            
        set_clause = ", ".join([f"{key} = ?" for key in data])
        conditions = " AND ".join([f"{key} = ?" for key in where])
        params = tuple(data.values()) + tuple(where.values())
        
        async with self._lock:
            await db.execute(
                f"UPDATE {self.name} SET {set_clause} WHERE {conditions}", 
                params
            )
            await db.commit()
            
        return db.total_changes

    async def delete(self, db: aiosqlite.Connection, where: Dict) -> int:
        """Delete records from the table."""
        if not where:
            raise ValueError(
                "Where clause cannot be empty for delete operation."
            )
            
        conditions = " AND ".join([f"{key} = ?" for key in where])
        params = tuple(where.values())
        
        async with self._lock:
            await db.execute(
                f"DELETE FROM {self.name} WHERE {conditions}", 
                params
            )
            await db.commit()
            
        return db.total_changes


async def load_module(jarvis_instance: Any) -> None:
    """Initialize SQL interface module."""
    print("Loading SQL interface module...")
    
    if (
        not jarvis_instance.sql_db 
        or jarvis_instance.sql_db._closed
    ):
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
            },
        ],
    )
    
    await jarvis_instance.notes_table.create(jarvis_instance.sql_db)
    print(
        f"SQL interface module loaded. Database: {DATABASE_FILE}. "
        f"Available commands: {', '.join(commands.keys())}"
    )


async def close_module(jarvis_instance: Any) -> None:
    """Close database connection on module unload."""
    if (
        hasattr(jarvis_instance, "sql_db")
        and jarvis_instance.sql_db
        and not jarvis_instance.sql_db._closed
    ):
        await jarvis_instance.sql_db.close()
        jarvis_instance.sql_db = None
        print("SQL interface module connection closed.")


async def add_note_async(jarvis_instance: Any, args: str) -> str:
    """Add a new note."""
    parts = args.split(" ", 1)
    if len(parts) == 2:
        title, content = parts
        note_data = {"title": title, "content": content}
        
        try:
            note_id = await jarvis_instance.notes_table.insert(
                jarvis_instance.sql_db, 
                note_data
            )
            return f"Note '{title}' added with ID: {note_id}"
        except Exception as e:
            return f"Error adding note: {e}"
    else:
        return "Usage: add_note <title> <content>"


async def list_notes_async(jarvis_instance: Any, args: str) -> str:
    """List all notes."""
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
    
    if not notes:
        return "No notes found."
        
    output = ["--- Notes ---"]
    for note in notes:
        output.append(
            f"ID: {note['id']}, Title: {note['title']} "
            f"(Created: {note['created_at']})"
        )
    output.append("-------------")
    
    return "\n".join(output)


async def view_note_async(jarvis_instance: Any, args: str) -> str:
    """View a specific note."""
    try:
        note_id = int(args)
        notes = await jarvis_instance.notes_table.select(
            jarvis_instance.sql_db, 
            where={"id": note_id}
        )
        
        if not notes:
            return f"Note with ID {note_id} not found."
            
        note = notes[0]
        output = [
            f"--- Note ID: {note['id']} ---",
            f"Title: {note['title']}",
            f"Created At: {note['created_at']}",
            f"Content:\n{note['content']}",
            "----------------------"
        ]
        
        return "\n".join(output)
    except ValueError:
        return "Usage: view_note <note_id> (ID must be a number)"
    except Exception as e:
        return f"Error viewing note: {e}"


async def edit_note_async(jarvis_instance: Any, args: str) -> str:
    """Edit an existing note."""
    parts = args.split(" ", 2)
    if len(parts) == 3:
        try:
            note_id = int(parts[0])
            field = parts[1].lower()
            new_value = parts[2]
            
            if field in ["title", "content"]:
                await jarvis_instance.notes_table.update(
                    jarvis_instance.sql_db,
                    {field: new_value},
                    {"id": note_id}
                )
                
                # Verify note exists
                existing_notes = await jarvis_instance.notes_table.select(
                    jarvis_instance.sql_db, 
                    where={"id": note_id}, 
                    limit=1
                )
                
                if not existing_notes:
                    return f"Note with ID {note_id} not found."
                    
                return f"Note ID {note_id} '{field}' updated successfully."
            else:
                return "Error: Field must be 'title' or 'content'."
        except ValueError:
            return "Usage: edit_note <note_id> <field> <new_value>"
        except Exception as e:
            return f"Error editing note: {e}"
    else:
        return (
            "Usage: edit_note <note_id> <field_to_edit: title|content> "
            "<new_value>"
        )


async def delete_note_async(jarvis_instance: Any, args: str) -> str:
    """Delete a note by ID."""
    try:
        note_id = int(args)
        # Check if note exists before deleting
        existing_notes = await jarvis_instance.notes_table.select(
            jarvis_instance.sql_db, 
            where={"id": note_id}, 
            limit=1
        )
        if not existing_notes:
            return f"Note with ID {note_id} not found."

        await jarvis_instance.notes_table.delete(
            jarvis_instance.sql_db, 
            {"id": note_id}
        )
        return f"Note ID {note_id} deleted successfully."
    except ValueError:
        return "Usage: delete_note <note_id> (ID must be a number)"
    except Exception as e:
        return f"Error deleting note: {e}"


async def sql_query_async(jarvis_instance: Any, query: str) -> str:
    """Execute raw SQL query."""
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
            return (
                f"Query executed successfully. "
                f"Rows affected: {cursor.rowcount if cursor.rowcount != -1 else 'unknown'}"
            )
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


async def health_check() -> bool:
    """Check ability to open a sqlite database."""
    try:
        async with aiosqlite.connect(DATABASE_FILE) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS hc(id INTEGER)")
        return True
    except Exception as exc:
        logger.warning("SQL interface health check failed: %s", exc)
        return False