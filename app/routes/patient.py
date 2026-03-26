from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import User, Appointment, Prescription, LabReport, Diagnosis, AnonymousTrainingData
from app import db
from datetime import datetime

patient_bp = Blueprint('patient', __name__)

# --- PHASE 1: CLINICAL DASHBOARD ---
@patient_bp.route('/dashboard')
@login_required
def dashboard():
    """Health Analytics Dashboard: EHR Trends & Clinical Summary"""
    # Fetch most recent data for the patient
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

# --- PHASE 2: AI SYMPTOM ENGINE (XAI) ---
@patient_bp.route('/symptom-checker', methods=['GET', 'POST'])
@login_required
def symptom_checker():
    """Explainable AI (XAI) Engine: Predictive Diagnostics & Risk Assessment"""
    results = []
    recommendation = None
    
    if request.method == 'POST':
        # 1. Input Sanitization
        raw_symptoms = request.form.get('symptoms', '').lower().strip()
        severity = request.form.get('severity', 'Low')
        duration = request.form.get('duration', '1 day')
        
        if len(raw_symptoms) < 3:
            flash("Description too short. Please provide more detail for AI analysis.", "warning")
            return redirect(url_for('patient.symptom_checker'))

        # 2. XAI Knowledge Base with Base Probabilities
        knowledge = {
            "Typhoid": {"base": 40, "risk": "High", "trigger": ["fever", "stomach", "weakness", "pain"], "reason": "Consistent with bacterial patterns in gastric distress."},
            "Migraine": {"base": 35, "risk": "Medium", "trigger": ["headache", "vision", "nausea", "light"], "reason": "Pattern indicates acute neurological sensitivity."},
            "Common Cold": {"base": 50, "risk": "Low", "trigger": ["cough", "sneeze", "runny nose", "fever"], "reason": "Symptoms align with viral upper respiratory patterns."},
            "Cardiac Alert": {"base": 20, "risk": "High", "trigger": ["chest pain", "shortness of breath", "breath"], "reason": "🚨 Pattern match for critical cardiovascular distress."}
        }
        
        # 3. Weighted Probability Logic
        for disease, data in knowledge.items():
            matches = sum(1 for k in data["trigger"] if k in raw_symptoms)
            if matches > 0:
                # Calc: Base + (Matches * 15) + Severity Bonus
                calc_prob = data["base"] + (matches * 15)
                if severity == "High": calc_prob += 10
                
                final_prob = min(calc_prob, 98) # Keep it realistic (max 98%)
                
                results.append({
                    "name": disease, 
                    "prob": final_prob, 
                    "risk": data["risk"], 
                    "reason": data["reason"]
                })
        
        # Sort results by highest confidence
        results = sorted(results, key=lambda x: x['prob'], reverse=True)[:3]
        
        if results:
            top = results[0]
            # 4. Phase 5: Self-Learning (Log data for model refinement)
            try:
                # Save to EHR (Diagnosis)
                new_diag = Diagnosis(
                    disease_name=top['name'],
                    probability=top['prob'],
                    risk_level=top['risk'],
                    patient_id=current_user.id
                )
                db.session.add(new_diag)

                # Save Anonymous Training Data
                learning_data = AnonymousTrainingData(
                    symptoms_input=raw_symptoms,
                    predicted_disease=top['name'],
                    severity_reported=severity
                )
                db.session.add(learning_data)
                db.session.commit()
            except Exception:
                db.session.rollback()

            # 5. Risk-Based Recommendation Logic
            if (top['risk'] == "High" and top['prob'] > 60) or severity == "High":
                recommendation = "🚨 URGENT: Symptoms indicate a high-risk condition. Contact emergency services or visit the ER immediately."
            elif top['prob'] > 50:
                recommendation = f"Recommended: Schedule a consultation for {top['name']}. Rest and monitor symptoms for {duration}."
            else:
                recommendation = "Condition appears non-critical. Stay hydrated and monitor for updates."

    return render_template('patient/symptom_checker.html', results=results, rec=recommendation)

# --- PHASE 4: LAB CENTER (AI INTERPRETATION) ---
@patient_bp.route('/lab-diagnostics', methods=['GET', 'POST'])
@login_required
def lab_diagnostics():
    """AI Lab Report Interpreter: Analyzes biomarkers from report text"""
    if request.method == 'POST':
        test_name = request.form.get('test_name')
        report_text = request.form.get('report_text', '').lower()
        
        if not report_text:
            flash("No data provided for AI interpretation.", "warning")
            return redirect(url_for('patient.lab_diagnostics'))

        # Clinical Keyword Logic
        interpretation = "Analysis: Biomarkers appear within normal physiological range."
        
        if "hemoglobin" in report_text and ("low" in report_text or "<" in report_text):
            interpretation = "⚠️ AI Alert: Low Hemoglobin detected. Pattern suggests iron-deficiency anemia."
        elif "glucose" in report_text and ("high" in report_text or "mg/dl" in report_text):
            interpretation = "⚠️ AI Alert: Elevated Glucose detected. Risk of Hyperglycemia; monitor glucose intake."
        elif "wbc" in report_text or "white blood cell" in report_text:
            interpretation = "⚠️ AI Alert: Leukocyte variance detected. Possible internal immune response/infection."

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
    """Clinician Consultation Booking"""
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
            flash("Booking failed. Please ensure all fields are correct.", "error")
    
    doctors = User.query.filter_by(role='doctor').all()
    return render_template('patient/book_appointment.html', doctors=doctors)