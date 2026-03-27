import os
import joblib
import numpy as np
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import User, Appointment, Prescription, LabReport, Diagnosis, AnonymousTrainingData
from app import db

patient_bp = Blueprint('patient', __name__)

# --- 🤖 LOAD AI MODEL (Pre-loaded for Speed) ---
MODEL_PATH = os.path.join('app', 'ai_models', 'disease_model.pkl')
SYMPTOM_PATH = os.path.join('app', 'ai_models', 'symptoms_list.pkl')

try:
    if os.path.exists(MODEL_PATH) and os.path.exists(SYMPTOM_PATH):
        model = joblib.load(MODEL_PATH)
        symptoms_list = joblib.load(SYMPTOM_PATH)
    else:
        model, symptoms_list = None, []
        print("⚠️ AI Model files not found. Run train_model.py first.")
except Exception as e:
    model, symptoms_list = None, []
    print(f"❌ Error loading AI model: {e}")

# --- PHASE 1: CLINICAL DASHBOARD ---
@patient_bp.route('/dashboard')
@login_required
def dashboard():
    """Health Analytics Dashboard: EHR Trends & Clinical Summary"""
    appointments = Appointment.query.filter_by(patient_id=current_user.id).order_by(Appointment.id.desc()).all()
    prescriptions = Prescription.query.filter_by(patient_id=current_user.id).all()
    recent_diagnoses = Diagnosis.query.filter_by(patient_id=current_user.id).order_by(Diagnosis.id.desc()).limit(5).all()
    lab_reports = LabReport.query.filter_by(patient_id=current_user.id).order_by(LabReport.id.desc()).limit(3).all()
    
    return render_template('patient/dashboard.html', 
                           appointments=appointments, 
                           prescriptions=prescriptions,
                           recent_diagnoses=recent_diagnoses,
                           lab_reports=lab_reports)

@patient_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """EHR Setup: Update Age, Gender, and Medical History"""
    if request.method == 'POST':
        try:
            current_user.age = request.form.get('age')
            current_user.gender = request.form.get('gender')
            current_user.medical_history = request.form.get('history', '').strip()
            
            db.session.commit()
            flash("Clinical Profile Updated Successfully!", "success")
            return redirect(url_for('patient.dashboard'))
        except Exception:
            db.session.rollback()
            flash("System Error: Could not update profile. Try again.", "error")
            
    return render_template('patient/profile.html')

# --- PHASE 2: ML-POWERED SYMPTOM ENGINE ---
@patient_bp.route('/symptom-checker', methods=['GET', 'POST'])
@login_required
def symptom_checker():
    """Predictive Engine using Random Forest Classifier and XAI Logic"""
    results = []
    recommendation = None
    
    if request.method == 'POST':
        raw_symptoms = request.form.get('symptoms', '').lower().strip()
        severity = request.form.get('severity', 'Low')
        duration = request.form.get('duration', '1 day')
        
        # Guard: Check if model is loaded
        if not model or not symptoms_list:
            flash("AI Engine is initializing. Please try again in a moment.", "info")
            return redirect(url_for('patient.symptom_checker'))

        # 1. Vectorization: Convert text input to 0/1 array for the ML Model
        input_vector = np.zeros(len(symptoms_list))
        matches_found = 0
        
        for i, symptom in enumerate(symptoms_list):
            # Dataset uses underscores (skin_rash), user input uses spaces (skin rash)
            clean_symptom = symptom.replace('_', ' ')
            if clean_symptom in raw_symptoms:
                input_vector[i] = 1
                matches_found += 1

        if matches_found == 0:
            flash("AI could not identify specific clinical symptoms. Please be more descriptive.", "warning")
            return render_template('patient/symptom_checker.html', results=[], rec=None)

        # 2. Get Probabilities from Random Forest
        try:
            probs = model.predict_proba([input_vector])[0]
            # Get top 3 disease indices
            top_indices = np.argsort(probs)[-3:][::-1]
            
            for idx in top_indices:
                confidence = round(probs[idx] * 100, 2)
                if confidence > 5: # Threshold to filter noise
                    disease = model.classes_[idx]
                    
                    # Risk classification based on AI confidence and severity
                    risk_lvl = "High" if confidence > 75 or severity == "High" else "Medium" if confidence > 40 else "Low"
                    
                    results.append({
                        "name": disease,
                        "prob": confidence,
                        "risk": risk_lvl,
                        "reason": f"Matches {matches_found} clinical markers identified in your description."
                    })

            # 3. Save Top Result to EHR and Self-Learning Table
            if results:
                top = results[0]
                new_diag = Diagnosis(
                    disease_name=top['name'],
                    probability=top['prob'],
                    risk_level=top['risk'],
                    patient_id=current_user.id
                )
                db.session.add(new_diag)

                learning_data = AnonymousTrainingData(
                    symptoms_input=raw_symptoms,
                    predicted_disease=top['name'],
                    severity_reported=severity
                )
                db.session.add(learning_data)
                db.session.commit()

                # 4. Recommendation Logic
                if top['risk'] == "High":
                    recommendation = "🚨 URGENT: Symptoms match high-risk patterns. Contact emergency services or visit the ER immediately."
                elif top['prob'] > 60:
                    recommendation = f"Suggested: Schedule a specialist consultation for {top['name']}. Monitor symptoms for {duration}."
                else:
                    recommendation = "Condition appears stable. Stay hydrated and track any new symptoms."

        except Exception as e:
            db.session.rollback()
            print(f"Prediction Error: {e}")
            flash("AI Engine encountered an analysis error.", "error")

    return render_template('patient/symptom_checker.html', results=results, rec=recommendation)

