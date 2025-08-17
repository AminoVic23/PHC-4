"""
Referral model for patient referrals
"""
from datetime import datetime, timedelta
from app import db

class Referral(db.Model):
    """Referral model for patient referrals to other facilities or specialists"""
    __tablename__ = 'referrals'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), index=True)
    referring_provider_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False, index=True)
    referral_no = db.Column(db.String(20), unique=True, nullable=False, index=True)
    referral_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    referral_type = db.Column(db.String(50), nullable=False, index=True)  # internal, external, specialist
    specialty = db.Column(db.String(100), nullable=False, index=True)  # cardiology, orthopedics, etc.
    facility_name = db.Column(db.String(200))
    provider_name = db.Column(db.String(200))
    contact_info = db.Column(db.Text)
    reason = db.Column(db.Text, nullable=False)
    clinical_summary = db.Column(db.Text)
    urgency = db.Column(db.String(20), default='routine', nullable=False, index=True)  # routine, urgent, emergency
    status = db.Column(db.String(20), default='pending', nullable=False, index=True)  # pending, accepted, completed, cancelled
    appointment_date = db.Column(db.Date)
    appointment_time = db.Column(db.Time)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    # Relationships
    patient = db.relationship('Patient', backref='referrals')
    visit = db.relationship('Visit', backref='referrals')
    referring_provider = db.relationship('Staff', backref='referrals')

    def __init__(self, **kwargs):
        super(Referral, self).__init__(**kwargs)
        if not self.referral_no:
            self.referral_no = self.generate_referral_no()

    @property
    def is_pending(self):
        """Check if referral is pending"""
        return self.status == 'pending'

    @property
    def is_accepted(self):
        """Check if referral is accepted"""
        return self.status == 'accepted'

    @property
    def is_completed(self):
        """Check if referral is completed"""
        return self.status == 'completed'

    @property
    def is_cancelled(self):
        """Check if referral is cancelled"""
        return self.status == 'cancelled'

    @property
    def is_urgent(self):
        """Check if referral is urgent or emergency"""
        return self.urgency in ['urgent', 'emergency']

    @property
    def is_overdue(self):
        """Check if referral is overdue (pending for more than 30 days)"""
        if self.status != 'pending':
            return False
        return self.referral_date < (datetime.now().date() - timedelta(days=30))

    def accept_referral(self, appointment_date=None, appointment_time=None):
        """Accept the referral"""
        self.status = 'accepted'
        if appointment_date:
            self.appointment_date = appointment_date
        if appointment_time:
            self.appointment_time = appointment_time

    def complete_referral(self):
        """Mark referral as completed"""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()

    def cancel_referral(self):
        """Cancel the referral"""
        self.status = 'cancelled'

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'patient_name': self.patient.full_name if self.patient else None,
            'visit_id': self.visit_id,
            'visit_no': self.visit.visit_no if self.visit else None,
            'referring_provider_id': self.referring_provider_id,
            'referring_provider_name': self.referring_provider.name if self.referring_provider else None,
            'referral_no': self.referral_no,
            'referral_date': self.referral_date.isoformat() if self.referral_date else None,
            'referral_type': self.referral_type,
            'specialty': self.specialty,
            'facility_name': self.facility_name,
            'provider_name': self.provider_name,
            'contact_info': self.contact_info,
            'reason': self.reason,
            'clinical_summary': self.clinical_summary,
            'urgency': self.urgency,
            'status': self.status,
            'appointment_date': self.appointment_date.isoformat() if self.appointment_date else None,
            'appointment_time': self.appointment_time.isoformat() if self.appointment_time else None,
            'notes': self.notes,
            'is_pending': self.is_pending,
            'is_accepted': self.is_accepted,
            'is_completed': self.is_completed,
            'is_cancelled': self.is_cancelled,
            'is_urgent': self.is_urgent,
            'is_overdue': self.is_overdue,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

    def __repr__(self):
        return f'<Referral {self.referral_no}: {self.specialty} ({self.status})>'

    @classmethod
    def generate_referral_no(cls):
        """Generate a unique referral number"""
        import random
        import string

        while True:
            # Generate referral number in format: REF-YYYYMMDD-XXXXX
            date_str = datetime.now().strftime('%Y%m%d')
            digits = ''.join(random.choices(string.digits, k=5))
            referral_no = f"REF-{date_str}-{digits}"

            # Check if referral number already exists
            if not cls.query.filter_by(referral_no=referral_no).first():
                return referral_no

    @classmethod
    def get_pending_referrals(cls):
        """Get all pending referrals"""
        return cls.query.filter_by(status='pending').order_by(cls.referral_date).all()

    @classmethod
    def get_urgent_referrals(cls):
        """Get urgent referrals"""
        return cls.query.filter(
            cls.urgency.in_(['urgent', 'emergency']),
            cls.status.in_(['pending', 'accepted'])
        ).order_by(cls.referral_date).all()

    @classmethod
    def get_overdue_referrals(cls):
        """Get overdue referrals"""
        cutoff_date = datetime.now().date() - timedelta(days=30)
        return cls.query.filter(
            cls.status == 'pending',
            cls.referral_date < cutoff_date
        ).order_by(cls.referral_date).all()

    @classmethod
    def get_patient_referrals(cls, patient_id, limit=20):
        """Get recent referrals for a patient"""
        return cls.query.filter_by(patient_id=patient_id)\
                       .order_by(cls.referral_date.desc())\
                       .limit(limit).all()

    @classmethod
    def get_provider_referrals(cls, provider_id, limit=20):
        """Get recent referrals by a provider"""
        return cls.query.filter_by(referring_provider_id=provider_id)\
                       .order_by(cls.referral_date.desc())\
                       .limit(limit).all()

    @classmethod
    def get_referrals_by_specialty(cls, specialty, limit=20):
        """Get referrals by specialty"""
        return cls.query.filter_by(specialty=specialty)\
                       .order_by(cls.referral_date.desc())\
                       .limit(limit).all()

    @classmethod
    def get_referrals_by_type(cls, referral_type, limit=20):
        """Get referrals by type"""
        return cls.query.filter_by(referral_type=referral_type)\
                       .order_by(cls.referral_date.desc())\
                       .limit(limit).all()
