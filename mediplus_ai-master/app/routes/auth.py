from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, current_user, login_required
from app.models import User
from app import db
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    """Redirects users to their respective dashboard if logged in, otherwise login."""
    if current_user.is_authenticated:
        # Flowchart Step: Role-Based Access Control
        if current_user.role == 'doctor':
            return redirect(url_for('doctor.dashboard'))
        return redirect(url_for('patient.dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Phase 1: Secure Registration & Account Type Selection"""
    if current_user.is_authenticated:
        return redirect(url_for('patient.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email').lower().strip() # Clean the email input
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password') # New Field
        role = request.form.get('role')

        # 1. Validation: Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match. Please try again.', 'error')
            return redirect(url_for('auth.register'))

        # 2. Validation: Check if user already exists
        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash('This email is already registered. Try logging in.', 'info')
            return redirect(url_for('auth.login'))

        # 3. Secure Password Hashing (Defaulting to scrypt/pbkdf2)
        hashed_password = generate_password_hash(password)

        new_user = User(
            username=username,
            email=email,
            password=hashed_password,
            role=role
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Account created successfully! Welcome to MediPlus AI.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred. Please try again later.', 'error')

    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User Authentication & Dashboard Redirection"""
    if current_user.is_authenticated:
        return redirect(url_for('patient.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email').lower().strip()
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        # Verify Hashed Password
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success')
            
            # Phase 3: Care Flow - Direct to correct portal
            if user.role == 'doctor':
                return redirect(url_for('doctor.dashboard'))
            return redirect(url_for('patient.dashboard'))
        
        flash('Invalid email or password. Please check your credentials.', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out securely.', 'info')
    return redirect(url_for('auth.login'))