---
name: database
description: "Database conventions and migration rules"
---
# Database Conventions

## Schema
Use snake_case for all table and column names.
Every table must have a primary key and created_at/updated_at timestamps.

## Migrations
Migrations must be reversible.
Never drop a column in the same release that stops writing to it.
Use expand-and-contract for breaking schema changes.
