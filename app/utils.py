import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Face libs
import face_recognition
import numpy as np
from PIL import Image

# Token serializer
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import current_app

# Flask helper
from werkzeug.utils import secure_filename

# ====== SMTP / App credentials (keep these as-is) ======
EMAIL_ADDRESS = "projectshudhindia@gmail.com"   # your Gmail address
EMAIL_PASSWORD = "hbxqfchoeqyjcbhw"             # 16-char Google App Password

# ---------------------------
# Low-level email sender
# ---------------------------
def _send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Low-level email sender via Gmail SMTP (TLS).
    Returns True if sent successfully, else False.
    """
    server = None
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        print(f"✅ Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Error sending email to {to_email}: {e}")
        # Optional: preview the email content for debugging
        try:
            print("📩 Failed email content preview:")
            print(msg.as_string())
        except Exception:
            pass
        return False
    finally:
        if server:
            try:
                server.quit()
            except Exception:
                pass

# ---------------------------
# Public email APIs used by routes.py
# ---------------------------
def send_notification_email(user=None, recipient=None, subject=None, body=None):
    """
    Backwards-compatible notifier used in routes.py in two ways:

    1) OTP mode (registration/login):
       send_notification_email(user)
       - Expects user.email and user.otp to exist.
       - Composes a standard OTP email.

    2) Direct message mode (reminders, custom):
       send_notification_email(recipient=<email>, subject="...", body="...")
       - Sends exactly the provided subject/body to recipient.

    Returns True/False for success.
    """
    # Mode 2: Direct message
    if recipient and subject and body:
        return _send_email(recipient, subject, body)

    # Mode 1: OTP mail (user object provided)
    if user is not None and getattr(user, "email", None):
        otp_value = getattr(user, "otp", None)
        # If no subject/body passed, compose OTP email
        if otp_value:
            otp_subject = "Your Project SHUDH OTP"
            otp_body = f"""Hello {getattr(user, 'name', 'User')},

Your One-Time Password (OTP) for Project SHUDH is: {otp_value}

Do not share this code with anyone.

Regards,
Project SHUDH Team
"""
            return _send_email(user.email, otp_subject, otp_body)
        else:
            # If user has no OTP, still allow custom subject/body if provided
            if subject and body:
                return _send_email(user.email, subject, body)
            else:
                print("⚠️ send_notification_email called without OTP/subject/body.")
                return False

    print("⚠️ send_notification_email: insufficient parameters.")
    return False

def send_custom_email(recipient, subject, body):
    """
    Convenience wrapper to send any custom email.
    """
    return _send_email(recipient, subject, body)


def send_penalty_email(offender, penalty):
    """
    Send penalty notification email with a direct secure link (tokenized).
    offender -> Offender object
    penalty  -> Penalty object (with token + amount)
    """
    subject = "Penalty Notice — Project SHUDH"

    # Use penalty.token for secure deep link (not raw offender.id)
    deep_link = f"http://127.0.0.1:5000/offender/case/{penalty.token}"

    body = f"""
Hello {offender.name},

You have been identified committing a public hygiene violation under Project SHUDH.

⚠️ Penalty Amount: ₹{penalty.amount}

Click the link below to view your case details and pay the penalty:
{deep_link}

Please clear the dues within 7 days to avoid additional legal action.

