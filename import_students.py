import pandas as pd
from run import app
from app.models import db, Student

def load_students():
    # Read CSV and strip spaces from column names
    df = pd.read_csv("Students_data.csv")
    df.columns = df.columns.str.strip()

    with app.app_context():
        for _, row in df.iterrows():
            photo_filename = row['photo'].strip()  # remove accidental spaces
            student = Student(
                name=row['name'].strip(),
                roll_no=row['roll_no'].strip(),
                email=row['email'].strip(),
                department=row['department'].strip(),
                year=int(row['year']),
                photo=f"db_faces/{photo_filename}"  # ✅ use column 'photo' from model
            )
            db.session.add(student)

        db.session.commit()
        print("✅ Students imported successfully!")

if __name__ == "__main__":
    load_students()
 