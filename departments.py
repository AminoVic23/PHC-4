"""
Department model for organizational structure
"""
from datetime import datetime
from app import db

class Department(db.Model):
    """Department model for organizational structure"""
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    type = db.Column(db.String(50), nullable=False, index=True)  # clinical, support, administrative, emergency
    description = db.Column(db.Text)
    location = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    facility_id = db.Column(db.Integer, db.ForeignKey('facilities.id'), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    facility = db.relationship('Facility', back_populates='departments')
    staff = db.relationship('Staff', backref='department_info', lazy='dynamic')
    visits = db.relationship('Visit', backref='clinic', lazy='dynamic')
    appointments = db.relationship('Appointment', backref='clinic_dept', lazy='dynamic')
    price_list_items = db.relationship('PriceList', backref='department_info', lazy='dynamic')
    
    def __init__(self, **kwargs):
        super(Department, self).__init__(**kwargs)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'description': self.description,
            'location': self.location,
            'phone': self.phone,
            'email': self.email,
            'active': self.active,
            'staff_count': self.staff.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Department {self.name} ({self.type})>'
    
    @classmethod
    def find_by_name(cls, name):
        """Find department by name"""
        return cls.query.filter_by(name=name).first()
    
    @classmethod
    def get_active_departments(cls):
        """Get all active departments"""
        return cls.query.filter_by(active=True).all()
    
    @classmethod
    def get_by_type(cls, dept_type):
        """Get departments by type"""
        return cls.query.filter_by(type=dept_type, active=True).all()
    
    @classmethod
    def get_clinical_departments(cls):
        """Get all clinical departments"""
        return cls.get_by_type('clinical')
    
    @classmethod
    def get_support_departments(cls):
        """Get all support departments"""
        return cls.get_by_type('support')
    
    @classmethod
    def get_administrative_departments(cls):
        """Get all administrative departments"""
        return cls.get_by_type('administrative')
