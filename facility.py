"""
Facility management routes for multi-facility HIS
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import login_required, current_user
from app.models import Facility, StaffFacility, Staff, Department, Patient, Visit
from app.extensions import db
from app.security import require_permission, audit_log, require_role
from app.utils.session import set_current_facility, get_current_facility, get_user_facilities
from datetime import datetime, timedelta
import json

facility_bp = Blueprint('facility', __name__, url_prefix='/facility')

@facility_bp.route('/select')
@login_required
def select():
    """Facility selection page"""
    facilities = get_user_facilities()
    
    if not facilities:
        flash('You do not have access to any facilities', 'error')
        return redirect(url_for('auth.logout'))
    
    if len(facilities) == 1:
        # Auto-select if user has access to only one facility
        set_current_facility(facilities[0].id)
        flash(f'Welcome to {facilities[0].name}', 'success')
        return redirect(url_for('dashboard.index'))
    
    return render_template('facility/select.html', facilities=facilities)

@facility_bp.route('/switch/<int:facility_id>', methods=['POST'])
@login_required
def switch(facility_id):
    """Switch to a different facility"""
    if set_current_facility(facility_id):
        facility = Facility.query.get(facility_id)
        flash(f'Switched to {facility.name}', 'success')
        return redirect(url_for('dashboard.index'))
    else:
        flash('Access denied to this facility', 'error')
        return redirect(url_for('facility.select'))

@facility_bp.route('/manage')
@login_required
@require_role('superadmin')
def manage():
    """Facility management for superadmin"""
    facilities = Facility.get_active_facilities()
    return render_template('facility/manage.html', facilities=facilities)

@facility_bp.route('/new', methods=['GET', 'POST'])
@login_required
@require_role('superadmin')
def new_facility():
    """Create new facility"""
    if request.method == 'POST':
        data = request.form
        
        facility = Facility(
            facility_code=data.get('facility_code'),
            name=data.get('name'),
            type=data.get('type'),
            address=data.get('address'),
            city=data.get('city'),
            state=data.get('state'),
            country=data.get('country'),
            postal_code=data.get('postal_code'),
            phone=data.get('phone'),
            email=data.get('email'),
            website=data.get('website'),
            bed_count=int(data.get('bed_count', 0)),
            emergency_beds=int(data.get('emergency_beds', 0)),
            icu_beds=int(data.get('icu_beds', 0)),
            operating_rooms=int(data.get('operating_rooms', 0)),
            license_number=data.get('license_number'),
            accreditation=data.get('accreditation'),
            established_date=datetime.strptime(data.get('established_date'), '%Y-%m-%d').date() if data.get('established_date') else None
        )
        
        db.session.add(facility)
        db.session.commit()
        
        audit_log('facility.created', facility.id, f"Created facility {facility.facility_code}")
        flash('Facility created successfully', 'success')
        return redirect(url_for('facility.manage'))
    
    return render_template('facility/new_facility.html')

@facility_bp.route('/<int:facility_id>')
@login_required
@require_permission('facility.view')
def detail(facility_id):
    """View facility details"""
    facility = Facility.query.get_or_404(facility_id)
    
    # Check if user has access to this facility
    if not current_user.has_facility_access(facility_id):
        flash('Access denied to this facility', 'error')
        return redirect(url_for('facility.select'))
    
    # Get facility statistics
    stats = Facility.get_facility_statistics(facility_id)
    
    return render_template('facility/detail.html', facility=facility, stats=stats[0] if stats else None)

@facility_bp.route('/<int:facility_id>/edit', methods=['GET', 'POST'])
@login_required
@require_role('superadmin')
def edit_facility(facility_id):
    """Edit facility"""
    facility = Facility.query.get_or_404(facility_id)
    
    if request.method == 'POST':
        data = request.form
        
        facility.facility_code = data.get('facility_code')
        facility.name = data.get('name')
        facility.type = data.get('type')
        facility.address = data.get('address')
        facility.city = data.get('city')
        facility.state = data.get('state')
        facility.country = data.get('country')
        facility.postal_code = data.get('postal_code')
        facility.phone = data.get('phone')
        facility.email = data.get('email')
        facility.website = data.get('website')
        facility.bed_count = int(data.get('bed_count', 0))
        facility.emergency_beds = int(data.get('emergency_beds', 0))
        facility.icu_beds = int(data.get('icu_beds', 0))
        facility.operating_rooms = int(data.get('operating_rooms', 0))
        facility.license_number = data.get('license_number')
        facility.accreditation = data.get('accreditation')
        facility.established_date = datetime.strptime(data.get('established_date'), '%Y-%m-%d').date() if data.get('established_date') else None
        
        db.session.commit()
        
        audit_log('facility.updated', facility.id, f"Updated facility {facility.facility_code}")
        flash('Facility updated successfully', 'success')
        return redirect(url_for('facility.detail', facility_id=facility.id))
    
    return render_template('facility/edit_facility.html', facility=facility)

@facility_bp.route('/<int:facility_id>/staff')
@login_required
@require_permission('facility.view')
def staff(facility_id):
    """View facility staff"""
    facility = Facility.query.get_or_404(facility_id)
    
    # Check if user has access to this facility
    if not current_user.has_facility_access(facility_id):
        flash('Access denied to this facility', 'error')
        return redirect(url_for('facility.select'))
    
    staff_facilities = StaffFacility.get_facility_staff(facility_id)
    
    return render_template('facility/staff.html', facility=facility, staff_facilities=staff_facilities)

@facility_bp.route('/<int:facility_id>/staff/assign', methods=['GET', 'POST'])
@login_required
@require_role('superadmin')
def assign_staff(facility_id):
    """Assign staff to facility"""
    facility = Facility.query.get_or_404(facility_id)
    
    if request.method == 'POST':
        data = request.form
        staff_id = int(data.get('staff_id'))
        
        # Check if assignment already exists
        existing = StaffFacility.query.filter_by(
            staff_id=staff_id,
            facility_id=facility_id
        ).first()
        
        if existing:
            flash('Staff member already assigned to this facility', 'warning')
        else:
            staff_facility = StaffFacility(
                staff_id=staff_id,
                facility_id=facility_id,
                can_access=data.get('can_access') == 'on',
                can_manage_staff=data.get('can_manage_staff') == 'on',
                can_manage_facility=data.get('can_manage_facility') == 'on',
                can_view_reports=data.get('can_view_reports') == 'on',
                can_export_data=data.get('can_export_data') == 'on',
                assigned_by_id=current_user.id,
                notes=data.get('notes')
            )
            
            db.session.add(staff_facility)
            db.session.commit()
            
            audit_log('facility.staff_assigned', facility.id, f"Assigned staff {staff_id} to facility {facility.facility_code}")
            flash('Staff assigned successfully', 'success')
        
        return redirect(url_for('facility.staff', facility_id=facility.id))
    
    # Get all staff not assigned to this facility
    assigned_staff_ids = [sf.staff_id for sf in StaffFacility.query.filter_by(facility_id=facility_id).all()]
    available_staff = Staff.query.filter(
        Staff.active == True,
        ~Staff.id.in_(assigned_staff_ids)
    ).all()
    
    return render_template('facility/assign_staff.html', facility=facility, available_staff=available_staff)

@facility_bp.route('/<int:facility_id>/departments')
@login_required
@require_permission('facility.view')
def departments(facility_id):
    """View facility departments"""
    facility = Facility.query.get_or_404(facility_id)
    
    # Check if user has access to this facility
    if not current_user.has_facility_access(facility_id):
        flash('Access denied to this facility', 'error')
        return redirect(url_for('facility.select'))
    
    departments = Department.query.filter_by(facility_id=facility_id, active=True).all()
    
    return render_template('facility/departments.html', facility=facility, departments=departments)

# API endpoints
@facility_bp.route('/api/facilities')
@login_required
def api_facilities():
    """Get facilities for API"""
    facilities = get_user_facilities()
    
    return jsonify({
        'facilities': [{
            'id': f.id,
            'facility_code': f.facility_code,
            'name': f.name,
            'type': f.type,
            'city': f.city,
            'state': f.state
        } for f in facilities]
    })

@facility_bp.route('/api/current-facility')
@login_required
def api_current_facility():
    """Get current facility for API"""
    facility = get_current_facility()
    
    if not facility:
        return jsonify({'error': 'No facility selected'}), 400
    
    return jsonify({
        'id': facility.id,
        'facility_code': facility.facility_code,
        'name': facility.name,
        'type': facility.type,
        'city': facility.city,
        'state': facility.state
    })

@facility_bp.route('/api/facility-stats/<int:facility_id>')
@login_required
def api_facility_stats(facility_id):
    """Get facility statistics for API"""
    # Check if user has access to this facility
    if not current_user.has_facility_access(facility_id):
        return jsonify({'error': 'Access denied'}), 403
    
    stats = Facility.get_facility_statistics(facility_id)
    
    if not stats:
        return jsonify({'error': 'Facility not found'}), 404
    
    stat = stats[0]
    return jsonify({
        'facility': {
            'id': stat['facility'].id,
            'name': stat['facility'].name,
            'facility_code': stat['facility'].facility_code
        },
        'patient_count': stat['patient_count'],
        'staff_count': stat['staff_count'],
        'today_visits': stat['today_visits']
    })
