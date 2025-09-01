import secrets
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager
from app.models import User, Penalty, Offender
from app.utils import send_notification_email, send_penalty_email, generate_face_encoding
import os
import face_recognition

main = Blueprint('main', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@main.route('/')
def welcome():
    return render_template('welcome.html')

@main.route('/upload_spitting_login_redirect')
def upload_spitting_login_redirect():
    session['post_login_redirect'] = url_for('main.upload_spitting_case')
    return redirect(url_for('main.login_officer'))

# -------------------------
# Registration (Admin/Officer)
# -------------------------
@main.route('/register_admin', methods=['GET', 'POST'])
def register_admin():
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        phone = request.form.get('phone')
        password = request.form.get('password')

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('main.register_admin'))

        hashed_pwd = generate_password_hash(password)
        otp = str(secrets.randbelow(900000) + 100000)

        new_admin = User(email=email, name=name, phone=phone,
                         password_hash=hashed_pwd, role='admin', otp=otp)
        db.session.add(new_admin)
        db.session.commit()

        send_notification_email(new_admin)
        session['verify_user_id'] = new_admin.id
        return redirect(url_for('main.verify_registration'))

    return render_template('register_admin.html')

@main.route('/register_officer', methods=['GET', 'POST'])
def register_officer():
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        phone = request.form.get('phone')
        password = request.form.get('password')

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('main.register_officer'))

        hashed_pwd = generate_password_hash(password)
        otp = str(secrets.randbelow(900000) + 100000)

        new_officer = User(email=email, name=name, phone=phone,
                           password_hash=hashed_pwd, role='officer', otp=otp)
        db.session.add(new_officer)
        db.session.commit()

        send_notification_email(new_officer)
        session['verify_user_id'] = new_officer.id
        return redirect(url_for('main.verify_registration'))

    return render_template('register_officer.html')

# -------------------------
# OTP Verify (Registration/Login)
# -------------------------
@main.route('/verify_registration', methods=['GET', 'POST'])
def verify_registration():
    user_id = session.get('verify_user_id')
    if not user_id:
        return redirect(url_for('main.welcome'))

    user = User.query.get(user_id)
    if request.method == 'POST':
        otp = request.form.get('otp')
        if user.otp == otp:
            user.otp_verified = True
            user.otp = None
            db.session.commit()
            flash('OTP verified! You can now login.', 'success')
            return redirect(url_for(f"main.login_{user.role}"))
        else:
            flash('Invalid OTP', 'danger')

    return render_template('verify_registration.html', user=user)

@main.route('/login_admin', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        email = request.form.get('username').strip()
        pwd = request.form.get('password').strip()
        user = User.query.filter_by(email=email, role='admin').first()
        if user and check_password_hash(user.password_hash, pwd):
            otp = str(secrets.randbelow(900000) + 100000)
            user.otp = otp
            db.session.commit()
            try:
                send_notification_email(user)
                session['verify_login_user_id'] = user.id
                return redirect(url_for('main.verify_login'))
            except Exception as e:
                flash(f"Error sending OTP: {str(e)}", 'danger')
                return redirect(url_for('main.login_admin'))
        flash('Invalid credentials', 'danger')
        return redirect(url_for('main.login_admin'))
    return render_template('login_admin.html')

@main.route('/login_officer', methods=['GET', 'POST'])
def login_officer():
    if request.method == 'POST':
        email = request.form.get('username').strip()
        pwd = request.form.get('password').strip()
        user = User.query.filter_by(email=email, role='officer').first()
        if user and check_password_hash(user.password_hash, pwd):
            otp = str(secrets.randbelow(900000) + 100000)
            user.otp = otp
            db.session.commit()
            try:
                send_notification_email(user)
                session['verify_login_user_id'] = user.id
                session['post_login_redirect'] = session.get('post_login_redirect', None)
                return redirect(url_for('main.verify_login'))
            except Exception as e:
                flash(f"Error sending OTP: {str(e)}", 'danger')
                return redirect(url_for('main.login_officer'))
        flash('Invalid credentials', 'danger')
        return redirect(url_for('main.login_officer'))
    return render_template('login_officer.html')

@main.route('/verify_login', methods=['GET', 'POST'])
def verify_login():
    user_id = session.get('verify_login_user_id')
    if not user_id:
        return redirect(url_for('main.welcome'))

    user = User.query.get(user_id)
    if request.method == 'POST':
        otp = request.form.get('otp')
        if user.otp == otp:
            user.otp = None
            db.session.commit()
            login_user(user)
            flash(f'Welcome {user.role.capitalize()} {user.name}!', 'success')
            session.pop('verify_login_user_id', None)

            redirect_target = session.pop('post_login_redirect', None)
            if redirect_target:
                return redirect(redirect_target)

            if user.role == 'admin':
                return redirect(url_for('main.dashboard_admin'))
            elif user.role == 'officer':
                return redirect(url_for('main.dashboard_officer'))
        else:
            flash('Invalid OTP', 'danger')

    return render_template('verify_login.html', user=user)

# -------------------------
# Dashboards
# -------------------------
@main.route('/dashboard_admin')
@login_required
def dashboard_admin():
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('main.welcome'))
    return render_template('dashboard_admin.html')

