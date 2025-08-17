"""
Registration routes for patient management
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.patients import Patient
from app.models.visits import Visit, Appointment
from app.models.departments import Department
from app.security import require_permission, audit_log
from datetime import datetime, timedelta
import json

registration_bp = Blueprint('registration', __name__)

@registration_bp.route('/')
@login_required
@require_permission('patient_read')
def index():
    """Registration dashboard"""
    today = datetime.now().date()
    
    # Get today's appointments
    today_appointments = Appointment.get_today_appointments()
    
    # Get open visits
    open_visits = Visit.get_open_visits()
    
    # Get recent patients
    recent_patients = Patient.query.filter_by(active=True)\
                                  .order_by(Patient.created_at.desc())\
                                  .limit(10).all()
    
    return render_template('registration/index.html',
                         today_appointments=today_appointments,
                         open_visits=open_visits,
                         recent_patients=recent_patients)

@registration_bp.route('/patients')
@login_required
@require_permission('patient_read')
def patients():
    """Patient list view"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    if search:
        patients = Patient.search_patients(search)
    else:
        patients = Patient.query.filter_by(active=True)\
                               .order_by(Patient.last_name, Patient.first_name)\
                               .paginate(page=page, per_page=20, error_out=False)
    
    return render_template('registration/patients.html', patients=patients, search=search)

