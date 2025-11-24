
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, make_response, Response
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from datetime import datetime
from functools import wraps
from flask_socketio import SocketIO, emit
from flask_migrate import Migrate
from database import db
from models import User, Leave, Document, Notification
from utils import save_document, delete_document, allowed_file, UPLOAD_FOLDER, requires_admin
from email_service import send_email
import os
from dotenv import load_dotenv

load_dotenv()

HR_EMAIL = os.getenv('HR_EMAIL')
from io import StringIO, BytesIO
import csv
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SQLALCHEMY_POOL_RECYCLE'] = 280
app.config['SQLALCHEMY_POOL_TIMEOUT'] = 20
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_POOL_SIZE'] = 10
app.config['SQLALCHEMY_MAX_OVERFLOW'] = 5
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

socketio = SocketIO(app)

db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Initialize database and create admin user if needed
def init_database():
    with app.app_context():
        # Create all tables if they don't exist
        db.create_all()
        
        # Initialize migrations
        migrate.init_app(app, db)
        
        # Create admin user if it doesn't exist
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', name='Administrator', employee_id='ADMIN001', password='Admin@123', is_admin=True, is_hr=True, department='IT Department')
            db.session.add(admin)
            db.session.commit()
        
        # Update existing users to have a default name if they don't have one
        users = User.query.all()
        for user in users:
            if not hasattr(user, 'name') or not user.name:
                user.name = user.username
                db.session.add(user)
        db.session.commit()

