from database import db
from datetime import datetime
from flask_login import UserMixin

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    #email = db.Column(db.String(120), unique=True, nullable=True)
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    employee_id = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(50), nullable=True)
    job_title = db.Column(db.String(100), nullable=True)
    is_hr = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    must_change_password = db.Column(db.Boolean, default=False)
    annual_leave_allocation = db.Column(db.Integer, default=30, nullable=False)
    leaves = db.relationship('Leave', backref='employee', lazy=True)

    def get_is_admin(self):
        return self.is_admin

class Leave(db.Model):
    __tablename__ = 'leave_table'
    id = db.Column(db.Integer, primary_key=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    duration_months = db.Column(db.Integer, nullable=True)
    duration_days = db.Column(db.Integer, nullable=True)
    leave_type = db.Column(db.String(50), nullable=False)
    reason = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='Pending')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    employee_id = db.Column(db.String(20), nullable=False)
    employee_name = db.Column(db.String(100), nullable=True)
    designation = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    documents = db.relationship('Document', backref='leave', lazy=True)

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    leave_id = db.Column(db.Integer, db.ForeignKey('leave_table.id'), nullable=False)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(20), default='info')  # info, success, warning, error
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def create_notification(user_id, message, type='info'):
        notification = Notification(user_id=user_id, message=message, type=type)
        db.session.add(notification)
        db.session.commit()
        return notification

    @staticmethod
    def get_unread_notifications(user_id):
        return Notification.query.filter_by(
            user_id=user_id,
            is_read=False
        ).order_by(Notification.created_at.desc()).all()

    def mark_as_read(self):
        self.is_read = True
        db.session.commit()