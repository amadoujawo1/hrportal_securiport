"""Idempotently add must_change_password column to `user` table.
Connects directly to the database similar to other schema update scripts.
"""
from sqlalchemy import create_engine, text

DB_URI = 'mysql://root:root@localhost/hrportal'

CHECK_SQL = text(
    """
    SELECT COLUMN_NAME FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = 'user'
      AND COLUMN_NAME = 'must_change_password';
    """
)

ADD_SQL = "ALTER TABLE `user` ADD COLUMN `must_change_password` TINYINT(1) NULL DEFAULT 0;"

def main():
    engine = create_engine(DB_URI)
    with engine.connect() as conn:
        schema = engine.url.database
        existing = {row[0] for row in conn.execute(CHECK_SQL, {'schema': schema})}
        if 'must_change_password' in existing:
            print('Column must_change_password already exists; nothing to do')
            return

        print('Adding column: must_change_password')
        with engine.begin() as conn_tx:
            conn_tx.execute(text(ADD_SQL))
            print('Added column: must_change_password')
        print('ALTER TABLE executed successfully')

if __name__ == '__main__':
    main()