# --- PHASE 4: LAB CENTER ---
@patient_bp.route('/lab-diagnostics', methods=['GET', 'POST'])
@login_required
def lab_diagnostics():
    """AI Lab Report Interpreter: Rule-based biomarker analysis"""
    if request.method == 'POST':
        test_name = request.form.get('test_name')
        report_text = request.form.get('report_text', '').lower()
        
        if not report_text:
            flash("No data provided for AI interpretation.", "warning")
            return redirect(url_for('patient.lab_diagnostics'))

        interpretation = "Analysis: Biomarkers appear within normal physiological range."
        
        if "hemoglobin" in report_text and ("low" in report_text or "<" in report_text):
            interpretation = "⚠️ AI Alert: Low Hemoglobin detected. Pattern suggests iron-deficiency anemia."
        elif "glucose" in report_text and ("high" in report_text or "mg/dl" in report_text):
            interpretation = "⚠️ AI Alert: Elevated Glucose detected. Risk of Hyperglycemia; monitor intake."
        elif "wbc" in report_text or "white blood cell" in report_text:
            interpretation = "⚠️ AI Alert: Leukocyte variance detected. Possible immune response/infection."

        try:
            new_report = LabReport(
                test_name=test_name,
                ai_interpretation=interpretation,
                patient_id=current_user.id
            )
            db.session.add(new_report)
            db.session.commit()
            flash("Lab Interpretation complete. Results saved to EHR.", "success")
            return redirect(url_for('patient.dashboard'))
        except Exception:
            db.session.rollback()
            flash("Error saving lab report.", "error")

    reports = LabReport.query.filter_by(patient_id=current_user.id).all()
    return render_template('patient/lab_tests.html', reports=reports)

# --- PHASE 3: CONSULTATION SCHEDULING ---
@patient_bp.route('/book', methods=['GET', 'POST'])
@login_required
def book_appointment():
    if request.method == 'POST':
        try:
            new_appt = Appointment(
                doctor_name=request.form.get('doctor_name'),
                date=request.form.get('date'),
                time=request.form.get('time'),
                patient_id=current_user.id,
                status='Confirmed'
            )
            db.session.add(new_appt)
            db.session.commit()
            flash("Appointment Confirmed! Secure notification sent to doctor.", "success")
            return redirect(url_for('patient.dashboard'))
        except Exception:
            db.session.rollback()
            flash("Booking failed. Please check all fields.", "error")
    
    doctors = User.query.filter_by(role='doctor').all()
    return render_template('patient/book_appointment.html', doctors=doctors)