# Initialize database
init_database()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            department = request.form.get('department', '').strip()
            employee_id = request.form.get('employee_id', '').strip()
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            # Normalize is_hr (form may send '1'/'0' or 'true'/'false')
            is_hr_raw = request.form.get('is_hr')
            is_hr = str(is_hr_raw).lower() in ('1', 'true', 'yes', 'on')
            # Parse is_active checkbox if provided (checkbox sends 'on' when checked)
            is_active_raw = request.form.get('is_active')
            is_active = str(is_active_raw).lower() in ('1', 'true', 'yes', 'on') if is_active_raw is not None else True
            
            # Validate required fields
            if not username:
                flash('Username is required', 'error')
                return redirect(url_for('register'))
            
            if not password:
                flash('Password is required', 'error')
                return redirect(url_for('register'))
            
            if not employee_id:
                flash('Employee ID is required', 'error')
                return redirect(url_for('register'))
            
            full_name = username
            if first_name and last_name:
                full_name = f"{first_name} {last_name}"
            elif first_name:
                full_name = first_name
            elif last_name:
                full_name = last_name
            
            if User.query.filter_by(username=username).first():
                flash('Username already exists', 'error')
                return redirect(url_for('register'))
                
            if User.query.filter_by(employee_id=employee_id).first():
                flash('Employee ID already exists', 'error')
                return redirect(url_for('register'))
            
            user = User(username=username, password=password, department=department, employee_id=employee_id, is_hr=is_hr, is_active=is_active, name=full_name, first_name=first_name or None, last_name=last_name or None, must_change_password=True)
            db.session.add(user)
            db.session.commit()
            flash('User registration successful!', 'success')
            return redirect(url_for('admin'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error registering user: {str(e)}', 'error')
            return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            
            if not username or not password:
                flash('Username and password are required', 'error')
                return redirect(url_for('login'))
            
            user = User.query.filter_by(username=username).first()
            
            if user and user.password == password:  # In production, use proper password hashing
                login_user(user)
                try:
                    if getattr(user, 'must_change_password', False):
                        return redirect(url_for('change_password'))
                except Exception:
                    pass
                return redirect(url_for('dashboard'))
            flash('Invalid username or password', 'error')
        except Exception as e:
            flash(f'Login error: {str(e)}', 'error')
    return render_template('login.html')

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        try:
            new_password = request.form.get('password', '').strip()
            confirm_password = request.form.get('confirm_password', '').strip()
            if not new_password or not confirm_password:
                flash('Password and confirmation are required', 'error')
                return redirect(url_for('change_password'))
            if new_password != confirm_password:
                flash('Passwords do not match', 'error')
                return redirect(url_for('change_password'))
            if len(new_password) < 6:
                flash('Password must be at least 6 characters', 'error')
                return redirect(url_for('change_password'))
            current_user.password = new_password
            try:
                if hasattr(current_user, 'must_change_password'):
                    current_user.must_change_password = False
            except Exception:
                pass
            db.session.commit()
            flash('Password changed successfully', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error changing password: {str(e)}', 'error')
            return redirect(url_for('change_password'))
    return render_template('change_password.html')

@app.route('/admin/add-user', methods=['POST'])
@login_required
@requires_admin
def add_user():
    try:
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        department = request.form.get('department', 'General').strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        is_hr = 'is_hr' in request.form
        
        # Validate required fields
        if not username:
            flash('Username is required', 'error')
            return redirect(url_for('admin'))
        
        if not password:
            flash('Password is required', 'error')
            return redirect(url_for('admin'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('admin'))
        
        # Generate employee ID based on department and current timestamp
        dept_prefix = ''.join(word[0].upper() for word in department.split()) if department else 'GEN'
        timestamp = datetime.now().strftime('%y%m%d%H%M')
        employee_id = f"{dept_prefix}{timestamp}"
        
        # Ensure employee_id is unique
        while User.query.filter_by(employee_id=employee_id).first():
            timestamp = str(int(timestamp) + 1)
            employee_id = f"{dept_prefix}{timestamp}"
        
        full_name = username
        if first_name and last_name:
            full_name = f"{first_name} {last_name}"
        elif first_name:
            full_name = first_name
        elif last_name:
            full_name = last_name
        user = User(username=username, password=password, department=department, employee_id=employee_id, is_hr=is_hr, name=full_name, first_name=first_name or None, last_name=last_name or None, must_change_password=True)
        db.session.add(user)
        db.session.commit()
        flash(f'User added successfully with Employee ID: {employee_id}', 'success')
        return redirect(url_for('admin'))
    
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding user: {str(e)}', 'error')
        return redirect(url_for('admin'))


@app.route('/admin/check-username')
@login_required
@requires_admin
def admin_check_username():
    """Admin-only endpoint to check whether a username is available.
    Returns JSON: { available: true/false }
    """
    username = request.args.get('username', '').strip()
    if not username:
        return jsonify({'available': False, 'message': 'Username required'})
    exists = User.query.filter_by(username=username).first() is not None
    return jsonify({'available': not exists})


@app.route('/admin/check-employee-id')
@login_required
@requires_admin
def admin_check_employee_id():
    """Admin-only endpoint to check whether an employee_id is available.
    Returns JSON: { available: true/false }
    """
    employee_id = request.args.get('employee_id', '').strip()
    if not employee_id:
        return jsonify({'available': False, 'message': 'Employee ID required'})
    exists = User.query.filter_by(employee_id=employee_id).first() is not None
    return jsonify({'available': not exists})

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/profile')
@login_required
def profile():
    total_leaves = Leave.query.filter_by(user_id=current_user.id).count()
    approved_leaves = Leave.query.filter_by(user_id=current_user.id, status='Approved').count()
    pending_leaves = Leave.query.filter_by(user_id=current_user.id, status='Pending').count()
    rejected_leaves = Leave.query.filter_by(user_id=current_user.id, status='Rejected').count()
    
    return render_template('profile.html',
                           total_leaves=total_leaves,
                           approved_leaves=approved_leaves,
                           pending_leaves=pending_leaves,
                           rejected_leaves=rejected_leaves)

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    name = request.form.get('name')
    if name:
        current_user.name = name
        db.session.commit()
        flash('Profile updated successfully', 'success')
    else:
        flash('Name cannot be empty', 'error')
    return redirect(url_for('profile'))

def requires_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.get_is_admin():
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin')
@login_required
@requires_admin
def admin():
    users = User.query.all()
    leaves = Leave.query.order_by(Leave.created_at.desc()).all()
    total_leaves = len(leaves)
    approved_leaves = len([leave for leave in leaves if leave.status == 'Approved'])
    pending_leaves = len([leave for leave in leaves if leave.status == 'Pending'])
    rejected_leaves = len([leave for leave in leaves if leave.status == 'Rejected'])
    # System-wide stats for admin panel
    from datetime import datetime
    current_year = datetime.now().year
    # Count active employees
    try:
        total_employees = User.query.filter_by(is_active=True).count()
    except Exception:
        total_employees = User.query.count()

    # Sum approved leave days for current year across all users
    admin_used_leaves_this_year = 0
    approved_all = [l for l in leaves if l.status == 'Approved']
    for l in approved_all:
        try:
            if l.start_date.year == current_year:
                admin_used_leaves_this_year += (l.end_date - l.start_date).days + 1
        except Exception:
            continue

    total_annual_leaves = 30
    admin_total_leave_balance = (total_annual_leaves * (total_employees or 0)) - admin_used_leaves_this_year

    user_stats = {}
    try:
        per_user_days = {}
        for l in approved_all:
            try:
                if l.start_date.year == current_year:
                    d = (l.end_date - l.start_date).days + 1
                    per_user_days[l.user_id] = (per_user_days.get(l.user_id, 0) + d)
            except Exception:
                continue
        for u in users:
            used = per_user_days.get(u.id, 0)
            alloc = u.annual_leave_allocation if u.annual_leave_allocation is not None else 30
            remaining = alloc - used
            if remaining < 0:
                remaining = 0
            user_stats[u.id] = {'used': used, 'remaining': remaining}
    except Exception:
        pass

    return render_template('admin.html', users=users, leaves=leaves,
                         total_leaves=total_leaves,
                         approved_leaves=approved_leaves,
                         pending_leaves=pending_leaves,
                         rejected_leaves=rejected_leaves,
                         admin_total_leave_balance=admin_total_leave_balance,
                         admin_used_leaves_this_year=admin_used_leaves_this_year,
                         admin_total_employees=total_employees,
                         user_stats=user_stats,
                         current_year=current_year)

@app.route('/admin/toggle-role/<int:user_id>', methods=['POST'])
@login_required
@requires_admin
def toggle_user_role(user_id):
    user = User.query.get_or_404(user_id)
    if user == current_user:
        flash('Cannot modify your own role', 'error')
    else:
        user.is_hr = not user.is_hr
        db.session.commit()
        flash('User role updated successfully', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/toggle-status/<int:user_id>', methods=['POST'])
@login_required
@requires_admin
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    if user == current_user:
        flash('Cannot modify your own status', 'error')
    else:
        user.is_active = not user.is_active
        db.session.commit()
        flash('User status updated successfully', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/reset-password/<int:user_id>', methods=['POST'])
@login_required
@requires_admin
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    if user == current_user:
        flash('Cannot reset your own password', 'error')
    else:
        user.password = 'password123'  # In production, use a secure password generator and proper hashing
        db.session.commit()
        flash('Password has been reset to: password123', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/edit-user/<int:user_id>', methods=['POST'])
@login_required
@requires_admin
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if user == current_user:
        flash('Cannot edit your own account', 'error')
        return redirect(url_for('admin'))
    try:
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        employee_id = request.form.get('employee_id', '').strip()
        department = request.form.get('department', '').strip()
        job_title = request.form.get('job_title', '').strip()
        is_hr_raw = request.form.get('is_hr')
        is_active_raw = request.form.get('is_active')

        user.first_name = first_name or None
        user.last_name = last_name or None
        if employee_id:
            user.employee_id = employee_id
        user.department = department or None
        user.job_title = job_title or None
        user.is_hr = str(is_hr_raw).lower() in ('1', 'true', 'yes', 'on')
        user.is_active = str(is_active_raw).lower() in ('1', 'true', 'yes', 'on')

        full_name = user.username
        if first_name and last_name:
            full_name = f"{first_name} {last_name}"
        elif first_name:
            full_name = first_name
        elif last_name:
            full_name = last_name
        user.name = full_name

        db.session.commit()
        flash('User updated successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating user: {str(e)}', 'error')
    return redirect(url_for('admin'))

@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
@login_required
@requires_admin
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user == current_user:
        flash('Cannot delete your own account', 'error')
    else:
        # Delete associated leaves first to maintain referential integrity
        Leave.query.filter_by(user_id=user_id).delete()
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/approve-leave/<int:leave_id>', methods=['POST'])
@login_required
@requires_admin
def approve_leave(leave_id):
    try:
        leave = Leave.query.get_or_404(leave_id)
        if (leave.leave_type or '').lower() == 'annual leave':
            try:
                requested_year = leave.start_date.year
                approved_annual = Leave.query.filter_by(user_id=leave.user_id, leave_type='Annual Leave', status='Approved').all()
                used_annual_days = 0
                for l in approved_annual:
                    try:
                        if l.start_date.year == requested_year:
                            used_annual_days += (l.end_date - l.start_date).days + 1
                    except Exception:
                        continue
                requested_days = (leave.end_date - leave.start_date).days + 1
                if used_annual_days + requested_days > 30:
                    flash('Cannot approve annual leave beyond remaining balance (30 days per year)', 'error')
                    return redirect(url_for('admin'))
            except Exception:
                pass
        leave.status = 'Approved'
        leave.updated_at = datetime.now()
        db.session.commit()
        # Email admin HR(s) about approval
        try:
            subject = 'Leave Request Approved'
            body = (
                f'A leave request has been approved.\n\n'
                f'Employee: {leave.employee_name} ({leave.employee_id})\n'
                f'Designation: {leave.designation}\n'
                f'Leave Type: {leave.leave_type}\n'
                f'Date Range: {leave.start_date} to {leave.end_date}\n'
                f'Duration: {leave.duration_days or 0} day(s)\n'
                f'Reason: {leave.reason}\n\n'
                f'View details in admin panel: {url_for("admin", _external=True)}\n'
            )
            send_email(HR_EMAIL, subject, body)
        except Exception as e:
            print(f'[email] Error while sending approval notification: {e}')
        
        # Email the employee about approval
        try:
            user_email = leave.employee.username
            subject = 'Leave Request Approved'
            body = (
                f'Dear {leave.employee_name},\n\n'
                f'Your leave request has been APPROVED.\n\n'
                f'Leave Type: {leave.leave_type}\n'
                f'Date Range: {leave.start_date} to {leave.end_date}\n'
                f'Duration: {leave.duration_days or 0} day(s)\n\n'
                f'You can view the status in your dashboard: {url_for("dashboard", _external=True)}\n'
            )
            send_email(user_email, subject, body)
        except Exception as e:
            print(f'[email] Error while sending user approval notification: {e}')

        flash(f'Leave request from {leave.employee_name} has been approved', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error approving leave: {str(e)}', 'error')
    return redirect(url_for('admin'))

@app.route('/admin/reject-leave/<int:leave_id>', methods=['POST'])
@login_required
@requires_admin
def reject_leave(leave_id):
    try:
        leave = Leave.query.get_or_404(leave_id)
        rejection_reason = request.form.get('rejection_reason', '').strip()
        leave.status = 'Rejected'
        leave.updated_at = datetime.now()
        db.session.commit()
        # Email admin HR(s) about rejection
        try:
            subject = 'Leave Request Rejected'
            body = (
                f'A leave request has been rejected.\n\n'
                f'Employee: {leave.employee_name} ({leave.employee_id})\n'
                f'Designation: {leave.designation}\n'
                f'Leave Type: {leave.leave_type}\n'
                f'Date Range: {leave.start_date} to {leave.end_date}\n'
                f'Duration: {leave.duration_days or 0} day(s)\n'
                f'Reason: {leave.reason}\n\n'
                f'{"Rejection Reason: " + rejection_reason + "\n\n" if rejection_reason else ""}'
                f'View details in admin panel: {url_for("admin", _external=True)}\n'
            )
            send_email(HR_EMAIL, subject, body)
        except Exception as e:
            print(f'[email] Error while sending rejection notification: {e}')

        # Email the employee about rejection
        try:
            user_email = leave.employee.username
            subject = 'Leave Request Rejected'
            body = (
                f'Dear {leave.employee_name},\n\n'
                f'Your leave request has been REJECTED.\n\n'
                f'Leave Type: {leave.leave_type}\n'
                f'Date Range: {leave.start_date} to {leave.end_date}\n'
                f'Duration: {leave.duration_days or 0} day(s)\n'
                f'{"Rejection Reason: " + rejection_reason + "\n" if rejection_reason else ""}\n'
                f'You can view the status in your dashboard: {url_for("dashboard", _external=True)}\n'
            )
            send_email(user_email, subject, body)
        except Exception as e:
            print(f'[email] Error while sending user rejection notification: {e}')

        if rejection_reason:
            flash(f'Leave request from {leave.employee_name} has been rejected. Reason: {rejection_reason}', 'success')
        else:
            flash(f'Leave request from {leave.employee_name} has been rejected', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error rejecting leave: {str(e)}', 'error')
    return redirect(url_for('admin'))

@app.route('/')
@login_required
def dashboard():
    query = Leave.query
    
    if not current_user.is_hr:
        query = query.filter_by(user_id=current_user.id)
    
    # Apply filters
    if request.args.get('start_date'):
        query = query.filter(Leave.start_date >= request.args.get('start_date'))
    if request.args.get('end_date'):
        query = query.filter(Leave.end_date <= request.args.get('end_date'))
    if request.args.get('employee_name'):
        query = query.filter(Leave.employee_name.ilike(f'%{request.args.get("employee_name")}%'))
    if request.args.get('designation'):
        query = query.filter(Leave.designation == request.args.get('designation'))
    if request.args.get('status'):
        query = query.filter(Leave.status == request.args.get('status'))
    
    # Get unique designations for the filter dropdown
    designations = db.session.query(Leave.designation).distinct().all()
    designations = [d[0] for d in designations if d[0]]
    
    leaves = query.all()
    
    # Calculate leave balance for current user
    total_leave_balance = 0
    used_leaves_this_year = 0
    
    # Get all approved and pending leaves for current user this year
    from datetime import datetime
    current_year = datetime.now().year
    user_leaves = Leave.query.filter_by(user_id=current_user.id).all()
    
    # Calculate days used (approved leaves only, this year)
    for leave in user_leaves:
        if leave.status == 'Approved' and leave.start_date.year == current_year:
            days_used = (leave.end_date - leave.start_date).days + 1
            used_leaves_this_year += days_used
    
    # Total annual leave allocation is 30 days (standard)
    total_annual_leaves = 30
    total_leave_balance = total_annual_leaves - used_leaves_this_year

    # If the current user is HR/admin, compute system-wide totals (across active employees)
    admin_total_leave_balance = None
    admin_used_leaves_this_year = None
    admin_total_employees = None
    if current_user.is_hr or current_user.is_admin:
        # Count active employees in the system
        try:
            admin_total_employees = User.query.filter_by(is_active=True).count()
        except Exception:
            admin_total_employees = User.query.count()

        # Sum used (approved) leave days for the current year across all users
        admin_used_leaves_this_year = 0
        all_leaves = Leave.query.filter(Leave.status == 'Approved').all()
        for leave in all_leaves:
            try:
                if leave.start_date.year == current_year:
                    days_used = (leave.end_date - leave.start_date).days + 1
                    admin_used_leaves_this_year += days_used
            except Exception:
                # skip malformed dates
                continue

        admin_total_leave_balance = (total_annual_leaves * (admin_total_employees or 0)) - admin_used_leaves_this_year
    
    # Calculate comprehensive statistics
    total_leaves = len(leaves)
    approved_leaves = len([leave for leave in leaves if leave.status == 'Approved'])
    pending_leaves = len([leave for leave in leaves if leave.status == 'Pending'])
    rejected_leaves = len([leave for leave in leaves if leave.status == 'Rejected'])
    
    # Calculate additional statistics
    total_employees = len(set(leave.employee_id for leave in leaves))
    
    # Calculate monthly statistics
    from datetime import datetime, timedelta
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    monthly_leaves = len([leave for leave in leaves 
                         if leave.start_date.month == current_month and 
                         leave.start_date.year == current_year])
    
    # Calculate upcoming leaves (next 7 days)
    next_week = datetime.now() + timedelta(days=7)
    upcoming_leaves = len([leave for leave in leaves 
                          if leave.start_date >= datetime.now().date() and 
                          leave.start_date <= next_week.date()])
    
    # Calculate leave trends and analytics
    # Weekly trend
    weekly_data = []
    for i in range(7):
        date_check = datetime.now() - timedelta(days=i)
        day_leaves = len([leave for leave in leaves 
                         if leave.start_date == date_check.date()])
        weekly_data.append({
            'date': date_check.strftime('%Y-%m-%d'),
            'day': date_check.strftime('%A'),
            'count': day_leaves
        })
    weekly_data.reverse()
    
    # Monthly trends for last 12 months
    monthly_data = []
    for i in range(12):
        month_date = datetime.now() - timedelta(days=30*i)
        month_name = month_date.strftime('%B %Y')
        month_count = len([leave for leave in leaves 
                          if leave.start_date.month == month_date.month and 
                          leave.start_date.year == month_date.year])
        monthly_data.append({
            'month': month_name,
            'count': month_count
        })
    monthly_data.reverse()
    
    # Department analytics
    department_stats = {}
    for leave in leaves:
        dept = leave.designation or 'General'
        if dept not in department_stats:
            department_stats[dept] = {'total': 0, 'approved': 0, 'pending': 0, 'rejected': 0}
        department_stats[dept]['total'] += 1
        # Safely handle status mapping
        status_lower = leave.status.lower()
        if status_lower in ['approved', 'pending', 'rejected']:
            department_stats[dept][status_lower] += 1
    
    # Leave type analytics
    leave_type_stats = {}
    for leave in leaves:
        leave_type = leave.leave_type or 'General'
        if leave_type not in leave_type_stats:
            leave_type_stats[leave_type] = {'total': 0, 'approved': 0, 'pending': 0, 'rejected': 0}
        leave_type_stats[leave_type]['total'] += 1
        # Safely handle status mapping
        status_lower = leave.status.lower()
        if status_lower in ['approved', 'pending', 'rejected']:
            leave_type_stats[leave_type][status_lower] += 1
    
    # Calculate approval rate and average processing time
    approval_rate = (approved_leaves / total_leaves * 100) if total_leaves > 0 else 0
    
    # Calculate average processing time for approved leaves (in hours)
    processing_times = []
    for leave in leaves:
        if leave.status == 'Approved' and hasattr(leave, 'updated_at') and hasattr(leave, 'created_at') and leave.updated_at and leave.created_at:
            processing_time = (leave.updated_at - leave.created_at).total_seconds() / 3600  # hours
            processing_times.append(processing_time)
    avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
    
    # Get recent activities (last 10 actions) with enhanced data
    recent_activities = []
    # Filter leaves that have created_at timestamp
    leaves_with_timestamps = [leave for leave in leaves if hasattr(leave, 'created_at') and leave.created_at]
    for leave in sorted(leaves_with_timestamps, key=lambda x: x.created_at, reverse=True)[:10]:
        activity_type = 'leave'
        if leave.status == 'Approved':
            activity_type = 'approval'
        elif leave.status == 'Rejected':
            activity_type = 'rejection'
        
        recent_activities.append({
            'employee_name': leave.employee_name,
            'action': f"Applied for {leave.leave_type} leave",
            'date': leave.created_at.strftime('%Y-%m-%d %H:%M') if hasattr(leave, 'created_at') and leave.created_at else 'N/A',
            'status': leave.status,
            'type': activity_type
        })
    
    return render_template('dashboard.html', 
                         leaves=leaves, 
                         designations=designations,
                         total_leaves=total_leaves,
                         approved_leaves=approved_leaves,
                         pending_leaves=pending_leaves,
                         rejected_leaves=rejected_leaves,
                         total_employees=total_employees,
                         monthly_leaves=monthly_leaves,
                         upcoming_leaves=upcoming_leaves,
                         weekly_data=weekly_data,
                         monthly_data=monthly_data,
                         department_stats=department_stats,
                         leave_type_stats=leave_type_stats,
                         approval_rate=round(approval_rate, 1),
                         avg_processing_time=round(avg_processing_time, 1),
                         recent_activities=recent_activities,
                         total_leave_balance=total_leave_balance,
                         used_leaves_this_year=used_leaves_this_year,
                         today=datetime.now().date())

@app.route('/apply-leave', methods=['GET', 'POST'])
@login_required
def apply_leave():
    from datetime import date
    today_date = date.today().strftime('%Y-%m-%d')
    if request.method == 'POST':
        try:
            # Get required fields with error handling
            start_date = datetime.strptime(request.form.get('start_date', today_date), '%Y-%m-%d')
            end_date = datetime.strptime(request.form.get('end_date', today_date), '%Y-%m-%d')
            reason = request.form.get('reason', '').strip()
            leave_type = request.form.get('leave_type', '').strip()
            
            # Get numeric fields with defaults
            try:
                duration_months = float(request.form.get('duration_months', 0))
            except (ValueError, TypeError):
                duration_months = 0
            
            try:
                duration_days = int(request.form.get('duration_days', 0))
            except (ValueError, TypeError):
                duration_days = 0
            
            # Get employee information
            employee_name = request.form.get('employee_name', current_user.name or current_user.username).strip()
            employee_id = request.form.get('employee_id', current_user.employee_id or f'EMP{current_user.id}').strip()
            designation = request.form.get('designation', 'Employee').strip()
            
            # Validate required fields
            if not reason:
                flash('Reason for leave is required', 'error')
                return redirect(url_for('apply_leave'))
            
            if not leave_type:
                flash('Leave type is required', 'error')
                return redirect(url_for('apply_leave'))

            if not employee_name:
                flash('Employee name is required', 'error')
                return redirect(url_for('apply_leave'))
            
            if not employee_id:
                flash('Employee ID is required', 'error')
                return redirect(url_for('apply_leave'))
            if leave_type.lower() == 'annual leave':
                try:
                    requested_year = start_date.year
                    annual_leaves = Leave.query.filter_by(user_id=current_user.id, leave_type='Annual Leave', status='Approved').all()
                    used_annual_days = 0
                    for l in annual_leaves:
                        try:
                            if l.start_date.year == requested_year:
                                used_annual_days += (l.end_date - l.start_date).days + 1
                        except Exception:
                            continue
                    if used_annual_days >= 30:
                        flash('Annual leave limit reached (30 days for the year)', 'error')
                        return redirect(url_for('apply_leave'))
                    requested_days = (end_date - start_date).days + 1
                    remaining = max(0, 30 - used_annual_days)
                    if requested_days > remaining:
                        flash(f'Annual leave request exceeds remaining balance: {remaining} day(s) left', 'error')
                        return redirect(url_for('apply_leave'))
                except Exception:
                    pass
            
            # Create leave record
            leave = Leave(start_date=start_date, end_date=end_date,
                         reason=reason, user_id=current_user.id,
                         employee_id=employee_id,
                         employee_name=employee_name,
                         designation=designation,
                         leave_type=leave_type,
                         duration_months=duration_months,
                         duration_days=duration_days)
            
            db.session.add(leave)
            db.session.commit()

            # Notify HR admin(s) via email
            try:
                subject = f"Leave Request from {employee_name}"
                body = (
                    f"Employee: {employee_name} ({employee_id})\n"
                    f"Designation: {designation}\n"
                    f"Leave Type: {leave_type}\n"
                    f"Date Range: {start_date.date()} to {end_date.date()}\n"
                    f"Duration: {duration_days or 0} day(s)\n"
                    f"Reason: {reason}\n\n"
                    f"Review and approve/reject here: {url_for('admin', _external=True)}\n"
                )
                send_email(HR_EMAIL, subject, body)
            except Exception as e:
                print(f'[email] Error while sending admin notification: {e}')
            
            # Handle document uploads
            # Handle document uploads
            uploaded_files = []
            if 'documents' in request.files:
                uploaded_files.extend(request.files.getlist('documents'))
            if 'documents[]' in request.files:
                uploaded_files.extend(request.files.getlist('documents[]'))
            
            if uploaded_files:
                success_count = 0
                skipped_files = []
                
                for file in uploaded_files:
                    if file and file.filename:
                        if allowed_file(file.filename):
                            filename = save_document(file, current_user.id)
                            if filename:
                                document = Document(filename=filename, leave_id=leave.id)
                                db.session.add(document)
                                success_count += 1
                        else:
                            skipped_files.append(file.filename)
                
                db.session.commit()
                
                if skipped_files:
                    flash(f'Some files were skipped due to invalid type: {", ".join(skipped_files)}', 'warning')
            
            flash('Leave application submitted successfully!', 'success')
            return redirect(url_for('dashboard'))
        
        except ValueError as e:
            flash(f'Invalid date format. Please use YYYY-MM-DD format', 'error')
            return redirect(url_for('apply_leave'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error submitting leave application: {str(e)}', 'error')
            return redirect(url_for('apply_leave'))
    return render_template('apply_leave.html', today_date=today_date)

@app.route('/submit-request', methods=['POST'])
def submit_request():
    send_email(
        subject="New Leave Request",
        html_content="<p>A new leave request was submitted.</p>",
        to_email="amadoujawo88@gmail.com"
    )
    flash("Request submitted and email notification sent!", "success")
    return redirect(url_for("dashboard"))

@app.route('/test-email')
def test_email():
    send_email(
        "Flask Test Email",
        "<h3>This is a test email from Brevo + Flask 🎉</h3>",
        "amadoujawo88@gmail.com"
    )
    return "Email sent!"

@app.route('/process-leave/<int:id>/<action>')
@login_required
def process_leave(id, action):
    if not current_user.is_hr:
        flash('Unauthorized access!', 'error')
        return redirect(url_for('dashboard'))
    
    leave = Leave.query.get_or_404(id)
    # Normalize action to proper status format
    if action.lower() == 'approve':
        try:
            if (leave.leave_type or '').lower() == 'annual leave':
                requested_year = leave.start_date.year
                approved_annual = Leave.query.filter_by(user_id=leave.user_id, leave_type='Annual Leave', status='Approved').all()
                used_annual_days = 0
                for l in approved_annual:
                    try:
                        if l.start_date.year == requested_year:
                            used_annual_days += (l.end_date - l.start_date).days + 1
                    except Exception:
                        continue
                requested_days = (leave.end_date - leave.start_date).days + 1
                if used_annual_days + requested_days > 30:
                    flash('Cannot approve annual leave beyond remaining balance (30 days per year)', 'error')
                    return redirect(url_for('dashboard'))
        except Exception:
            pass
        leave.status = 'Approved'
    elif action.lower() == 'reject':
        leave.status = 'Rejected'
    else:
        leave.status = action.capitalize()
    db.session.commit()
    
    # Create notification for the leave applicant
    message = f'Your leave request has been {action}d'
    notification = Notification.create_notification(
        user_id=leave.user_id,
        message=message,
        type='success' if action == 'approve' else 'error'
    )
    
    # Emit real-time notification
    socketio.emit('notification', {
        'type': 'leave_update',
        'leaveId': leave.id,
        'status': leave.status,
        'message': message
    }, room=str(leave.user_id))
    
    flash(f'Leave {action}d successfully!', 'success')
    return redirect(url_for('dashboard'))

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        socketio.emit('notification', {
            'type': 'connection',
            'message': 'Connected to real-time notifications'
        }, room=str(current_user.id))

# API endpoints for notifications and documents
@app.route('/api/notifications/unread-count')
@login_required
def get_unread_notifications_count():
    count = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).count()
    return jsonify({'count': count})

@app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id == current_user.id:
        notification.mark_as_read()
        return jsonify({'success': True})
    return jsonify({'success': False}), 403

@app.route('/api/leaves/upload-document', methods=['POST'])
@login_required
def upload_leave_document():
    if 'document' not in request.files:
        return jsonify({'success': False, 'message': 'No file provided'})
    
    file = request.files['document']
    leave_id = request.form.get('leave_id')
    
    if not leave_id:
        return jsonify({'success': False, 'message': 'Leave ID required'})
    
    leave = Leave.query.get_or_404(leave_id)
    if leave.user_id != current_user.id and not current_user.is_hr:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    filename = save_document(file, current_user.id)
    if filename:
        document = Document(filename=filename, leave_id=leave_id)
        db.session.add(document)
        db.session.commit()
        return jsonify({'success': True, 'document': {
            'id': document.id,
            'filename': filename,
            'url': url_for('get_document', filename=filename)
        }})
    
    return jsonify({'success': False, 'message': 'Invalid file type'})

@app.route('/uploads/<filename>')
@login_required
def get_document(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/documents/<int:document_id>', methods=['DELETE'])
@login_required
def delete_leave_document(document_id):
    document = Document.query.get_or_404(document_id)
    leave = Leave.query.get(document.leave_id)
    
    if leave.user_id != current_user.id and not current_user.is_hr:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    if delete_document(document.filename):
        db.session.delete(document)
        db.session.commit()
        return jsonify({'success': True})

@app.route('/admin/export-leaves-csv')
@login_required
@requires_admin
def export_leaves_csv():
    leaves = Leave.query.all()
    output = StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(['Start Date', 'End Date', 'Duration (Months)', 'Duration (Days)', 
                    'Employee Name', 'Employee ID', 'Designation', 'Reason', 'Status'])
    
    # Write data
    for leave in leaves:
        writer.writerow([
            leave.start_date.strftime('%Y-%m-%d'),
            leave.end_date.strftime('%Y-%m-%d'),
            round((leave.end_date - leave.start_date).days / 30.44, 1),
            (leave.end_date - leave.start_date).days,
            leave.employee_name,
            leave.employee_id,
            leave.designation,
            leave.reason,
            leave.status
        ])
    
    output.seek(0)
    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=leave_applications.csv'}
    )

@app.route('/admin/export-leaves-pdf')
@login_required
@requires_admin
def export_leaves_pdf():
    leaves = Leave.query.all()
    buffer = BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    # Add title
    styles = getSampleStyleSheet()
    elements.append(Paragraph('Leave Applications Report', styles['Title']))
    elements.append(Paragraph(f'Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', styles['Normal']))
    
    # Create table data
    data = [
        ['Start Date', 'End Date', 'Duration (Months)', 'Duration (Days)', 
         'Employee Name', 'Employee ID', 'Designation', 'Status']
    ]
    
    for leave in leaves:
        data.append([
            leave.start_date.strftime('%Y-%m-%d'),
            leave.end_date.strftime('%Y-%m-%d'),
            str(round((leave.end_date - leave.start_date).days / 30.44, 1)),
            str((leave.end_date - leave.start_date).days),
            leave.employee_name,
            leave.employee_id,
            leave.designation,
            leave.status
        ])
    
    # Create table and style it
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    doc.build(elements)
    
    buffer.seek(0)
    return Response(
        buffer.getvalue(),
        mimetype='application/pdf',
        headers={'Content-Disposition': 'attachment; filename=leave_applications.pdf'}
    )
    
    return jsonify({'success': False, 'message': 'Failed to delete document'})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, host='0.0.0.0', port=5009, debug=True)
