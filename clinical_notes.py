"""
Clinical Note model for SOAP notes and clinical documentation
"""
from datetime import datetime
from app import db

class ClinicalNote(db.Model):
    """Clinical Note model for SOAP notes and clinical documentation"""
    __tablename__ = 'clinical_notes'
    
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=False, index=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False, index=True)
    note_type = db.Column(db.String(20), nullable=False, index=True)  # SOAP, Dental, Progress, etc.
    soap_json = db.Column(db.JSON)  # Store SOAP components as JSON
    diagnosis_icd = db.Column(db.String(20))  # ICD-10 diagnosis codes
    diagnosis_text = db.Column(db.Text)
    plan = db.Column(db.Text)
    follow_up_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    visit = db.relationship('Visit', backref='clinical_notes')
    provider = db.relationship('Staff', backref='clinical_notes')
    
    def __init__(self, **kwargs):
        super(ClinicalNote, self).__init__(**kwargs)
        if not self.soap_json:
            self.soap_json = {
                'subjective': '',
                'objective': '',
                'assessment': '',
                'plan': ''
            }
    
    @property
    def subjective(self):
        """Get subjective component from SOAP"""
        return self.soap_json.get('subjective', '') if self.soap_json else ''
    
    @property
    def objective(self):
        """Get objective component from SOAP"""
        return self.soap_json.get('objective', '') if self.soap_json else ''
    
    @property
    def assessment(self):
        """Get assessment component from SOAP"""
        return self.soap_json.get('assessment', '') if self.soap_json else ''
    
    @property
    def plan_component(self):
        """Get plan component from SOAP"""
        return self.soap_json.get('plan', '') if self.soap_json else ''
    
    def update_soap(self, subjective=None, objective=None, assessment=None, plan=None):
        """Update SOAP components"""
        if not self.soap_json:
            self.soap_json = {}
        
        if subjective is not None:
            self.soap_json['subjective'] = subjective
        if objective is not None:
            self.soap_json['objective'] = objective
        if assessment is not None:
            self.soap_json['assessment'] = assessment
        if plan is not None:
            self.soap_json['plan'] = plan
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'visit_id': self.visit_id,
            'visit_no': self.visit.visit_no if self.visit else None,
            'provider_id': self.provider_id,
            'provider_name': self.provider.name if self.provider else None,
            'note_type': self.note_type,
            'soap_json': self.soap_json,
            'subjective': self.subjective,
            'objective': self.objective,
            'assessment': self.assessment,
            'plan_component': self.plan_component,
            'diagnosis_icd': self.diagnosis_icd,
            'diagnosis_text': self.diagnosis_text,
            'plan': self.plan,
            'follow_up_notes': self.follow_up_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<ClinicalNote {self.id}: {self.note_type} by {self.provider.name if self.provider else "Unknown"}>'
    
    @classmethod
    def get_visit_notes(cls, visit_id):
        """Get all clinical notes for a visit"""
        return cls.query.filter_by(visit_id=visit_id)\
                       .order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_provider_notes(cls, provider_id, limit=20):
        """Get recent clinical notes by a provider"""
        return cls.query.filter_by(provider_id=provider_id)\
                       .order_by(cls.created_at.desc())\
                       .limit(limit).all()
    
    @classmethod
    def get_notes_by_type(cls, note_type, limit=20):
        """Get clinical notes by type"""
        return cls.query.filter_by(note_type=note_type)\
                       .order_by(cls.created_at.desc())\
                       .limit(limit).all()
    
    @classmethod
    def get_notes_by_diagnosis(cls, diagnosis_icd, limit=20):
        """Get clinical notes by ICD diagnosis code"""
        return cls.query.filter_by(diagnosis_icd=diagnosis_icd)\
                       .order_by(cls.created_at.desc())\
                       .limit(limit).all()
