"""
Session management utilities for multi-facility access control
"""
from flask import session, g
from flask_login import current_user
from app.models import Facility, StaffFacility

def set_current_facility(facility_id):
    """Set the current facility for the user session"""
    if not current_user.is_authenticated:
        return False
    
    # Check if user has access to this facility
    if not current_user.has_facility_access(facility_id):
        return False
    
    session['current_facility_id'] = facility_id
    return True

def get_current_facility():
    """Get the current facility for the user session"""
    if not current_user.is_authenticated:
        return None
    
    facility_id = session.get('current_facility_id')
    if not facility_id:
        return None
    
    # Verify user still has access to this facility
    if not current_user.has_facility_access(facility_id):
        session.pop('current_facility_id', None)
        return None
    
    return Facility.query.get(facility_id)

def get_current_facility_id():
    """Get the current facility ID for the user session"""
    if not current_user.is_authenticated:
        return None
    
    facility_id = session.get('current_facility_id')
    if not facility_id:
        return None
    
    # Verify user still has access to this facility
    if not current_user.has_facility_access(facility_id):
        session.pop('current_facility_id', None)
        return None
    
    return facility_id

def get_user_facilities():
    """Get all facilities the current user has access to"""
    if not current_user.is_authenticated:
        return []
    
    return current_user.get_accessible_facilities()

def require_facility_access():
    """Decorator to require facility access for routes"""
    def decorator(f):
        def decorated_function(*args, **kwargs):
            if not get_current_facility():
                # Redirect to facility selection page
                from flask import redirect, url_for, flash
                flash('Please select a facility to continue', 'warning')
                return redirect(url_for('facility.select'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def filter_by_facility(query, facility_id=None):
    """Filter a query by facility if facility_id is provided"""
    if facility_id:
        # Check if the model has a facility_id column
        if hasattr(query.column_descriptions[0]['type'], 'facility_id'):
            return query.filter(query.column_descriptions[0]['type'].facility_id == facility_id)
    return query
