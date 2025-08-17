"""
Staff model for user authentication and role management
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class Staff(db.Model, UserMixin):
    """Staff/User model for authentication and role management"""
    __tablename__ = 'staff'
    
    id = db.Column(db.Integer, primary_key=True)
    emp_no = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    hashed_pw = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    department = db.relationship('Department', backref='staff')
    role = db.relationship('Role', backref='staff')
    
    # Clinical relationships
    clinical_notes = db.relationship('ClinicalNote', backref='provider', lazy='dynamic')
    orders = db.relationship('Order', backref='ordered_by', lazy='dynamic')
    prescriptions = db.relationship('Prescription', backref='prescriber', lazy='dynamic')
    payments = db.relationship('Payment', backref='cashier', lazy='dynamic')
    
    # HR relationships
    shifts = db.relationship('Shift', backref='staff_member', lazy='dynamic')
    leave_requests = db.relationship('LeaveRequest', backref='staff_member', lazy='dynamic')
    
    # Helpdesk relationships
    opened_tickets = db.relationship('Ticket', foreign_keys='Ticket.opened_by_staff_id', backref='opened_by', lazy='dynamic')
    assigned_tickets = db.relationship('Ticket', foreign_keys='Ticket.assigned_to', backref='assigned_to_staff', lazy='dynamic')
    
    # Quality relationships
    quality_incidents = db.relationship('QualityIncident', backref='reported_by', lazy='dynamic')
    
    # Maintenance relationships
    opened_work_orders = db.relationship('WorkOrder', foreign_keys='WorkOrder.opened_by_id', backref='opened_by', lazy='dynamic')
    assigned_work_orders = db.relationship('WorkOrder', foreign_keys='WorkOrder.assigned_to', backref='assigned_to_staff', lazy='dynamic')
    
    # Audit relationships
    audit_logs = db.relationship('AuditLog', backref='actor', lazy='dynamic')
    
    # Multi-facility relationships
    facility_access = db.relationship('StaffFacility', backref='staff', lazy='dynamic')
    
    def __init__(self, **kwargs):
        super(Staff, self).__init__(**kwargs)
        if self.hashed_pw is None and 'password' in kwargs:
            self.set_password(kwargs['password'])
    
    def set_password(self, password):
        """Set password hash"""
        self.hashed_pw = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.hashed_pw, password)
    
    def get_id(self):
        """Return user ID for Flask-Login"""
        return str(self.id)
    
    def is_active(self):
        """Check if user is active"""
        return self.active
    
    def has_permission(self, permission_code):
        """Check if user has a specific permission"""
        from app.security import has_permission
        return has_permission(self, permission_code)
    
    def has_role(self, role_name):
        """Check if user has a specific role"""
        from app.security import has_role
        return has_role(self, role_name)
    
    def get_permissions(self):
        """Get all permissions for this user"""
        from app.security import get_user_permissions
        return get_user_permissions(self)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'emp_no': self.emp_no,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'department_id': self.department_id,
            'department_name': self.department.name if self.department else None,
            'role_id': self.role_id,
            'role_name': self.role.name if self.role else None,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'permissions': self.get_permissions()
        }
    
    def __repr__(self):
        return f'<Staff {self.emp_no}: {self.name}>'
    
    @classmethod
    def find_by_email(cls, email):
        """Find staff member by email"""
        return cls.query.filter_by(email=email).first()
    
    @classmethod
    def find_by_emp_no(cls, emp_no):
        """Find staff member by employee number"""
        return cls.query.filter_by(emp_no=emp_no).first()
    
    @classmethod
    def get_active_staff(cls):
        """Get all active staff members"""
        return cls.query.filter_by(active=True).all()
    
    @classmethod
    def get_department_staff(cls, department_id):
        """Get all active staff in a department"""
        return cls.query.filter_by(
            department_id=department_id,
            active=True
        ).all()
    
    @classmethod
    def get_by_role(cls, role_name):
        """Get all staff with a specific role"""
        return cls.query.join(Role).filter(
            Role.name == role_name,
            cls.active == True
        ).all()
    
    @classmethod
    def get_facility_staff(cls, facility_id):
        """Get all staff with access to a specific facility"""
        from app.models import StaffFacility
        return cls.query.join(StaffFacility).filter(
            StaffFacility.facility_id == facility_id,
            StaffFacility.can_access == True,
            StaffFacility.is_active == True,
            cls.active == True
        ).all()
    
    def get_accessible_facilities(self):
        """Get all facilities this staff member can access"""
        from app.models import StaffFacility, Facility
        return Facility.query.join(StaffFacility).filter(
            StaffFacility.staff_id == self.id,
            StaffFacility.can_access == True,
            StaffFacility.is_active == True,
            Facility.is_active == True
        ).all()
    
    def has_facility_access(self, facility_id):
        """Check if staff has access to a specific facility"""
        from app.models import StaffFacility
        return StaffFacility.query.filter(
            StaffFacility.staff_id == self.id,
            StaffFacility.facility_id == facility_id,
            StaffFacility.can_access == True,
            StaffFacility.is_active == True
        ).first() is not None
