import os
from werkzeug.utils import secure_filename
from datetime import datetime
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user, login_required
import smtplib
import ssl
from email.mime.text import MIMEText

def requires_admin(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.get_is_admin():
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_document(file, user_id):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        new_filename = f'{user_id}_{timestamp}_{filename}'
        
        # Create upload directory if it doesn't exist
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
        
        file_path = os.path.join(UPLOAD_FOLDER, new_filename)
        file.save(file_path)
        return new_filename
    return None

def get_file_path(filename):
    return os.path.join(UPLOAD_FOLDER, filename)

def delete_document(filename):
    file_path = get_file_path(filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return True
    return False


from email.mime.multipart import MIMEMultipart

def send_email(to_address, subject, body, html_body=None):
    """Send an email using SMTP configuration from environment variables.

    Expected environment variables:
    - SMTP_HOST: SMTP server host (required)
    - SMTP_PORT: SMTP server port (default 587)
    - SMTP_USER: SMTP username (optional)
    - SMTP_PASSWORD: SMTP password (optional)
    - SMTP_USE_TLS: 'true' to use STARTTLS (default true)
    - SMTP_USE_SSL: 'true' to use SSL (default false; ignored if TLS true)
    - SMTP_FROM: From address (default SMTP_USER)

    Returns True on success, False otherwise. Fails gracefully without raising.
    """
    host = os.getenv('SMTP_HOST')
    port = int(os.getenv('SMTP_PORT', '587'))
    user = os.getenv('SMTP_USER')
    password = os.getenv('SMTP_PASSWORD')
    use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
    use_ssl = os.getenv('SMTP_USE_SSL', 'false').lower() == 'true'
    from_addr = os.getenv('SMTP_FROM', user or 'noreply@example.com')

    if not host:
        # SMTP not configured; skip silently
        print('[email] SMTP_HOST not set. Skipping email send.')
        return False

    # Compose message
    if html_body:
        msg = MIMEMultipart('alternative')
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    else:
        msg = MIMEText(body, 'plain', 'utf-8')
    
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to_address

    try:
        if use_tls and not use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP(host, port) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                if user and password:
                    server.login(user, password)
                server.sendmail(from_addr, [to_address], msg.as_string())
        else:
            # SSL or plain
            if use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(host, port, context=context) as server:
                    if user and password:
                        server.login(user, password)
                    server.sendmail(from_addr, [to_address], msg.as_string())
            else:
                with smtplib.SMTP(host, port) as server:
                    if user and password:
                        server.login(user, password)
                    server.sendmail(from_addr, [to_address], msg.as_string())
        print(f'[email] Sent to {to_address}: {subject}')
        return True
    except Exception as e:
        print(f'[email] Failed to send email to {to_address}: {e}')
        return False


def send_admin_emails(subject, body, html_body=None):
    """Send notification email(s) to admin HR recipients.

    Sources recipients from:
    - ADMIN_EMAILS (comma-separated)
    - ADMIN_EMAIL (single)
    - Fallback default: 'amadoujawo88@gmail.com'
    """
    emails_env = os.getenv('ADMIN_EMAILS', '')
    single_env = os.getenv('ADMIN_EMAIL', '')
    recipients = []

    if emails_env:
        recipients.extend([e.strip() for e in emails_env.split(',') if e.strip()])
    if single_env:
        recipients.append(single_env.strip())
    # Ensure at least the provided HR email is included
    recipients.append('amadoujawo88@gmail.com')

    # Deduplicate
    unique_recipients = list(dict.fromkeys([r for r in recipients if r]))
    sent_any = False
    for r in unique_recipients:
        if send_email(r, subject, body, html_body=html_body):
            sent_any = True
    return sent_any