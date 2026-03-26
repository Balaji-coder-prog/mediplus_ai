from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import User, Appointment, Prescription, db

doctor_bp = Blueprint('doctor', __name__)

@doctor_bp.route('/dashboard')
@login_required
def dashboard():
    # Only doctors can access this
    if current_user.role != 'doctor':
        flash("Access Denied: Doctors Only.", "danger")
        return redirect(url_for('patient.dashboard'))
    
    # Fetch all appointments booked for this specific doctor
    # In the flow, we use the doctor's username as the identifier
    my_appointments = Appointment.query.filter_by(doctor_name=f"Dr. {current_user.username}").all()
    return render_template('doctor/dashboard.html', appointments=my_appointments)

@doctor_bp.route('/prescribe/<int:appt_id>', methods=['GET', 'POST'])
@login_required
def prescribe(appt_id):
    appointment = Appointment.query.get_or_404(appt_id)
    
    if request.method == 'POST':
        new_presc = Prescription(
            details=request.form.get('meds'),
            patient_id=appointment.patient_id
        )
        # Update appointment status as per flow
        appointment.status = 'Completed'
        db.session.add(new_presc)
        db.session.commit()
        
        flash("E-Prescription uploaded to Patient EHR successfully!", "success")
        return redirect(url_for('doctor.dashboard'))
        
    return render_template('doctor/prescribe.html', appt=appointment)