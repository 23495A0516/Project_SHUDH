import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate  # ✅ Added import

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'main.login_officer'
migrate = Migrate()  # ✅ Added migrate object

def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config['SECRET_KEY'] = os.environ.get('SHUDH_SECRET', 'dev-secret-key')

    # Ensure instance folder exists
    instance_path = os.path.join(app.root_path, '..', 'instance')
    os.makedirs(instance_path, exist_ok=True)

    # SQLite DB Path
    db_path = os.path.join(instance_path, 'database.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    migrate.init_app(app, db)  # ✅ Enable Flask-Migrate
    login_manager.init_app(app)

    from app.routes import main
    app.register_blueprint(main)

    with app.app_context():
        from app import models
        # db.create_all()  # ❌ Removed (we will use migrations instead)

    return app
