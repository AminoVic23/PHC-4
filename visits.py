"""
Visit and Appointment models for patient encounters and scheduling
"""
from datetime import datetime, timedelta
from app import db

class Visit(db.Model):
    """Visit model for patient encounters"""
    __tablename__ = 'visits'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)
    visit_no = db.Column(db.String(20), nullable=False, index=True)
    visit_date = db.Column(db.Date, nullable=False, index=True)
    visit_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='open', index=True)  # open, closed, referred
    triage_level = db.Column(db.String(10), index=True)  # 1-5, 1 being most urgent
    clinic_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    facility_id = db.Column(db.Integer, db.ForeignKey('facilities.id'), nullable=False)
    referral_id = db.Column(db.Integer, db.ForeignKey('referrals.id'))
    payer_type = db.Column(db.String(20), default='cash', index=True)  # cash, insurance
    chief_complaint = db.Column(db.Text)
    vital_signs = db.Column(db.JSON)  # Store vital signs as JSON
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = db.Column(db.DateTime)
    
    # Relationships
    patient = db.relationship('Patient', backref='visits')
    clinic = db.relationship('Department', backref='visits')
    facility = db.relationship('Facility', back_populates='visits')
    referral = db.relationship('Referral', backref='visits')
    clinical_notes = db.relationship('ClinicalNote', backref='visit', lazy='dynamic')
    orders = db.relationship('Order', backref='visit', lazy='dynamic')
    prescriptions = db.relationship('Prescription', backref='visit', lazy='dynamic')
    invoices = db.relationship('Invoice', backref='visit', lazy='dynamic')
    
    def __init__(self, **kwargs):
        super(Visit, self).__init__(**kwargs)
        if not self.visit_no:
            self.visit_no = self.generate_visit_no()
    
    @property
    def is_open(self):
        """Check if visit is still open"""
        return self.status == 'open'
    
    @property
    def duration(self):
        """Calculate visit duration if closed"""
        if self.closed_at and self.created_at:
            return self.closed_at - self.created_at
        return None
    
    @property
    def wait_time(self):
        """Calculate wait time from appointment to first clinical note"""
        if not self.appointments:
            return None
        
        appointment = self.appointments[0]
        first_note = self.clinical_notes.order_by(ClinicalNote.created_at).first()
        
        if appointment and first_note:
            return first_note.created_at - appointment.start_dt
        return None
    
    def close_visit(self):
        """Close the visit"""
        self.status = 'closed'
        self.closed_at = datetime.utcnow()
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'patient_name': self.patient.full_name if self.patient else None,
            'visit_no': self.visit_no,
            'visit_date': self.visit_date.isoformat() if self.visit_date else None,
            'visit_time': self.visit_time.isoformat() if self.visit_time else None,
            'status': self.status,
            'triage_level': self.triage_level,
            'clinic_id': self.clinic_id,
            'clinic_name': self.clinic.name if self.clinic else None,
            'referral_id': self.referral_id,
            'payer_type': self.payer_type,
            'chief_complaint': self.chief_complaint,
            'vital_signs': self.vital_signs,
            'notes': self.notes,
            'is_open': self.is_open,
            'duration': str(self.duration) if self.duration else None,
            'wait_time': str(self.wait_time) if self.wait_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None
        }
    
    def __repr__(self):
        return f'<Visit {self.visit_no}: {self.patient.full_name if self.patient else "Unknown"} ({self.status})>'
    
    @classmethod
    def generate_visit_no(cls):
        """Generate a unique visit number"""
        import random
        import string
        
        while True:
            # Generate visit number in format: V-YYYYMMDD-XXXXX
            date_str = datetime.now().strftime('%Y%m%d')
            digits = ''.join(random.choices(string.digits, k=5))
            visit_no = f"V-{date_str}-{digits}"
            
            # Check if visit number already exists
            if not cls.query.filter_by(visit_no=visit_no).first():
                return visit_no
    
    @classmethod
    def get_open_visits(cls, clinic_id=None):
        """Get all open visits, optionally filtered by clinic"""
        query = cls.query.filter_by(status='open')
        if clinic_id:
            query = query.filter_by(clinic_id=clinic_id)
        return query.order_by(cls.visit_date.desc(), cls.visit_time.desc()).all()
    
    @classmethod
    def get_visits_by_date(cls, date, clinic_id=None):
        """Get visits for a specific date"""
        query = cls.query.filter_by(visit_date=date)
        if clinic_id:
            query = query.filter_by(clinic_id=clinic_id)
        return query.order_by(cls.visit_time).all()
    
    @classmethod
    def get_visits_by_patient(cls, patient_id, limit=10):
        """Get recent visits for a patient"""
        return cls.query.filter_by(patient_id=patient_id)\
                       .order_by(cls.visit_date.desc())\
                       .limit(limit).all()