@main.route('/dashboard_officer')
@login_required
def dashboard_officer():
    if current_user.role != 'officer':
        flash('Access denied!', 'danger')
        return redirect(url_for('main.welcome'))
    cases = Penalty.query.order_by(Penalty.id.desc()).all()
    return render_template('dashboard_officer.html', cases=cases)

# -------------------------
# Reminders
# -------------------------
@main.route('/send_reminder/<int:case_id>')
@login_required
def send_reminder(case_id):
    if current_user.role != 'officer':
        flash('Access denied!', 'danger')
        return redirect(url_for('main.welcome'))

    case = Penalty.query.get_or_404(case_id)

    try:
        if case.offender_id:
            offender = Offender.query.get(case.offender_id)
            if offender:
                send_penalty_email(offender, case)
                flash(f"Reminder sent to {case.offender_name}.", "success")
        else:
            flash("No linked offender for this case.", "warning")
    except Exception as e:
        flash(f"Error sending reminder: {str(e)}", "danger")

    return redirect(url_for('main.dashboard_officer'))

# -------------------------
# Upload Spitting Case (Main)
# -------------------------
@main.route('/upload_spitting', methods=['GET', 'POST'])
@login_required
def upload_spitting_case():
    if current_user.role != 'officer':
        flash('Access denied!', 'danger')
        return redirect(url_for('main.welcome'))

    uploaded_image = None
    match_found = False
    offender_name = None
    offender_roll = None
    penalty_amount = 500
    matched_image = None
    case = None

    db_faces_dir = os.path.join('app', 'static', 'db_faces')
    os.makedirs(db_faces_dir, exist_ok=True)
    db_faces = os.listdir(db_faces_dir)

    if request.method == 'POST':
        file = request.files.get('spit_image')
        if file:
            filename = f"spit_{secrets.token_hex(4)}_{file.filename}"
            upload_path = os.path.join("app", "static", "uploads", filename)
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            file.save(upload_path)
            uploaded_image = filename

            # ---------- FACE MATCHING ----------
            try:
                uploaded_encoding = generate_face_encoding(upload_path)
                if uploaded_encoding:
                    for db_face in db_faces:
                        db_face_path = os.path.join(db_faces_dir, db_face)
                        db_encoding = generate_face_encoding(db_face_path)
                        if db_encoding and face_recognition.compare_faces([db_encoding], uploaded_encoding, tolerance=0.5)[0]:
                            offender = Offender.query.filter_by(image_path=db_face).first()
                            if offender:
                                match_found = True
                                offender_name = offender.name
                                offender_roll = offender.roll_number
                                matched_image = f"db_faces/{db_face}"
                                break
            except Exception as e:
                print(f"❌ Face recognition error: {e}")

            # ---------- Create Penalty ----------
            new_case = Penalty(
                offender_id=offender.id if match_found else None,
                offender_name=offender_name if match_found else "Unknown",
                offender_email=offender.email if match_found else None,
                image_path=f"uploads/{filename}",
                matched=match_found,
                paid=False,
                amount=penalty_amount
            )
            db.session.add(new_case)
            db.session.commit()
            case = new_case

            if match_found and offender:
                send_penalty_email(offender, new_case)

            flash("Case uploaded and saved successfully!", "success")

    return render_template(
        'upload_spitting.html',
        case=case,
        uploaded_image=uploaded_image,
        match_found=match_found,
        offender_name=offender_name,
        offender_roll=offender_roll,
        penalty_amount=penalty_amount,
        matched_image=matched_image,
        db_faces=db_faces
    )

# -------------------------
# Offender Page
# -------------------------
@main.route('/offender/case/<token>')
def offender_page(token):
    case = Penalty.query.filter_by(token=token).first_or_404()
    return render_template('pay_fine.html', case=case)

@main.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.welcome'))
