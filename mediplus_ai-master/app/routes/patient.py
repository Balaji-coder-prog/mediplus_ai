import os
import joblib
import numpy as np
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file
from flask_login import login_required, current_user
from app.models import User, Appointment, LabReport, Diagnosis, Prescription
from app import db

# Blueprint definition
patient_bp = Blueprint('patient', __name__)

# --- 🤖 AI MODEL CONFIGURATION ---
MODEL_PATH = os.path.join('app', 'ai_models', 'disease_model.pkl')
SYMPTOM_PATH = os.path.join('app', 'ai_models', 'symptoms_list.pkl')

try:
    if os.path.exists(MODEL_PATH) and os.path.exists(SYMPTOM_PATH):
        model = joblib.load(MODEL_PATH)
        symptoms_list = joblib.load(SYMPTOM_PATH)
    else:
        model, symptoms_list = None, []
        print("⚠️ AI Engine offline: Model files not found.")
except Exception as e:
    model, symptoms_list = None, []
    print(f"❌ AI Load Error: {e}")

# --- 🛠️ ADVANCED LOCALIZATION ENGINE ---
def get_text(lang, key, disease=None, matches=0):
    """Centralized dictionary for all UI text and AI feedback"""
    data = {
        "English": {
            "res": f"Matches {matches} clinical markers identified in your description.",
            "rec_h": "🚨 URGENT: Symptoms match high-risk patterns. Contact emergency services or visit the ER immediately.",
            "rec_m": f"Suggested: Schedule a specialist consultation for {disease}. Monitor symptoms for 24 hours.",
            "rec_l": "Condition appears stable. Stay hydrated, rest, and track any new symptoms.",
            "book_s": "Appointment Confirmed! You can view it in your dashboard.",
            "pay_err": "Subscription required to book clinical appointments.",
            "up_success": "Success! You are now a Pro user. All premium features unlocked.",
            "cancel": "Appointment cancelled successfully."
        },
        "Tanglish": {
            "res": f"Ungaloda description-la {matches} medical markers match aagudhu.",
            "rec_h": "🚨 URGENT: Risk romba high-ah iruku. Udane Hospital ponga illa emergency-ku call pannunga!",
            "rec_m": f"Suggested: {disease} pathi specialist doctor kitta pesunga. 24 hours symptoms-ah follow pannunga.",
            "rec_l": "Normal-ah dhaan iruku. Nalla rest edunga, water nalla kudinga.",
            "book_s": "Appointment Confirm aayidichu! Dashboard-la check pannikalam.",
            "pay_err": "Appointment book panna subscription pay panni irukanum!",
            "up_success": "Success! Neenga ippo Pro user. Doctor appointments ippo unlock aayidichu!",
            "cancel": "Appointment cancel panniyaachu."
        },
        "Tamil": {
            "res": f"உங்கள் விளக்கத்தில் {matches} மருத்துவ குறிகள் கண்டறியப்பட்டுள்ளன.",
            "rec_h": "🚨 அவசரம்: உங்கள் அறிகுறிகள் அதிக ஆபத்தானவை. உடனடியாக அவசர சிகிச்சை பிரிவை அணுகவும்.",
            "rec_m": f"பரிந்துரை: {disease} குறித்து மருத்துவரிடம் ஆலோசனை பெறவும். 24 மணிநேரம் கண்காணிக்கவும்.",
            "rec_l": "நிலைமை சீராக உள்ளது. போதுமான ஓய்வு மற்றும் தண்ணீர் அவசியம்.",
            "book_s": "முன்பதிவு உறுதி செய்யப்பட்டது! உங்கள் டாஷ்போர்டில் பார்க்கலாம்.",
            "pay_err": "முன்பதிவு செய்ய சந்தா செலுத்த வேண்டும்.",
            "up_success": "வெற்றி! நீங்கள் இப்போது புரோ பயனர். அனைத்து சேவைகளும் தயார்.",
            "cancel": "முன்பதிவு ரத்து செய்யப்பட்டது."
        }
    }
    return data.get(lang, data["English"]).get(key)

# --- 📈 DASHBOARD & ANALYTICS ---

@patient_bp.route('/dashboard')
@login_required
def dashboard():
    """Renders clinical dashboard with EHR trends and summary"""
    appts = Appointment.query.filter_by(patient_id=current_user.id).order_by(Appointment.id.desc()).all()
    diags = Diagnosis.query.filter_by(patient_id=current_user.id).order_by(Diagnosis.id.desc()).limit(5).all()
    reports = LabReport.query.filter_by(patient_id=current_user.id).order_by(LabReport.id.desc()).limit(3).all()
    prescriptions = Prescription.query.filter_by(patient_id=current_user.id).all()
    
    # Calculate health score placeholder
    health_score = 85 if not diags else 100 - (len(diags) * 5)
    
    return render_template('patient/dashboard.html', 
                           appointments=appts, 
                           recent_diagnoses=diags, 
                           lab_reports=reports,
                           prescriptions=prescriptions,
                           score=health_score)

# --- 👤 PATIENT PROFILE & EHR SETUP ---

