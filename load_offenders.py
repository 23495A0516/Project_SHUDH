# load_offenders.py (replace existing)
import os
from app import create_app, db
from app.models import Offender
from app.utils import get_face_encodings_from_file

app = create_app()
app.app_context().push()

DATA_DIR = os.path.join('app', 'static', 'db_faces')

def load_offenders():
    if not os.path.isdir(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
        print("Put offender/student photos into:", DATA_DIR)
        return

    added = 0
    updated = 0
    for fname in os.listdir(DATA_DIR):
        if not fname.lower().endswith(('.jpg','.jpeg','.png')):
            continue
        base = os.path.splitext(fname)[0]  # e.g. "21CS001_Rahul" or "21CS001_extra1"
        # get roll by first underscore split
        roll = base.split('_',1)[0]
        # find all files that start with this roll
        related = [f for f in os.listdir(DATA_DIR) if f.startswith(roll)]
        # collect encodings from all related files
        encodings = []
        for rf in related:
            path = os.path.join(DATA_DIR, rf)
            encs = get_face_encodings_from_file(path)
            for e in encs:
                encodings.append(e)
        if not encodings:
            print(f"[load] no face encodings for roll {roll} (files: {related})")
            continue

        # choose name from the first file (after underscore if present)
        name = base.split('_',1)[1] if '_' in base else roll
        email = f"{roll}@college.edu"

        existing = Offender.query.filter_by(roll_number=roll).first()
        if existing:
            existing.name = name
            existing.email = email
            existing.image_path = f"static/db_faces/{related[0]}"
            existing.face_encoding = encodings  # store list
            db.session.add(existing)
            updated += 1
        else:
            off = Offender(
                name=name,
                roll_number=roll,
                email=email,
                image_path=f"static/db_faces/{related[0]}",
                face_encoding=encodings
            )
            db.session.add(off)
            added += 1
        db.session.commit()

    print(f"Done. Added: {added}, Updated: {updated}")

if __name__ == '__main__':
    load_offenders()
