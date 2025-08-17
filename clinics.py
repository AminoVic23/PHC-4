"""
Clinics routes for clinical operations
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.visits import Visit, Appointment
from app.models.clinical_notes import ClinicalNote
from app.models.orders import Order
from app.models.patients import Patient
from app.models.departments import Department
from app.security import require_permission, audit_log
from datetime import datetime, timedelta
import json

clinics_bp = Blueprint('clinics', __name__)

@clinics_bp.route('/')
@login_required
@require_permission('visit_read')
def index():
    """Clinics dashboard"""
    today = datetime.now().date()
    
    # Get today's appointments for current user
    today_appointments = Appointment.get_today_appointments(provider_id=current_user.id)
    
    # Get open visits in user's department
    open_visits = Visit.get_open_visits(clinic_id=current_user.department_id)
    
    # Get recent clinical notes by user
    recent_notes = ClinicalNote.get_provider_notes(current_user.id, limit=5)
    
    return render_template('clinics/index.html',
                         today_appointments=today_appointments,
                         open_visits=open_visits,
                         recent_notes=recent_notes)

@clinics_bp.route('/queue')
@login_required
@require_permission('visit_read')
def queue():
    """Patient queue view"""
    # Get open visits in user's department
    open_visits = Visit.get_open_visits(clinic_id=current_user.department_id)
    
    # Get today's appointments
    today_appointments = Appointment.get_today_appointments(clinic_id=current_user.department_id)
    
    return render_template('clinics/queue.html',
                         open_visits=open_visits,
                         today_appointments=today_appointments)

@clinics_bp.route('/visits/<int:visit_id>')
@login_required
@require_permission('visit_read')
def visit_detail(visit_id):
    """Visit detail view for clinical staff"""
    visit = Visit.query.get_or_404(visit_id)
    
    # Get clinical notes for this visit
    clinical_notes = ClinicalNote.get_visit_notes(visit_id)
    
    # Get orders for this visit
    orders = Order.get_visit_orders(visit_id)
    
    return render_template('clinics/visit_detail.html',
                         visit=visit,
                         clinical_notes=clinical_notes,
                         orders=orders)

@clinics_bp.route('/visits/<int:visit_id>/notes/new', methods=['GET', 'POST'])
@login_required
@require_permission('clinical_notes_create')
def new_clinical_note(visit_id):
    """Create new clinical note"""
    visit = Visit.query.get_or_404(visit_id)
    
    if request.method == 'POST':
        try:
            # Create clinical note
            note = ClinicalNote(
                visit_id=visit_id,
                provider_id=current_user.id,
                note_type=request.form.get('note_type', 'SOAP'),
                diagnosis_icd=request.form.get('diagnosis_icd'),
                diagnosis_text=request.form.get('diagnosis_text'),
                plan=request.form.get('plan'),
                follow_up_notes=request.form.get('follow_up_notes')
            )
            
            # Set SOAP components
            soap_data = {
                'subjective': request.form.get('subjective', ''),
                'objective': request.form.get('objective', ''),
                'assessment': request.form.get('assessment', ''),
                'plan': request.form.get('plan_component', '')
            }
            note.soap_json = soap_data
            
            db.session.add(note)
            db.session.commit()
            
            audit_log('clinical_notes_create', 'ClinicalNote', note.id, 
                     after_data=note.to_dict())
            
            flash('Clinical note created successfully!', 'success')
            return redirect(url_for('clinics.visit_detail', visit_id=visit_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating clinical note: {str(e)}', 'error')
    
    return render_template('clinics/new_clinical_note.html', visit=visit)

@clinics_bp.route('/visits/<int:visit_id>/notes/<int:note_id>/edit', methods=['GET', 'POST'])
@login_required
@require_permission('clinical_notes_update')
def edit_clinical_note(visit_id, note_id):
    """Edit clinical note"""
    visit = Visit.query.get_or_404(visit_id)
    note = ClinicalNote.query.get_or_404(note_id)
    
    # Check if user can edit this note
    if note.provider_id != current_user.id:
        flash('You can only edit your own clinical notes.', 'error')
        return redirect(url_for('clinics.visit_detail', visit_id=visit_id))
    
    if request.method == 'POST':
        try:
            before_data = note.to_dict()
            
            # Update note fields
            note.note_type = request.form.get('note_type', 'SOAP')
            note.diagnosis_icd = request.form.get('diagnosis_icd')
            note.diagnosis_text = request.form.get('diagnosis_text')
            note.plan = request.form.get('plan')
            note.follow_up_notes = request.form.get('follow_up_notes')
            
            # Update SOAP components
            soap_data = {
                'subjective': request.form.get('subjective', ''),
                'objective': request.form.get('objective', ''),
                'assessment': request.form.get('assessment', ''),
                'plan': request.form.get('plan_component', '')
            }
            note.soap_json = soap_data
            
            db.session.commit()
            
            audit_log('clinical_notes_update', 'ClinicalNote', note.id, 
                     before_data=before_data, after_data=note.to_dict())
            
            flash('Clinical note updated successfully!', 'success')
            return redirect(url_for('clinics.visit_detail', visit_id=visit_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating clinical note: {str(e)}', 'error')
    
    return render_template('clinics/edit_clinical_note.html', visit=visit, note=note)

@clinics_bp.route('/visits/<int:visit_id>/orders/new', methods=['GET', 'POST'])
@login_required
@require_permission('orders_create')
def new_order(visit_id):
    """Create new order"""
    visit = Visit.query.get_or_404(visit_id)
    
    if request.method == 'POST':
        try:
            # Create order
            order = Order(
                visit_id=visit_id,
                ordered_by_id=current_user.id,
                type=request.form.get('order_type'),
                code=request.form.get('code'),
                description=request.form.get('description'),
                priority=request.form.get('priority', 'routine'),
                clinical_indication=request.form.get('clinical_indication'),
                special_instructions=request.form.get('special_instructions')
            )
            
            db.session.add(order)
            db.session.commit()
            
            audit_log('orders_create', 'Order', order.id, 
                     after_data=order.to_dict())
            
            flash('Order created successfully!', 'success')
            return redirect(url_for('clinics.visit_detail', visit_id=visit_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating order: {str(e)}', 'error')
    
    return render_template('clinics/new_order.html', visit=visit)

@clinics_bp.route('/visits/<int:visit_id>/close', methods=['POST'])
@login_required
@require_permission('visit_close')
def close_visit(visit_id):
    """Close a visit"""
    visit = Visit.query.get_or_404(visit_id)
    
    try:
        before_data = visit.to_dict()
        visit.close_visit()
        db.session.commit()
        
        audit_log('visit_close', 'Visit', visit.id, 
                 before_data=before_data, after_data=visit.to_dict())
        
        flash('Visit closed successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error closing visit: {str(e)}', 'error')
    
    return redirect(url_for('clinics.visit_detail', visit_id=visit_id))

@clinics_bp.route('/patients/<int:patient_id>')
@login_required
@require_permission('patient_read')
def patient_detail(patient_id):
    """Patient detail view for clinical staff"""
    patient = Patient.query.get_or_404(patient_id)
    
    # Get recent visits
    recent_visits = patient.get_visit_history(limit=10)
    
    # Get recent clinical notes
    recent_notes = ClinicalNote.query.filter_by(visit_id=Visit.query.filter_by(patient_id=patient_id).subquery())\
                                   .order_by(ClinicalNote.created_at.desc())\
                                   .limit(10).all()
    
    return render_template('clinics/patient_detail.html',
                         patient=patient,
                         recent_visits=recent_visits,
                         recent_notes=recent_notes)

@clinics_bp.route('/appointments')
@login_required
@require_permission('visit_read')
def appointments():
    """Provider's appointments"""
    date = request.args.get('date')
    if date:
        date = datetime.strptime(date, '%Y-%m-%d').date()
    else:
        date = datetime.now().date()
    
    appointments = Appointment.get_provider_appointments(current_user.id, date)
    
    return render_template('clinics/appointments.html', 
                         appointments=appointments, selected_date=date)