@patient_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
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
            flash("System Error: Could not update profile.", "error")
    return render_template('patient/profile.html')

# --- 🧪 ML SYMPTOM ENGINE ---

@patient_bp.route('/symptom-checker', methods=['GET', 'POST'])
@login_required
def symptom_checker():
    results, rec = [], None
    plan = getattr(current_user, 'subscription_plan', 'trial')
    
    if request.method == 'POST':
        raw = request.form.get('symptoms', '').lower().strip()
        lang = request.form.get('output_lang', 'English')
        
        if not model or not symptoms_list:
            flash("AI Engine is initializing. Please try again in a moment.", "info")
            return redirect(url_for('patient.symptom_checker'))

        # Vectorization
        vector = np.zeros(len(symptoms_list))
        matches = 0
        for i, s in enumerate(symptoms_list):
            if s.replace('_', ' ') in raw:
                vector[i] = 1
                matches += 1

        if matches > 0:
            probs = model.predict_proba([vector])[0]
            top_indices = np.argsort(probs)[-3:][::-1]
            
            for idx in top_indices:
                conf = round(probs[idx] * 100, 2)
                if conf > 5:
                    disease = model.classes_[idx]
                    risk = "High" if conf > 75 else "Medium" if conf > 40 else "Low"
                    results.append({
                        "name": disease, 
                        "prob": conf, 
                        "risk": risk, 
                        "reason": get_text(lang, "res", matches=matches)
                    })

            if results:
                top = results[0]
                rec = get_text(lang, "rec_h" if top['risk'] == "High" else "rec_m", disease=top['name'])
                
                # Auto-save diagnosis to EHR
                new_diag = Diagnosis(disease_name=top['name'], probability=top['prob'], 
                                     risk_level=top['risk'], patient_id=current_user.id)
                db.session.add(new_diag)
                db.session.commit()
        else:
            flash("AI could not identify clinical symptoms. Please describe more.", "warning")

    return render_template('patient/symptom_checker.html', results=results, rec=rec, user_plan=plan)

# --- 📅 CONSULTATION & BOOKING ---

@patient_bp.route('/pricing')
@login_required
def pricing():
    return render_template('patient/pricing.html')

@patient_bp.route('/upgrade', methods=['POST'])
@login_required
def upgrade_plan():
    current_user.subscription_plan = 'pro'
    db.session.commit()
    flash(get_text('Tanglish', "up_success"), "success")
    return redirect(url_for('patient.book_appointment'))

@patient_bp.route('/book', methods=['GET', 'POST'])
@login_required
def book_appointment():
    plan = getattr(current_user, 'subscription_plan', 'trial')
    if plan == 'trial':
        flash(get_text('Tanglish', "pay_err"), "info")
        return redirect(url_for('patient.pricing'))

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
            flash(get_text(request.form.get('lang', 'English'), "book_s"), "success")
            return redirect(url_for('patient.dashboard'))
        except Exception:
            db.session.rollback()
            flash("Booking failed. Please check your inputs.", "error")
    
    docs = User.query.filter_by(role='doctor').all()
    return render_template('patient/book_appointment.html', doctors=docs, user_plan=plan)

@patient_bp.route('/cancel-appointment/<int:id>')
@login_required
def cancel_appointment(id):
    appt = Appointment.query.get_or_404(id)
    if appt.patient_id == current_user.id:
        db.session.delete(appt)
        db.session.commit()
        flash(get_text('English', "cancel"), "success")
    return redirect(url_for('patient.dashboard'))

# --- 🔬 LABS & REPORTS ---

@patient_bp.route('/lab-diagnostics', methods=['GET', 'POST'])
@login_required
def lab_diagnostics():
    if request.method == 'POST':
        test = request.form.get('test_name')
        report = request.form.get('report_text', '').lower()
        
        interp = "Analysis: Normal biomarkers."
        if "hemoglobin" in report and ("low" in report or "9" in report):
            interp = "⚠️ AI Alert: Low Hemoglobin detected. Pattern suggests iron-deficiency anemia."
        elif "glucose" in report and "high" in report:
            interp = "⚠️ AI Alert: Elevated Glucose detected. Possible Hyperglycemia."

        db.session.add(LabReport(test_name=test, ai_interpretation=interp, patient_id=current_user.id))
        db.session.commit()
        flash("Lab report analyzed and saved to EHR.", "success")
        return redirect(url_for('patient.dashboard'))
    
    return render_template('patient/lab_tests.html', user_plan=getattr(current_user, 'subscription_plan', 'trial'))

# --- 💊 PHARMACY & PRESCRIPTIONS ---

@patient_bp.route('/my-prescriptions')
@login_required
def my_prescriptions():
    prescriptions = Prescription.query.filter_by(patient_id=current_user.id).all()
    return render_template('patient/prescriptions.html', prescriptions=prescriptions)

@patient_bp.route('/export-ehr')
@login_required
def export_ehr():
    """Feature placeholder for generating PDF health summaries"""
    flash("PDF Export feature is being prepared for your EHR.", "info")
    return redirect(url_for('patient.dashboard'))