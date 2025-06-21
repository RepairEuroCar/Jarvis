# PostgreSQL Setup for Jarvis

This document describes how to initialise the improved database schema fo
managing Jarvis users and learning topics. The file `jarvis_users_pg.sql`
defines all user tables, indexes, triggers and materialised views. The
supplementary file `jarvis_topics_pg.sql` adds the topic catalogue and related
tables. These scripts can be executed manually, but the `postgres_interface`
module will also run them automatically when loaded.

```bash
psql -d your_database -f docs/jarvis_users_pg.sql
psql -d your_database -f docs/jarvis_topics_pg.sql
```

The schema separates authentication tokens and audit logs into dedicated tables
and uses JSONB columns with GIN indexes for efficient queries. A full-text
search vector is generated from usernames to allow quick lookup.

After setting up the database you can connect from Jarvis using the optional
`postgres_interface` module.
