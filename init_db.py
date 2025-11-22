from sqlalchemy import create_engine, text

try:
    # Create engine without database name first
    engine = create_engine('mysql://jawo:abc_123@localhost/')
    
    # Connect and create database
    with engine.connect() as conn:
        conn.execute(text('CREATE DATABASE IF NOT EXISTS hrportal'))
        print('Database created successfully!')
        
    # Create engine with database name and initialize tables
    db_engine = create_engine('mysql://jawo:abc_123@localhost/hrportal')
    with db_engine.connect() as conn:
        print('Connected to database successfully!')
        
except Exception as e:
    print(f'Error: {str(e)}')