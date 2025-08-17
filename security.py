"""
Security and RBAC (Role-Based Access Control) module
"""
from functools import wraps
from flask import abort, current_app, request, jsonify
from flask_login import current_user
from app.models.staff import Staff
from app.models.roles import Role, Permission, RolePermission

# Define permission codes
PERMISSIONS = {
    # Patient management
    'patient_create': 'Create new patients',
    'patient_read': 'View patient information',
    'patient_update': 'Update patient information',
    'patient_delete': 'Delete patient records',
    
    # Visit management
    'visit_create': 'Create new visits',
    'visit_read': 'View visit information',
    'visit_update': 'Update visit information',
    'visit_close': 'Close visits',
    
    # Clinical operations
    'clinical_notes_create': 'Create clinical notes',
    'clinical_notes_read': 'Read clinical notes',
    'clinical_notes_update': 'Update clinical notes',
    
    # Orders and results
    'orders_create': 'Create lab/radiology orders',
    'orders_read': 'View orders',
    'orders_update': 'Update orders',
    'results_post': 'Post lab/radiology results',
    
    # Pharmacy
    'prescription_create': 'Create prescriptions',
    'prescription_dispense': 'Dispense medications',
    'inventory_manage': 'Manage inventory',
    
    # Billing and finance
    'invoice_create': 'Create invoices',
    'invoice_finalize': 'Finalize invoices',
    'payment_process': 'Process payments',
    'claims_manage': 'Manage insurance claims',
    
    # Referrals
    'referral_create': 'Create referrals',
    'referral_manage': 'Manage referrals',
    
    # HR
    'staff_manage': 'Manage staff',
    'schedule_manage': 'Manage schedules',
    
    # Helpdesk
    'ticket_create': 'Create helpdesk tickets',
    'ticket_assign': 'Assign tickets',
    'ticket_resolve': 'Resolve tickets',
    
    # Quality
    'incident_report': 'Report quality incidents',
    'incident_manage': 'Manage quality incidents',
    'audit_conduct': 'Conduct audits',
    
    # Maintenance
    'workorder_create': 'Create work orders',
    'workorder_manage': 'Manage work orders',
    'asset_manage': 'Manage assets',
    
    # Administration
    'reports_view': 'View reports',
    'settings_manage': 'Manage system settings',
    'user_manage': 'Manage users and roles',
}

# Role definitions with permissions
ROLE_PERMISSIONS = {
    'registration': [
        'patient_create', 'patient_read', 'patient_update',
        'visit_create', 'visit_read', 'visit_update',
        'appointment_create', 'appointment_read'
    ],
    'physician': [
        'patient_read', 'visit_read', 'visit_update', 'visit_close',
        'clinical_notes_create', 'clinical_notes_read', 'clinical_notes_update',
        'orders_create', 'orders_read', 'orders_update',
        'prescription_create', 'prescription_read',
        'referral_create'
    ],
    'dentist': [
        'patient_read', 'visit_read', 'visit_update', 'visit_close',
        'clinical_notes_create', 'clinical_notes_read', 'clinical_notes_update',
        'orders_create', 'orders_read', 'orders_update',
        'prescription_create', 'prescription_read'
    ],
    'lab': [
        'orders_read', 'results_post', 'inventory_manage'
    ],
    'radiology': [
        'orders_read', 'results_post'
    ],
    'pharmacy': [
        'prescription_read', 'prescription_dispense', 'inventory_manage'
    ],
    'cashier': [
        'invoice_read', 'payment_process', 'patient_read'
    ],
    'referral': [
        'referral_create', 'referral_manage', 'patient_read'
    ],
    'finance': [
        'invoice_create', 'invoice_finalize', 'payment_process',
        'claims_manage', 'reports_view'
    ],
    'hr': [
        'staff_manage', 'schedule_manage', 'reports_view'
    ],
    'helpdesk': [
        'ticket_create', 'ticket_assign', 'ticket_resolve'
    ],
    'quality': [
        'incident_report', 'incident_manage', 'audit_conduct',
        'reports_view'
    ],
    'satisfaction': [
        'reports_view'
    ],
    'medical_admin': [
        'reports_view', 'settings_manage', 'user_manage'
    ],
    'maintenance': [
        'workorder_create', 'workorder_manage', 'asset_manage'
    ],
    'facility_head': [
        'patient_read', 'visit_read', 'orders_read', 'results_read',
        'prescription_read', 'invoice_read', 'referral_read',
        'ticket_read', 'incident_read', 'workorder_read',
        'reports_view', 'settings_manage'
    ],
    'superadmin': [
        # All permissions
        *PERMISSIONS.keys()
    ]
}