Regards,
Project SHUDH Team
"""
    return _send_email(offender.email, subject, body)

# ---------------------------
# Token serializer helpers
# ---------------------------
def _serializer():
    """
    Returns a URLSafeTimedSerializer bound to app SECRET_KEY.
    Requires to be called inside an app context (current_app available).
    """
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

def generate_case_token(penalty_id, offender_id):
    """Create signed token containing penalty & offender IDs."""
    return _serializer().dumps({'penalty_id': int(penalty_id), 'offender_id': int(offender_id)})

def verify_case_token(token, max_age_days=7):
    """Verify token; return dict or None."""
    try:
        return _serializer().loads(token, max_age=max_age_days * 24 * 3600)
    except (BadSignature, SignatureExpired):
        return None

# ---------------------------
# Robust face recognition helpers
# ---------------------------
def _rgb_load(path):
    """Load an image using PIL and convert to RGB numpy array."""
    img = Image.open(path).convert('RGB')
    return np.array(img)

def get_face_encodings_from_file(image_path, upsample_times=1, model_order=('hog', 'cnn')):
    """
    Try multiple detection strategies and return list of encodings found.
    Returns list of 128-d numpy arrays (may be empty).

    - Tries models in model_order ('hog' faster, 'cnn' more accurate).
    - upsample_times improves detection of small/far faces.
    """
    if not os.path.exists(image_path):
        print(f"[face] path does not exist: {image_path}")
        return []

    try:
        img = _rgb_load(image_path)
    except Exception as e:
        print(f"[face] cannot load {image_path}: {e}")
        return []

    encodings = []
    # try both models (hog -> cnn) for robustness
    for model in model_order:
        try:
            locs = face_recognition.face_locations(img, number_of_times_to_upsample=upsample_times, model=model)
            if not locs:
                continue
            encs = face_recognition.face_encodings(img, known_face_locations=locs)
            if encs:
                encodings.extend(encs)
        except Exception as e:
            print(f"[face] model {model} failed on {image_path}: {e}")
            continue

    # deduplicate encodings (if both models gave same faces)
    uniq = []
    for e in encodings:
        if not any(np.allclose(e, u, atol=1e-6) for u in uniq):
            uniq.append(e)
    return uniq

def get_face_encoding_from_file(image_path):
    """
    Backwards-compatible wrapper used by older scripts.
    Returns the first encoding found as a Python list (or None).
    """
    encs = get_face_encodings_from_file(image_path, upsample_times=1, model_order=('hog', 'cnn'))
    if not encs:
        return None
    first = encs[0]
    # Convert numpy array to plain Python list for safe DB pickling compatibility
    return first.tolist()

def generate_face_encoding(image_path):
    """
    Alias kept for compatibility: return first encoding as list or None.
    """
    return get_face_encoding_from_file(image_path)

def face_distance_to_confidence(distance, threshold=0.6):
    """
    Convert face_distance (0..1) to an approximate confidence percent.
    Lower distance -> higher confidence.
    Heuristic mapping:
      distance 0.0 -> 100%
      distance threshold -> ~50%
      distance 1.0 -> ~0%
    """
    try:
        distance = float(distance)
    except Exception:
        return 0
    if distance <= 0:
        return 100
    if distance <= threshold:
        # linear between 100 and 50
        return int(max(0, min(100, 100 - (distance / threshold) * 50)))
    # over threshold, degrade to 0 at distance ~1.0
    beyond = min(distance, 1.0) - threshold
    max_span = 1.0 - threshold if (1.0 - threshold) > 0 else 1.0
    return max(0, int(max(0, 50 - (beyond / max_span) * 50)))

# ---------------------------
# Convenience: secure filename for uploads
# ---------------------------
def save_upload_file(file_storage, target_folder='app/static/uploads'):
    """
    Save Werkzeug FileStorage safely into the target folder and return the saved filename.
    """
    if not file_storage:
        return None
    os.makedirs(target_folder, exist_ok=True)
    filename = secure_filename(file_storage.filename)
    # add short random prefix to avoid collisions
    prefix = secrets_token_hex(6)
    filename = f"{prefix}_{filename}"
    full_path = os.path.join(target_folder, filename)
    file_storage.save(full_path)
    return filename

# small helper to generate random hex (avoid importing secrets everywhere)
def secrets_token_hex(nbytes=8):
    try:
        import secrets
        return secrets.token_hex(nbytes)
    except Exception:
        import uuid
        return uuid.uuid4().hex[: nbytes * 2]
