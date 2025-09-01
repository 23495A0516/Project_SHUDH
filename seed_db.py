import os
from app import create_app, db
from app.models import User
from app.utils import get_face_encoding_from_file
app = create_app()

def seed():
    with app.app_context():
        # Clear existing users
        User.query.delete()
        db.session.commit()

        admin = User(name='Admin User', email='admin@college.edu', role='admin')
        admin.set_password('admin123')
        officer = User(name='Officer User', email='officer@college.edu', role='officer')
        officer.set_password('officer123')
        db.session.add(admin); db.session.add(officer)
        db.session.commit()

        # Add example offenders with face encodings
        sample_dir = os.path.join(os.path.dirname(__file__), 'app', 'static', 'sample_faces')
        if not os.path.exists(sample_dir):
            os.makedirs(sample_dir)
            print("Add sample face images into:", sample_dir)
            return

        for fname in os.listdir(sample_dir):
            if fname.lower().endswith(('.jpg','.jpeg','.png')):
                path = os.path.join(sample_dir, fname)
                enc = get_face_encoding_from_file(path)
                if enc is not None:
                    u = User(name=f"Student {fname}", email=f"{fname}@college.edu", role='offender')
                    u.set_password('password')
                    u.face_encoding = enc
                    u.student_id = fname.split('.')[0]
                    db.session.add(u)
        db.session.commit()
        print("Seeding complete. Admin: admin@college.edu/admin123  Officer: officer@college.edu/officer123")

if __name__ == '__main__':
    seed()
