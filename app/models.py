from app import db
from flask_login import UserMixin
from datetime import datetime

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'patient' or 'doctor'
    
    # Phase 1: User Profile Setup
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    medical_history = db.Column(db.Text)

    # EHR Relationships
    appointments = db.relationship('Appointment', backref='patient_user', lazy=True, foreign_keys='Appointment.patient_id')
    prescriptions = db.relationship('Prescription', backref='patient_user', lazy=True, foreign_keys='Prescription.patient_id')
    lab_reports = db.relationship('LabReport', backref='patient_user', lazy=True)
    diagnoses = db.relationship('Diagnosis', backref='patient_user', lazy=True)
    # New: Relationship for Feedback
    feedbacks = db.relationship('Feedback', backref='patient_user', lazy=True)

class Diagnosis(db.Model):
    """AI / ML Disease Prediction Output (Phase 2)"""
    id = db.Column(db.Integer, primary_key=True)
    disease_name = db.Column(db.String(100), nullable=False)
    probability = db.Column(db.Integer) 
    risk_level = db.Column(db.String(20)) 
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class LabReport(db.Model):
    """Lab Diagnostic Flow & AI Lab Analysis (Phase 2.5)"""
    id = db.Column(db.Integer, primary_key=True)
    test_name = db.Column(db.String(100), nullable=False)
    raw_data = db.Column(db.Text) 
    ai_interpretation = db.Column(db.Text)
    status = db.Column(db.String(20), default='Uploaded')
    date_uploaded = db.Column(db.DateTime, default=datetime.utcnow)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Appointment(db.Model):
    """Consultation & Care Flow (Phase 3)"""
    id = db.Column(db.Integer, primary_key=True)
    doctor_name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    time = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='Scheduled') 
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Prescription(db.Model):
    """E-Prescription & Medicine Reminder System (Phase 3.5)"""
    id = db.Column(db.Integer, primary_key=True)
    details = db.Column(db.Text, nullable=False) 
    date_prescribed = db.Column(db.DateTime, default=datetime.utcnow)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# --- NEW: FINAL FLOW MODELS ---

class Feedback(db.Model):
    """Feedback, Rating & Review (Phase 4)"""
    id = db.Column(db.Integer, primary_key=True)
    doctor_name = db.Column(db.String(100))
    rating = db.Column(db.Integer) # 1 to 5 stars
    review = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class AnonymousTrainingData(db.Model):
    """AI Model Self-Learning Logic (Phase 4 - Final)"""
    id = db.Column(db.Integer, primary_key=True)
    symptoms_input = db.Column(db.Text)
    predicted_disease = db.Column(db.String(100))
    severity_reported = db.Column(db.String(20))
    # NO patient_id here to keep the data anonymous for learning
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)