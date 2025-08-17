"""
API routes for REST API endpoints
"""
from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from app import db
from app.models.patients import Patient
from app.models.visits import Visit, Appointment
from app.models.orders import Order
from app.models.billing import Invoice
from app.models.staff import Staff
from app.security import check_api_permission, audit_log
from datetime import datetime, timedelta
import json

api_bp = Blueprint('api', __name__)

# Authentication endpoints
@api_bp.route('/auth/login', methods=['POST'])
def login():
    """API login endpoint"""
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400
    
    # Find user by email
    user = Staff.find_by_email(data['email'])
    
    if not user or not user.check_password(data['password']) or not user.active:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Create access token
    access_token = create_access_token(identity=user.id)
    
    return jsonify({
        'access_token': access_token,
        'user': user.to_dict()
    })

@api_bp.route('/auth/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user information"""
    user_id = get_jwt_identity()
    user = Staff.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(user.to_dict())

# Patient endpoints
@api_bp.route('/patients', methods=['GET'])
@jwt_required()
def get_patients():
    """Get patients list"""
    # Check permission
    permission_check = check_api_permission('patient_read')
    if permission_check:
        return permission_check
    
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    search = request.args.get('search', '')
    
    # Build query
    query = Patient.query.filter_by(active=True)
    
    if search:
        query = query.filter(
            db.or_(
                Patient.first_name.ilike(f'%{search}%'),
                Patient.last_name.ilike(f'%{search}%'),
                Patient.mrn.ilike(f'%{search}%'),
                Patient.national_id.ilike(f'%{search}%')
            )
        )
    
    # Paginate results
    patients = query.order_by(Patient.last_name, Patient.first_name)\
                   .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'patients': [p.to_dict() for p in patients.items],
        'total': patients.total,
        'pages': patients.pages,
        'current_page': patients.page,
        'per_page': patients.per_page
    })

@api_bp.route('/patients/<int:patient_id>', methods=['GET'])
@jwt_required()
def get_patient(patient_id):
    """Get patient detail"""
    # Check permission
    permission_check = check_api_permission('patient_read')
    if permission_check:
        return permission_check
    
    patient = Patient.query.get_or_404(patient_id)
    
    if not patient.active:
        return jsonify({'error': 'Patient not found'}), 404
    
    return jsonify(patient.to_dict())

@api_bp.route('/patients', methods=['POST'])
@jwt_required()
def create_patient():
    """Create new patient"""
    # Check permission
    permission_check = check_api_permission('patient_create')
    if permission_check:
        return permission_check
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        # Generate MRN
        mrn = Patient.generate_mrn()
        
        # Create patient
        patient = Patient(
            mrn=mrn,
            national_id=data.get('national_id'),
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            middle_name=data.get('middle_name'),
            dob=datetime.strptime(data.get('dob'), '%Y-%m-%d').date() if data.get('dob') else None,
            sex=data.get('sex'),
            phone=data.get('phone'),
            email=data.get('email'),
            address=data.get('address'),
            city=data.get('city'),
            state=data.get('state'),
            postal_code=data.get('postal_code'),
            country=data.get('country', 'Country'),
            emergency_contact_name=data.get('emergency_contact_name'),
            emergency_contact_phone=data.get('emergency_contact_phone'),
            emergency_contact_relationship=data.get('emergency_contact_relationship'),
            blood_type=data.get('blood_type'),
            allergies=data.get('allergies'),
            chronic_conditions=data.get('chronic_conditions')
        )
        
        db.session.add(patient)
        db.session.commit()
        
        audit_log('patient_create', 'Patient', patient.id, 
                 after_data=patient.to_dict())
        
        return jsonify(patient.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api_bp.route('/patients/<int:patient_id>', methods=['PUT'])
@jwt_required()
def update_patient(patient_id):
    """Update patient"""
    # Check permission
    permission_check = check_api_permission('patient_update')
    if permission_check:
        return permission_check
    
    patient = Patient.query.get_or_404(patient_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        before_data = patient.to_dict()
        
        # Update fields
        if 'national_id' in data:
            patient.national_id = data['national_id']
        if 'first_name' in data:
            patient.first_name = data['first_name']
        if 'last_name' in data:
            patient.last_name = data['last_name']
        if 'middle_name' in data:
            patient.middle_name = data['middle_name']
        if 'dob' in data:
            patient.dob = datetime.strptime(data['dob'], '%Y-%m-%d').date()
        if 'sex' in data:
            patient.sex = data['sex']
        if 'phone' in data:
            patient.phone = data['phone']
        if 'email' in data:
            patient.email = data['email']
        if 'address' in data:
            patient.address = data['address']
        if 'city' in data:
            patient.city = data['city']
        if 'state' in data:
            patient.state = data['state']
        if 'postal_code' in data:
            patient.postal_code = data['postal_code']
        if 'country' in data:
            patient.country = data['country']
        if 'emergency_contact_name' in data:
            patient.emergency_contact_name = data['emergency_contact_name']
        if 'emergency_contact_phone' in data:
            patient.emergency_contact_phone = data['emergency_contact_phone']
        if 'emergency_contact_relationship' in data:
            patient.emergency_contact_relationship = data['emergency_contact_relationship']
        if 'blood_type' in data:
            patient.blood_type = data['blood_type']
        if 'allergies' in data:
            patient.allergies = data['allergies']
        if 'chronic_conditions' in data:
            patient.chronic_conditions = data['chronic_conditions']
        
        db.session.commit()
        
        audit_log('patient_update', 'Patient', patient.id, 
                 before_data=before_data, after_data=patient.to_dict())
        
        return jsonify(patient.to_dict())
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# Visit endpoints
@api_bp.route('/visits', methods=['GET'])
@jwt_required()
def get_visits():
    """Get visits list"""
    # Check permission
    permission_check = check_api_permission('visit_read')
    if permission_check:
        return permission_check
    
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    patient_id = request.args.get('patient_id', type=int)
    status = request.args.get('status')
    date = request.args.get('date')
    
    # Build query
    query = Visit.query
    
    if patient_id:
        query = query.filter_by(patient_id=patient_id)
    if status:
        query = query.filter_by(status=status)
    if date:
        query = query.filter_by(visit_date=datetime.strptime(date, '%Y-%m-%d').date())
    
    # Paginate results
    visits = query.order_by(Visit.visit_date.desc(), Visit.visit_time.desc())\
                 .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'visits': [v.to_dict() for v in visits.items],
        'total': visits.total,
        'pages': visits.pages,
        'current_page': visits.page,
        'per_page': visits.per_page
    })