@clinics_bp.route('/appointments/<int:appointment_id>/checkin', methods=['POST'])
@login_required
@require_permission('visit_update')
def checkin_appointment(appointment_id):
    """Check in an appointment"""
    appointment = Appointment.query.get_or_404(appointment_id)
    
    try:
        appointment.check_in()
        db.session.commit()
        
        flash('Patient checked in successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error checking in patient: {str(e)}', 'error')
    
    return redirect(url_for('clinics.appointments'))

@clinics_bp.route('/appointments/<int:appointment_id>/complete', methods=['POST'])
@login_required
@require_permission('visit_update')
def complete_appointment(appointment_id):
    """Complete an appointment"""
    appointment = Appointment.query.get_or_404(appointment_id)
    
    try:
        appointment.complete()
        db.session.commit()
        
        flash('Appointment completed successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error completing appointment: {str(e)}', 'error')
    
    return redirect(url_for('clinics.appointments'))

# API endpoints
@clinics_bp.route('/api/visits/<int:visit_id>/vitals', methods=['POST'])
@login_required
@require_permission('visit_update')
def update_vitals(visit_id):
    """Update vital signs for a visit"""
    visit = Visit.query.get_or_404(visit_id)
    
    try:
        vitals_data = request.get_json()
        visit.vital_signs = vitals_data
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Vital signs updated'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@clinics_bp.route('/api/patients/<int:patient_id>/history')
@login_required
@require_permission('patient_read')
def patient_history(patient_id):
    """Get patient history for AJAX"""
    patient = Patient.query.get_or_404(patient_id)
    
    # Get recent visits
    recent_visits = patient.get_visit_history(limit=5)
    
    # Get recent clinical notes
    recent_notes = ClinicalNote.query.join(Visit)\
                                   .filter(Visit.patient_id == patient_id)\
                                   .order_by(ClinicalNote.created_at.desc())\
                                   .limit(5).all()
    
    return jsonify({
        'visits': [v.to_dict() for v in recent_visits],
        'notes': [n.to_dict() for n in recent_notes]
    })
