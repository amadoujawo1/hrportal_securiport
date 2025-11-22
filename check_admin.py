#!/usr/bin/env python
from models import User
from main import app

app.app_context().push()

# Check admin user
admin = User.query.filter_by(username='admin').first()
if admin:
    print(f"Admin User Found:")
    print(f"  Username: {admin.username}")
    print(f"  Name: {admin.name}")
    print(f"  Password (raw): {admin.password}")
    print(f"  Is Admin: {admin.is_admin}")
    print(f"  Is HR: {admin.is_hr}")
    print(f"  Password match 'Admin@123': {admin.password == 'Admin@123'}")
else:
    print("No admin user found!")