@api_bp.route('/visits/<int:visit_id>', methods=['GET'])
@jwt_required()
def get_visit(visit_id):
    """Get visit detail"""
    # Check permission
    permission_check = check_api_permission('visit_read')
    if permission_check:
        return permission_check
    
    visit = Visit.query.get_or_404(visit_id)
    return jsonify(visit.to_dict())

@api_bp.route('/visits', methods=['POST'])
@jwt_required()
def create_visit():
    """Create new visit"""
    # Check permission
    permission_check = check_api_permission('visit_create')
    if permission_check:
        return permission_check
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        # Create visit
        visit = Visit(
            patient_id=data.get('patient_id'),
            clinic_id=data.get('clinic_id'),
            visit_date=datetime.strptime(data.get('visit_date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d').date(),
            visit_time=datetime.strptime(data.get('visit_time', datetime.now().strftime('%H:%M')), '%H:%M').time(),
            triage_level=data.get('triage_level'),
            payer_type=data.get('payer_type', 'cash'),
            chief_complaint=data.get('chief_complaint'),
            notes=data.get('notes')
        )
        
        db.session.add(visit)
        db.session.commit()
        
        audit_log('visit_create', 'Visit', visit.id, 
                 after_data=visit.to_dict())
        
        return jsonify(visit.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# Order endpoints
@api_bp.route('/orders', methods=['GET'])
@jwt_required()
def get_orders():
    """Get orders list"""
    # Check permission
    permission_check = check_api_permission('orders_read')
    if permission_check:
        return permission_check
    
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    order_type = request.args.get('type')
    status = request.args.get('status')
    visit_id = request.args.get('visit_id', type=int)
    
    # Build query
    query = Order.query
    
    if order_type:
        query = query.filter_by(type=order_type)
    if status:
        query = query.filter_by(status=status)
    if visit_id:
        query = query.filter_by(visit_id=visit_id)
    
    # Paginate results
    orders = query.order_by(Order.created_at.desc())\
                 .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'orders': [o.to_dict() for o in orders.items],
        'total': orders.total,
        'pages': orders.pages,
        'current_page': orders.page,
        'per_page': orders.per_page
    })

@api_bp.route('/orders/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order(order_id):
    """Get order detail"""
    # Check permission
    permission_check = check_api_permission('orders_read')
    if permission_check:
        return permission_check
    
    order = Order.query.get_or_404(order_id)
    return jsonify(order.to_dict())

# Invoice endpoints
@api_bp.route('/invoices', methods=['GET'])
@jwt_required()
def get_invoices():
    """Get invoices list"""
    # Check permission
    permission_check = check_api_permission('invoice_read')
    if permission_check:
        return permission_check
    
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    status = request.args.get('status')
    patient_id = request.args.get('patient_id', type=int)
    
    # Build query
    query = Invoice.query
    
    if status:
        query = query.filter_by(status=status)
    if patient_id:
        query = query.filter_by(patient_id=patient_id)
    
    # Paginate results
    invoices = query.order_by(Invoice.created_at.desc())\
                   .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'invoices': [i.to_dict() for i in invoices.items],
        'total': invoices.total,
        'pages': invoices.pages,
        'current_page': invoices.page,
        'per_page': invoices.per_page
    })

@api_bp.route('/invoices/<int:invoice_id>', methods=['GET'])
@jwt_required()
def get_invoice(invoice_id):
    """Get invoice detail"""
    # Check permission
    permission_check = check_api_permission('invoice_read')
    if permission_check:
        return permission_check
    
    invoice = Invoice.query.get_or_404(invoice_id)
    return jsonify(invoice.to_dict())

# Error handlers
@api_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@api_bp.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500
