# RampCoreOs

Start server with python run.py
Server uses cors and CSRF tokens for security and cookies

## Database setup

Run `SQL_Setup.sql` in MySQL to create the database and tables. It includes
the `value_sources` table for field-level source tracking, so fresh installations
do not need to run `scripts/migrate_provenance.py` separately.
