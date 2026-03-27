from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

# Initialize Extensions
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login' # Redirects here if not logged in

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = 'ediplus_secret_key_123'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mediplus.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize Plugins
    db.init_app(app)
    login_manager.init_app(app)

    # --- 🔗 REGISTER BLUEPRINTS ---
    from app.routes.patient import patient_bp
    from app.routes.auth import auth_bp # Assuming you have an auth file
    
    # This prefix '/patient' means all URLs start with /patient/dashboard, etc.
    app.register_blueprint(patient_bp, url_prefix='/patient')
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # Create Database Tables if they don't exist
    with app.app_context():
        db.create_all()

    return app

@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))