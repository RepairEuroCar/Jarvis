# PostgreSQL Setup for Jarvis

This document describes how to initialise the improved database schema for
managing Jarvis users and topics. Two schema files are provided:
`jarvis_users_pg.sql` and `jarvis_topics_pg.sql`. They define all tables,
indexes, triggers and materialised views. Use them to create the database on a
PostgreSQL server.

```bash
psql -d your_database -f docs/jarvis_users_pg.sql
psql -d your_database -f docs/jarvis_topics_pg.sql
```

The schema separates authentication tokens and audit logs into dedicated tables
and uses JSONB columns with GIN indexes for efficient queries. A full-text
search vector is generated from usernames to allow quick lookup.

After setting up the database you can connect from Jarvis using the optional
`postgres_interface` module.
