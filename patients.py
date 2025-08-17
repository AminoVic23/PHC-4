"""
Patient model for patient demographic and medical information
"""
from datetime import datetime, timedelta
from app import db

class Patient(db.Model):
    """Patient model for demographic and medical information"""
    __tablename__ = 'patients'
    
    id = db.Column(db.Integer, primary_key=True)
    mrn = db.Column(db.String(20), nullable=False, index=True)  # Medical Record Number
    national_id = db.Column(db.String(20), index=True)
    passport_id = db.Column(db.String(20), index=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    middle_name = db.Column(db.String(50))
    dob = db.Column(db.Date, nullable=False, index=True)
    sex = db.Column(db.String(10), nullable=False, index=True)  # M, F, Other
    nationality = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), index=True)
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    postal_code = db.Column(db.String(20))
    country = db.Column(db.String(50), default='Country')
    emergency_contact_name = db.Column(db.String(100))
    emergency_contact_phone = db.Column(db.String(20))
    emergency_contact_relationship = db.Column(db.String(50))
    blood_type = db.Column(db.String(5))  # A+, B-, O+, etc.
    allergies = db.Column(db.Text)
    chronic_conditions = db.Column(db.Text)
    facility_id = db.Column(db.Integer, db.ForeignKey('facilities.id'), nullable=False)
    insurance_id = db.Column(db.Integer, db.ForeignKey('insurance_policies.id'))
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    facility = db.relationship('Facility', back_populates='patients')
    insurance_policy = db.relationship('InsurancePolicy', backref='patient_info')
    visits = db.relationship('Visit', backref='patient', lazy='dynamic')
    appointments = db.relationship('Appointment', backref='patient', lazy='dynamic')
    invoices = db.relationship('Invoice', backref='patient', lazy='dynamic')
    surveys = db.relationship('Survey', backref='patient', lazy='dynamic')
    
    def __init__(self, **kwargs):
        super(Patient, self).__init__(**kwargs)
    
    @property
    def full_name(self):
        """Get patient's full name"""
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self):
        """Calculate patient's age"""
        if self.dob:
            today = datetime.now().date()
            return today.year - self.dob.year - ((today.month, today.day) < (self.dob.month, self.dob.day))
        return None
    
    @property
    def age_group(self):
        """Get patient's age group"""
        age = self.age
        if age is None:
            return 'Unknown'
        elif age < 18:
            return 'Pediatric'
        elif age < 65:
            return 'Adult'
        else:
            return 'Geriatric'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'mrn': self.mrn,
            'national_id': self.national_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'middle_name': self.middle_name,
            'full_name': self.full_name,
            'dob': self.dob.isoformat() if self.dob else None,
            'age': self.age,
            'age_group': self.age_group,
            'sex': self.sex,
            'phone': self.phone,
            'email': self.email,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'postal_code': self.postal_code,
            'country': self.country,
            'emergency_contact_name': self.emergency_contact_name,
            'emergency_contact_phone': self.emergency_contact_phone,
            'emergency_contact_relationship': self.emergency_contact_relationship,
            'blood_type': self.blood_type,
            'allergies': self.allergies,
            'chronic_conditions': self.chronic_conditions,
            'insurance_id': self.insurance_id,
            'active': self.active,
            'visit_count': self.visits.count(),
            'last_visit': self.get_last_visit_date(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def get_last_visit_date(self):
        """Get the date of the patient's last visit"""
        last_visit = self.visits.order_by(Visit.visit_date.desc()).first()
        return last_visit.visit_date.isoformat() if last_visit else None
    
    def get_visit_history(self, limit=10):
        """Get patient's recent visit history"""
        return self.visits.order_by(Visit.visit_date.desc()).limit(limit).all()
    
    def get_active_insurance(self):
        """Get patient's active insurance policy"""
        if self.insurance_policy and self.insurance_policy.is_active():
            return self.insurance_policy
        return None
    
    def __repr__(self):
        return f'<Patient {self.mrn}: {self.full_name}>'
    
    @classmethod
    def find_by_mrn(cls, mrn):
        """Find patient by Medical Record Number"""
        return cls.query.filter_by(mrn=mrn).first()
    
    @classmethod
    def find_by_national_id(cls, national_id):
        """Find patient by National ID"""
        return cls.query.filter_by(national_id=national_id).first()
    
    @classmethod
    def search_patients(cls, query, limit=20, facility_id=None):
        """Search patients by name, MRN, or national ID"""
        search_term = f"%{query}%"
        query_filter = cls.query.filter(
            db.or_(
                cls.first_name.ilike(search_term),
                cls.last_name.ilike(search_term),
                cls.mrn.ilike(search_term),
                cls.national_id.ilike(search_term),
                cls.passport_id.ilike(search_term)
            ),
            cls.active == True
        )
        
        if facility_id:
            query_filter = query_filter.filter(cls.facility_id == facility_id)
            
        return query_filter.limit(limit).all()
    
    @classmethod
    def get_active_patients(cls):
        """Get all active patients"""
        return cls.query.filter_by(active=True).all()
    
    @classmethod
    def get_patients_by_age_group(cls, age_group):
        """Get patients by age group"""
        if age_group == 'Pediatric':
            return cls.query.filter(
                cls.dob >= datetime.now().date() - timedelta(days=18*365),
                cls.active == True
            ).all()
        elif age_group == 'Adult':
            return cls.query.filter(
                cls.dob < datetime.now().date() - timedelta(days=18*365),
                cls.dob >= datetime.now().date() - timedelta(days=65*365),
                cls.active == True
            ).all()
        elif age_group == 'Geriatric':
            return cls.query.filter(
                cls.dob < datetime.now().date() - timedelta(days=65*365),
                cls.active == True
            ).all()
        return []
    
    @classmethod
    def generate_mrn(cls, facility_code):
        """Generate a unique Medical Record Number with facility code prefix"""
        import random
        import string
        
        while True:
            # Generate MRN in format: FACILITY-YYYY-XXXXX (facility + year + 5 random digits)
            year = datetime.now().year
            digits = ''.join(random.choices(string.digits, k=5))
            mrn = f"{facility_code}-{year}-{digits}"
            
            # Check if MRN already exists
            if not cls.find_by_mrn(mrn):
                return mrn
