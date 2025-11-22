"""Idempotently add first_name and last_name columns to `user` table.
Connects directly to the database without importing the Flask app to avoid
model import issues before migration.
"""
from sqlalchemy import create_engine, text

DB_URI = 'mysql://root:root@localhost/hrportal'

CHECK_SQL = text(
    """
    SELECT COLUMN_NAME FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = 'user'
      AND COLUMN_NAME IN ('first_name','last_name');
    """
)

ADD_FIRST_SQL = "ALTER TABLE `user` ADD COLUMN `first_name` VARCHAR(50) NULL;"
ADD_LAST_SQL = "ALTER TABLE `user` ADD COLUMN `last_name` VARCHAR(50) NULL;"

def main():
    engine = create_engine(DB_URI)
    with engine.connect() as conn:
        schema = engine.url.database
        existing = {row[0] for row in conn.execute(CHECK_SQL, {'schema': schema})}

        to_add = []
        if 'first_name' not in existing:
            to_add.append(('first_name', ADD_FIRST_SQL))
        if 'last_name' not in existing:
            to_add.append(('last_name', ADD_LAST_SQL))

        if not to_add:
            print('Columns already exist; nothing to do')
            return

        print('Adding columns:', ', '.join(name for name, _ in to_add))
        with engine.begin() as conn_tx:
            for name, sql in to_add:
                conn_tx.execute(text(sql))
                print(f'Added column: {name}')
        print('ALTER TABLE executed successfully')

if __name__ == '__main__':
    main()