def require_permission(permission_code):
    """Decorator to require a specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            if not has_permission(current_user, permission_code):
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_role(role_name):
    """Decorator to require a specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            if not has_role(current_user, role_name):
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_any_role(*role_names):
    """Decorator to require any of the specified roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            if not any(has_role(current_user, role) for role in role_names):
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def has_permission(user, permission_code):
    """Check if user has a specific permission"""
    if not user or not user.active:
        return False
    
    # Superadmin has all permissions
    if has_role(user, 'superadmin'):
        return True
    
    # Facility head has read permissions
    if has_role(user, 'facility_head') and permission_code.endswith('_read'):
        return True
    
    # Check user's role permissions
    if user.role and user.role.permissions:
        return any(p.code == permission_code for p in user.role.permissions)
    
    return False

def has_role(user, role_name):
    """Check if user has a specific role"""
    if not user or not user.active:
        return False
    
    return user.role and user.role.name == role_name

def get_user_permissions(user):
    """Get all permissions for a user"""
    if not user or not user.active or not user.role:
        return []
    
    return [p.code for p in user.role.permissions]

def check_api_permission(permission_code):
    """Check permission for API endpoints"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required'}), 401
    
    if not has_permission(current_user, permission_code):
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    return None

def audit_log(action, entity, entity_id, before_data=None, after_data=None):
    """Log audit trail for important actions"""
    from app.models.common import AuditLog
    
    if current_user.is_authenticated:
        audit_entry = AuditLog(
            actor_id=current_user.id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            before_json=before_data,
            after_json=after_data
        )
        
        try:
            from app import db
            db.session.add(audit_entry)
            db.session.commit()
        except Exception as e:
            current_app.logger.error(f"Failed to log audit trail: {e}")
            db.session.rollback()

def get_department_staff(department_id):
    """Get all active staff in a department"""
    return Staff.query.filter_by(
        department_id=department_id,
        active=True
    ).all()

def can_access_patient(user, patient_id):
    """Check if user can access a specific patient"""
    # Superadmin and facility head can access all patients
    if has_role(user, 'superadmin') or has_role(user, 'facility_head'):
        return True
    
    # Registration staff can access all patients
    if has_role(user, 'registration'):
        return True
    
    # Clinical staff can access patients they've seen
    if has_role(user, 'physician') or has_role(user, 'dentist'):
        from app.models.visits import Visit
        from app.models.clinical_notes import ClinicalNote
        
        # Check if user has created clinical notes for this patient
        return ClinicalNote.query.filter_by(
            provider_id=user.id,
            visit_id=Visit.query.filter_by(patient_id=patient_id).subquery()
        ).first() is not None
    
    return False

def can_access_visit(user, visit_id):
    """Check if user can access a specific visit"""
    # Superadmin and facility head can access all visits
    if has_role(user, 'superadmin') or has_role(user, 'facility_head'):
        return True
    
    # Registration staff can access all visits
    if has_role(user, 'registration'):
        return True
    
    # Clinical staff can access visits they're involved with
    if has_role(user, 'physician') or has_role(user, 'dentist'):
        from app.models.clinical_notes import ClinicalNote
        return ClinicalNote.query.filter_by(
            provider_id=user.id,
            visit_id=visit_id
        ).first() is not None
    
    return False
