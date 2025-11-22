"""Run an idempotent ALTER TABLE to add annual_leave_allocation column.
This script connects directly to the database without importing the Flask app.
"""
from sqlalchemy import create_engine, text

DB_URI = 'mysql://root:root@localhost/hrportal'

sql = """
ALTER TABLE `user`
  ADD COLUMN `annual_leave_allocation` INT NOT NULL DEFAULT 30;
"""
engine = create_engine(DB_URI)
check_sql = text("SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = 'user' AND COLUMN_NAME = 'annual_leave_allocation';")
with engine.connect() as conn:
  schema = engine.url.database
  exists = conn.execute(check_sql, {'schema': schema}).scalar()

if exists:
  print('Column already exists; nothing to do')
else:
  print('Column not present; adding column...')
  with engine.begin() as conn:
    conn.execute(text(sql))
  print('ALTER TABLE executed successfully')
