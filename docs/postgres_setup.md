# PostgreSQL Setup for Jarvis

This document describes how to initialise the improved database schema for
managing Jarvis users. The schema file `jarvis_users_pg.sql` defines all tables,
indexes, triggers and materialised views. Use it to create the database on a
PostgreSQL server.

```bash
psql -d your_database -f docs/jarvis_users_pg.sql
```

The schema separates authentication tokens and audit logs into dedicated tables
and uses JSONB columns with GIN indexes for efficient queries. A full-text
search vector is generated from usernames to allow quick lookup.

After setting up the database you can connect from Jarvis using the optional
`postgres_interface` module.