@registration_bp.route('/patients/new', methods=['GET', 'POST'])
@login_required
@require_permission('patient_create')
def new_patient():
    """Create new patient"""
    if request.method == 'POST':
        try:
            # Generate MRN
            mrn = Patient.generate_mrn()
            
            # Create patient
            patient = Patient(
                mrn=mrn,
                national_id=request.form.get('national_id'),
                first_name=request.form.get('first_name'),
                last_name=request.form.get('last_name'),
                middle_name=request.form.get('middle_name'),
                dob=datetime.strptime(request.form.get('dob'), '%Y-%m-%d').date(),
                sex=request.form.get('sex'),
                phone=request.form.get('phone'),
                email=request.form.get('email'),
                address=request.form.get('address'),
                city=request.form.get('city'),
                state=request.form.get('state'),
                postal_code=request.form.get('postal_code'),
                country=request.form.get('country', 'Country'),
                emergency_contact_name=request.form.get('emergency_contact_name'),
                emergency_contact_phone=request.form.get('emergency_contact_phone'),
                emergency_contact_relationship=request.form.get('emergency_contact_relationship'),
                blood_type=request.form.get('blood_type'),
                allergies=request.form.get('allergies'),
                chronic_conditions=request.form.get('chronic_conditions')
            )
            
            db.session.add(patient)
            db.session.commit()
            
            audit_log('patient_create', 'Patient', patient.id, 
                     after_data=patient.to_dict())
            
            flash('Patient created successfully!', 'success')
            return redirect(url_for('registration.patient_detail', patient_id=patient.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating patient: {str(e)}', 'error')
    
    return render_template('registration/new_patient.html')

@registration_bp.route('/patients/<int:patient_id>')
@login_required
@require_permission('patient_read')
def patient_detail(patient_id):
    """Patient detail view"""
    patient = Patient.query.get_or_404(patient_id)
    
    # Get recent visits
    recent_visits = patient.get_visit_history(limit=10)
    
    # Get recent appointments
    recent_appointments = patient.appointments.order_by(Appointment.start_dt.desc()).limit(10).all()
    
    return render_template('registration/patient_detail.html',
                         patient=patient,
                         recent_visits=recent_visits,
                         recent_appointments=recent_appointments)

@registration_bp.route('/patients/<int:patient_id>/edit', methods=['GET', 'POST'])
@login_required
@require_permission('patient_update')
def edit_patient(patient_id):
    """Edit patient"""
    patient = Patient.query.get_or_404(patient_id)
    
    if request.method == 'POST':
        try:
            before_data = patient.to_dict()
            
            # Update patient fields
            patient.national_id = request.form.get('national_id')
            patient.first_name = request.form.get('first_name')
            patient.last_name = request.form.get('last_name')
            patient.middle_name = request.form.get('middle_name')
            patient.dob = datetime.strptime(request.form.get('dob'), '%Y-%m-%d').date()
            patient.sex = request.form.get('sex')
            patient.phone = request.form.get('phone')
            patient.email = request.form.get('email')
            patient.address = request.form.get('address')
            patient.city = request.form.get('city')
            patient.state = request.form.get('state')
            patient.postal_code = request.form.get('postal_code')
            patient.country = request.form.get('country', 'Country')
            patient.emergency_contact_name = request.form.get('emergency_contact_name')
            patient.emergency_contact_phone = request.form.get('emergency_contact_phone')
            patient.emergency_contact_relationship = request.form.get('emergency_contact_relationship')
            patient.blood_type = request.form.get('blood_type')
            patient.allergies = request.form.get('allergies')
            patient.chronic_conditions = request.form.get('chronic_conditions')
            
            db.session.commit()
            
            audit_log('patient_update', 'Patient', patient.id, 
                     before_data=before_data, after_data=patient.to_dict())
            
            flash('Patient updated successfully!', 'success')
            return redirect(url_for('registration.patient_detail', patient_id=patient.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating patient: {str(e)}', 'error')
    
    return render_template('registration/edit_patient.html', patient=patient)

@registration_bp.route('/visits/new', methods=['GET', 'POST'])
@login_required
@require_permission('visit_create')
def new_visit():
    """Create new visit"""
    if request.method == 'POST':
        try:
            patient_id = request.form.get('patient_id')
            clinic_id = request.form.get('clinic_id')
            
            # Get patient
            patient = Patient.query.get_or_404(patient_id)
            
            # Create visit
            visit = Visit(
                patient_id=patient_id,
                clinic_id=clinic_id,
                visit_date=datetime.now().date(),
                visit_time=datetime.now().time(),
                triage_level=request.form.get('triage_level'),
                payer_type=request.form.get('payer_type', 'cash'),
                chief_complaint=request.form.get('chief_complaint'),
                notes=request.form.get('notes')
            )
            
            db.session.add(visit)
            db.session.commit()
            
            audit_log('visit_create', 'Visit', visit.id, 
                     after_data=visit.to_dict())
            
            flash('Visit created successfully!', 'success')
            return redirect(url_for('registration.visit_detail', visit_id=visit.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating visit: {str(e)}', 'error')
    
    # Get patients and clinics for form
    patients = Patient.query.filter_by(active=True).order_by(Patient.last_name, Patient.first_name).all()
    clinics = Department.get_clinical_departments()
    
    return render_template('registration/new_visit.html', patients=patients, clinics=clinics)

@registration_bp.route('/visits/<int:visit_id>')
@login_required
@require_permission('visit_read')
def visit_detail(visit_id):
    """Visit detail view"""
    visit = Visit.query.get_or_404(visit_id)
    
    return render_template('registration/visit_detail.html', visit=visit)

@registration_bp.route('/appointments')
@login_required
@require_permission('visit_read')
def appointments():
    """Appointments list"""
    date = request.args.get('date')
    if date:
        date = datetime.strptime(date, '%Y-%m-%d').date()
    else:
        date = datetime.now().date()
    
    appointments = Appointment.get_today_appointments()
    
    return render_template('registration/appointments.html', 
                         appointments=appointments, selected_date=date)

@registration_bp.route('/appointments/new', methods=['GET', 'POST'])
@login_required
@require_permission('visit_create')
def new_appointment():
    """Create new appointment"""
    if request.method == 'POST':
        try:
            # Create appointment
            appointment = Appointment(
                patient_id=request.form.get('patient_id'),
                clinic_id=request.form.get('clinic_id'),
                provider_id=request.form.get('provider_id'),
                start_dt=datetime.strptime(request.form.get('start_dt'), '%Y-%m-%dT%H:%M'),
                appointment_type=request.form.get('appointment_type'),
                notes=request.form.get('notes')
            )
            
            db.session.add(appointment)
            db.session.commit()
            
            audit_log('appointment_create', 'Appointment', appointment.id, 
                     after_data=appointment.to_dict())
            
            flash('Appointment created successfully!', 'success')
            return redirect(url_for('registration.appointments'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating appointment: {str(e)}', 'error')
    
    # Get form data
    patients = Patient.query.filter_by(active=True).order_by(Patient.last_name, Patient.first_name).all()
    clinics = Department.get_clinical_departments()
    
    return render_template('registration/new_appointment.html', 
                         patients=patients, clinics=clinics)

# API endpoints for AJAX calls
@registration_bp.route('/api/patients/search')
@login_required
@require_permission('patient_read')
def api_patient_search():
    """Search patients via AJAX"""
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    
    patients = Patient.search_patients(query, limit=10)
    return jsonify([{
        'id': p.id,
        'mrn': p.mrn,
        'name': p.full_name,
        'dob': p.dob.isoformat() if p.dob else None,
        'phone': p.phone
    } for p in patients])

@registration_bp.route('/api/departments/<int:dept_id>/staff')
@login_required
def api_department_staff(dept_id):
    """Get staff for a department"""
    from app.models.staff import Staff
    staff = Staff.get_department_staff(dept_id)
    return jsonify([{
        'id': s.id,
        'name': s.name,
        'role': s.role.name if s.role else None
    } for s in staff])