class Appointment(db.Model):
    """Appointment model for scheduled patient visits"""
    __tablename__ = 'appointments'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    start_dt = db.Column(db.DateTime, nullable=False, index=True)
    end_dt = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='scheduled', nullable=False, index=True)  # scheduled, checked_in, no_show, completed, cancelled
    appointment_type = db.Column(db.String(50))  # consultation, follow_up, procedure, etc.
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = db.relationship('Patient', backref='appointments')
    clinic = db.relationship('Department', backref='appointments')
    provider = db.relationship('Staff', backref='appointments')
    
    def __init__(self, **kwargs):
        super(Appointment, self).__init__(**kwargs)
        # Set end time to 30 minutes after start if not provided
        if self.start_dt and not self.end_dt:
            self.end_dt = self.start_dt + timedelta(minutes=30)
    
    @property
    def is_today(self):
        """Check if appointment is today"""
        return self.start_dt.date() == datetime.now().date()
    
    @property
    def is_overdue(self):
        """Check if appointment is overdue"""
        return self.start_dt < datetime.now() and self.status == 'scheduled'
    
    @property
    def duration(self):
        """Calculate appointment duration"""
        if self.start_dt and self.end_dt:
            return self.end_dt - self.start_dt
        return None
    
    def check_in(self):
        """Mark appointment as checked in"""
        self.status = 'checked_in'
    
    def complete(self):
        """Mark appointment as completed"""
        self.status = 'completed'
    
    def cancel(self):
        """Cancel appointment"""
        self.status = 'cancelled'
    
    def no_show(self):
        """Mark appointment as no-show"""
        self.status = 'no_show'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'patient_name': self.patient.full_name if self.patient else None,
            'clinic_id': self.clinic_id,
            'clinic_name': self.clinic.name if self.clinic else None,
            'provider_id': self.provider_id,
            'provider_name': self.provider.name if self.provider else None,
            'start_dt': self.start_dt.isoformat() if self.start_dt else None,
            'end_dt': self.end_dt.isoformat() if self.end_dt else None,
            'status': self.status,
            'appointment_type': self.appointment_type,
            'notes': self.notes,
            'is_today': self.is_today,
            'is_overdue': self.is_overdue,
            'duration': str(self.duration) if self.duration else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Appointment {self.id}: {self.patient.full_name if self.patient else "Unknown"} at {self.start_dt}>'
    
    @classmethod
    def get_today_appointments(cls, clinic_id=None, provider_id=None):
        """Get today's appointments"""
        query = cls.query.filter(
            db.func.date(cls.start_dt) == datetime.now().date(),
            cls.status.in_(['scheduled', 'checked_in'])
        )
        
        if clinic_id:
            query = query.filter_by(clinic_id=clinic_id)
        if provider_id:
            query = query.filter_by(provider_id=provider_id)
        
        return query.order_by(cls.start_dt).all()
    
    @classmethod
    def get_provider_appointments(cls, provider_id, date=None):
        """Get appointments for a specific provider"""
        query = cls.query.filter_by(provider_id=provider_id)
        
        if date:
            query = query.filter(db.func.date(cls.start_dt) == date)
        
        return query.order_by(cls.start_dt).all()
    
    @classmethod
    def get_patient_appointments(cls, patient_id, limit=10):
        """Get recent appointments for a patient"""
        return cls.query.filter_by(patient_id=patient_id)\
                       .order_by(cls.start_dt.desc())\
                       .limit(limit).all()
    
    @classmethod
    def get_no_shows(cls, start_date=None, end_date=None):
        """Get no-show appointments"""
        query = cls.query.filter_by(status='no_show')
        
        if start_date:
            query = query.filter(cls.start_dt >= start_date)
        if end_date:
            query = query.filter(cls.start_dt <= end_date)
        
        return query.order_by(cls.start_dt.desc()).all()
