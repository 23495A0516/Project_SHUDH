from flask_login import UserMixin
from datetime import datetime, timedelta
import uuid
from app import db
from werkzeug.security import generate_password_hash, check_password_hash

# -------------------------
# Helpers for defaults
# -------------------------
def _default_token():
    return uuid.uuid4().hex

def _default_token_expiry():
    # Token valid for 7 days
    return datetime.utcnow() + timedelta(days=7)

# -------------------------
# Auth users: admin/officer
# -------------------------
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), default='officer')  # admin/officer
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)

    # Optional for face recognition (not required for officers/admins)
    face_encoding = db.Column(db.PickleType, nullable=True)

    phone = db.Column(db.String(30), nullable=True)
    student_id = db.Column(db.String(50), nullable=True)

    # OTP for login
    otp = db.Column(db.String(8), nullable=True)
    otp_verified = db.Column(db.Boolean, default=False)

    def set_password(self, pwd):
        # explicit method selection for stable hashing across platforms
        self.password_hash = generate_password_hash(pwd, method="pbkdf2:sha256")

    def check_password(self, pwd):
        return check_password_hash(self.password_hash, pwd)

    def __repr__(self):
        return f"<User id={self.id} role={self.role} email={self.email}>"

# -------------------------
# Offender master table
# -------------------------
class Offender(db.Model):
    __tablename__ = 'offender'
    id = db.Column(db.Integer, primary_key=True)

    # Core identity
    name = db.Column(db.String(100), nullable=False)
    roll_number = db.Column(db.String(50), unique=True, nullable=False, index=True)  # e.g., college roll / student id
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)

    # College metadata (added for CSV import & display)
    department = db.Column(db.String(80), nullable=True)   # e.g., CSE, ECE
    year = db.Column(db.Integer, nullable=True)            # e.g., 1/2/3/4

    # Media & recognition
    phone = db.Column(db.String(30), nullable=True)
    image_path = db.Column(db.String(400), nullable=True)      # optional absolute/relative portrait path
    photo_filename = db.Column(db.String(200), nullable=True)  # store CSV "photo" (e.g., "23495A0511.jpg")
    face_encoding = db.Column(db.PickleType, nullable=True)    # ✅ nullable for flexibility

    # Relationship: one offender -> many penalties
    penalties = db.relationship(
        'Penalty',
        backref='offender',
        lazy=True,
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    def __repr__(self):
        return f"<Offender id={self.id} roll={self.roll_number} email={self.email}>"

# -------------------------
# Penalties issued
# -------------------------
class Penalty(db.Model):
    __tablename__ = 'penalties'
    id = db.Column(db.Integer, primary_key=True)

    # ✅ Link penalties to Offender (not users)
    offender_id = db.Column(
        db.Integer,
        db.ForeignKey('offender.id', ondelete="CASCADE"),
        nullable=True
    )

    # Snapshot fields for audit
    offender_name = db.Column(db.String(120))
    offender_email = db.Column(db.String(120))

    # Evidence & status
    image_path = db.Column(db.String(400), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    matched = db.Column(db.Boolean, default=False, index=True)
    paid = db.Column(db.Boolean, default=False, index=True)
    amount = db.Column(db.Float, default=500.0)  # default fine

    # Tokenized deep-link for offender access
    token = db.Column(db.String(100), unique=True, default=_default_token, index=True)
    token_expiry = db.Column(db.DateTime, default=_default_token_expiry)

    # (Optional) OTP for any future case-level verification flow
    otp = db.Column(db.String(8), nullable=True)
    otp_verified = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<Penalty id={self.id} offender_id={self.offender_id} amount={self.amount} paid={self.paid}>"

# -------------------------
# Student master table (for CSV import)
# -------------------------
class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(120), nullable=False)
    roll_no = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    department = db.Column(db.String(80), nullable=False)
    year = db.Column(db.Integer, nullable=False)

    photo = db.Column(db.String(200), nullable=False)  # store filename like "23495A0511.jpg"

    def __repr__(self):
        return f"<Student roll={self.roll_no} email={self.email}>"
