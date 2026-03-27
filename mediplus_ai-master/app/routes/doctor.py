from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import User, Appointment, Prescription, Diagnosis, LabReport
from app import db

doctor_bp = Blueprint('doctor', __name__)

@doctor_bp.route('/dashboard')
@login_required
def dashboard():
    """Doctor's Command Center: Manage Patient Queue & AI Insights"""
    if current_user.role != 'doctor':
        flash("Access Denied: Clinician credentials required.", "danger")
        return redirect(url_for('patient.dashboard'))
    
    # 1. Fetch appointments where the doctor name matches (handling "Dr." prefix)
    # This matches the 'Dr. Username' format used in your booking flow
    search_name = f"Dr. {current_user.username}"
    my_appointments = Appointment.query.filter_by(doctor_name=search_name).order_by(Appointment.id.desc()).all()
    
    # 2. Get distinct patients associated with these appointments for a quick queue
    patient_ids = [a.patient_id for a in my_appointments]
    unique_patients = User.query.filter(User.id.in_(patient_ids)).all() if patient_ids else []

    return render_template('doctor/dashboard.html', 
                           appointments=my_appointments, 
                           patients=unique_patients)

@doctor_bp.route('/prescribe/<int:appt_id>', methods=['GET', 'POST'])
@login_required
def prescribe(appt_id):
    """EHR Review & Prescription Interface"""
    if current_user.role != 'doctor':
        return redirect(url_for('patient.dashboard'))

    appointment = Appointment.query.get_or_404(appt_id)
    patient = User.query.get(appointment.patient_id)

    # 1. Fetch AI Context: What did the AI find before this visit?
    # This is the "Magic" — showing the AI's work to the doctor
    ai_diagnoses = Diagnosis.query.filter_by(patient_id=patient.id).order_by(Diagnosis.id.desc()).limit(3).all()
    ai_labs = LabReport.query.filter_by(patient_id=patient.id).order_by(LabReport.id.desc()).limit(2).all()

    if request.method == 'POST':
        try:
            # 2. Save Clinical Prescription
            new_presc = Prescription(
                details=request.form.get('meds'),
                patient_id=appointment.patient_id
            )
            
            # 3. Update Appointment Workflow
            appointment.status = 'Completed'
            
            db.session.add(new_presc)
            db.session.commit()
            
            flash(f"Clinical Validation Complete. Prescription synced to {patient.username.title()}'s EHR.", "success")
            return redirect(url_for('doctor.dashboard'))
        except Exception:
            db.session.rollback()
            flash("System Error: Could not save prescription.", "error")
        
    return render_template('doctor/prescribe.html', 
                           appt=appointment, 
                           patient=patient, 
                           ai_diagnoses=ai_diagnoses,
                           ai_labs=ai_labs)