"""
Quality models for incident management and audits
"""
from datetime import datetime, timedelta
from app import db

class QualityIncident(db.Model):
    """Quality incident model for managing quality issues"""
    __tablename__ = 'quality_incidents'

    id = db.Column(db.Integer, primary_key=True)
    incident_no = db.Column(db.String(20), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)  # medication_error, infection, fall, equipment, documentation, other
    severity = db.Column(db.String(20), default='medium', nullable=False, index=True)  # low, medium, high, critical
    status = db.Column(db.String(20), default='reported', nullable=False, index=True)  # reported, investigating, resolved, closed
    reported_by_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False, index=True)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('staff.id'), index=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), index=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), index=True)
    incident_date = db.Column(db.Date, nullable=False, index=True)
    reported_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    assigned_at = db.Column(db.DateTime)
    resolved_at = db.Column(db.DateTime)
    closed_at = db.Column(db.DateTime)
    root_cause = db.Column(db.Text)
    corrective_actions = db.Column(db.Text)
    preventive_measures = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    reported_by = db.relationship('Staff', foreign_keys=[reported_by_id], backref='reported_incidents')
    assigned_to = db.relationship('Staff', foreign_keys=[assigned_to_id], backref='assigned_incidents')
    department = db.relationship('Department', backref='incidents')
    patient = db.relationship('Patient', backref='incidents')
    visit = db.relationship('Visit', backref='incidents')

    def __init__(self, **kwargs):
        super(QualityIncident, self).__init__(**kwargs)
        if not self.incident_no:
            self.incident_no = self.generate_incident_no()

    @property
    def is_reported(self):
        """Check if incident is reported"""
        return self.status == 'reported'

    @property
    def is_investigating(self):
        """Check if incident is under investigation"""
        return self.status == 'investigating'

    @property
    def is_resolved(self):
        """Check if incident is resolved"""
        return self.status == 'resolved'

    @property
    def is_closed(self):
        """Check if incident is closed"""
        return self.status == 'closed'

    @property
    def is_critical(self):
        """Check if incident is critical severity"""
        return self.severity == 'critical'

    @property
    def is_high_severity(self):
        """Check if incident is high or critical severity"""
        return self.severity in ['high', 'critical']

    @property
    def age_days(self):
        """Get incident age in days"""
        if self.reported_at:
            return (datetime.utcnow() - self.reported_at).days
        return 0

    @property
    def time_to_resolution(self):
        """Get time to resolution in days"""
        if self.resolved_at and self.reported_at:
            return (self.resolved_at - self.reported_at).days
        return None

    def assign_incident(self, assigned_to_id):
        """Assign incident to staff member"""
        self.assigned_to_id = assigned_to_id
        self.status = 'investigating'
        self.assigned_at = datetime.utcnow()

    def resolve_incident(self, root_cause=None, corrective_actions=None, preventive_measures=None):
        """Resolve the incident"""
        self.status = 'resolved'
        self.resolved_at = datetime.utcnow()
        if root_cause:
            self.root_cause = root_cause
        if corrective_actions:
            self.corrective_actions = corrective_actions
        if preventive_measures:
            self.preventive_measures = preventive_measures

    def close_incident(self):
        """Close the incident"""
        self.status = 'closed'
        self.closed_at = datetime.utcnow()

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'incident_no': self.incident_no,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'severity': self.severity,
            'status': self.status,
            'reported_by_id': self.reported_by_id,
            'reported_by_name': self.reported_by.name if self.reported_by else None,
            'assigned_to_id': self.assigned_to_id,
            'assigned_to_name': self.assigned_to.name if self.assigned_to else None,
            'department_id': self.department_id,
            'department_name': self.department.name if self.department else None,
            'patient_id': self.patient_id,
            'patient_name': self.patient.full_name if self.patient else None,
            'visit_id': self.visit_id,
            'visit_no': self.visit.visit_no if self.visit else None,
            'incident_date': self.incident_date.isoformat() if self.incident_date else None,
            'reported_at': self.reported_at.isoformat() if self.reported_at else None,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'root_cause': self.root_cause,
            'corrective_actions': self.corrective_actions,
            'preventive_measures': self.preventive_measures,
            'notes': self.notes,
            'is_reported': self.is_reported,
            'is_investigating': self.is_investigating,
            'is_resolved': self.is_resolved,
            'is_closed': self.is_closed,
            'is_critical': self.is_critical,
            'is_high_severity': self.is_high_severity,
            'age_days': self.age_days,
            'time_to_resolution': self.time_to_resolution,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<QualityIncident {self.incident_no}: {self.title} ({self.severity})>'

    @classmethod
    def generate_incident_no(cls):
        """Generate a unique incident number"""
        import random
        import string

        while True:
            # Generate incident number in format: INC-YYYYMMDD-XXXXX
            date_str = datetime.now().strftime('%Y%m%d')
            digits = ''.join(random.choices(string.digits, k=5))
            incident_no = f"INC-{date_str}-{digits}"

            # Check if incident number already exists
            if not cls.query.filter_by(incident_no=incident_no).first():
                return incident_no

    @classmethod
    def get_reported_incidents(cls):
        """Get all reported incidents"""
        return cls.query.filter_by(status='reported').order_by(cls.severity.desc(), cls.reported_at).all()

    @classmethod
    def get_investigating_incidents(cls):
        """Get incidents under investigation"""
        return cls.query.filter_by(status='investigating').order_by(cls.severity.desc(), cls.assigned_at).all()

    @classmethod
    def get_critical_incidents(cls):
        """Get critical severity incidents"""
        return cls.query.filter_by(severity='critical').order_by(cls.reported_at).all()

    @classmethod
    def get_high_severity_incidents(cls):
        """Get high severity incidents"""
        return cls.query.filter(
            cls.severity.in_(['high', 'critical'])
        ).order_by(cls.severity.desc(), cls.reported_at).all()

    @classmethod
    def get_incidents_by_category(cls, category, limit=50):
        """Get incidents by category"""
        return cls.query.filter_by(category=category)\
                       .order_by(cls.reported_at.desc())\
                       .limit(limit).all()

    @classmethod
    def get_incidents_by_department(cls, department_id, limit=50):
        """Get incidents by department"""
        return cls.query.filter_by(department_id=department_id)\
                       .order_by(cls.reported_at.desc())\
                       .limit(limit).all()

    @classmethod
    def get_patient_incidents(cls, patient_id, limit=20):
        """Get incidents for a patient"""
        return cls.query.filter_by(patient_id=patient_id)\
                       .order_by(cls.reported_at.desc())\
                       .limit(limit).all()

    @classmethod
    def get_recently_resolved_incidents(cls, days=30):
        """Get recently resolved incidents"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return cls.query.filter(
            cls.status == 'resolved',
            cls.resolved_at >= cutoff_date
        ).order_by(cls.resolved_at.desc()).all()

    @classmethod
    def get_incident_statistics(cls):
        """Get incident statistics"""
        total_incidents = cls.query.count()
        reported_incidents = cls.query.filter_by(status='reported').count()
        investigating_incidents = cls.query.filter_by(status='investigating').count()
        resolved_incidents = cls.query.filter_by(status='resolved').count()
        closed_incidents = cls.query.filter_by(status='closed').count()
        
        critical_incidents = cls.query.filter_by(severity='critical').count()
        high_severity_incidents = cls.query.filter_by(severity='high').count()
        
        return {
            'total_incidents': total_incidents,
            'reported_incidents': reported_incidents,
            'investigating_incidents': investigating_incidents,
            'resolved_incidents': resolved_incidents,
            'closed_incidents': closed_incidents,
            'critical_incidents': critical_incidents,
            'high_severity_incidents': high_severity_incidents
        }

class Audit(db.Model):
    """Audit model for quality audits"""
    __tablename__ = 'audits'

    id = db.Column(db.Integer, primary_key=True)
    audit_no = db.Column(db.String(20), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    audit_type = db.Column(db.String(50), nullable=False, index=True)  # clinical, administrative, safety, compliance
    scope = db.Column(db.String(200), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), index=True)
    auditor_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False, index=True)
    planned_date = db.Column(db.Date, nullable=False, index=True)
    actual_date = db.Column(db.Date, index=True)
    status = db.Column(db.String(20), default='planned', nullable=False, index=True)  # planned, in_progress, completed, cancelled
    findings = db.Column(db.Text)
    recommendations = db.Column(db.Text)
    score = db.Column(db.Integer)  # Audit score (0-100)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    # Relationships
    department = db.relationship('Department', backref='audits')
    auditor = db.relationship('Staff', backref='conducted_audits')

    def __init__(self, **kwargs):
        super(Audit, self).__init__(**kwargs)
        if not self.audit_no:
            self.audit_no = self.generate_audit_no()

    @property
    def is_planned(self):
        """Check if audit is planned"""
        return self.status == 'planned'

    @property
    def is_in_progress(self):
        """Check if audit is in progress"""
        return self.status == 'in_progress'

    @property
    def is_completed(self):
        """Check if audit is completed"""
        return self.status == 'completed'

    @property
    def is_cancelled(self):
        """Check if audit is cancelled"""
        return self.status == 'cancelled'

    @property
    def is_overdue(self):
        """Check if audit is overdue"""
        return self.planned_date < datetime.now().date() and self.status == 'planned'

    @property
    def is_today(self):
        """Check if audit is scheduled for today"""
        return self.planned_date == datetime.now().date()

    @property
    def score_grade(self):
        """Get audit score grade"""
        if not self.score:
            return 'N/A'
        elif self.score >= 90:
            return 'A'
        elif self.score >= 80:
            return 'B'
        elif self.score >= 70:
            return 'C'
        elif self.score >= 60:
            return 'D'
        else:
            return 'F'

    def start_audit(self):
        """Start the audit"""
        self.status = 'in_progress'
        self.actual_date = datetime.now().date()

    def complete_audit(self, findings=None, recommendations=None, score=None):
        """Complete the audit"""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
        if findings:
            self.findings = findings
        if recommendations:
            self.recommendations = recommendations
        if score is not None:
            self.score = score

    def cancel_audit(self):
        """Cancel the audit"""
        self.status = 'cancelled'

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'audit_no': self.audit_no,
            'title': self.title,
            'description': self.description,
            'audit_type': self.audit_type,
            'scope': self.scope,
            'department_id': self.department_id,
            'department_name': self.department.name if self.department else None,
            'auditor_id': self.auditor_id,
            'auditor_name': self.auditor.name if self.auditor else None,
            'planned_date': self.planned_date.isoformat() if self.planned_date else None,
            'actual_date': self.actual_date.isoformat() if self.actual_date else None,
            'status': self.status,
            'findings': self.findings,
            'recommendations': self.recommendations,
            'score': self.score,
            'score_grade': self.score_grade,
            'is_planned': self.is_planned,
            'is_in_progress': self.is_in_progress,
            'is_completed': self.is_completed,
            'is_cancelled': self.is_cancelled,
            'is_overdue': self.is_overdue,
            'is_today': self.is_today,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

    def __repr__(self):
        return f'<Audit {self.audit_no}: {self.title} ({self.status})>'

    @classmethod
    def generate_audit_no(cls):
        """Generate a unique audit number"""
        import random
        import string

        while True:
            # Generate audit number in format: AUD-YYYYMMDD-XXXXX
            date_str = datetime.now().strftime('%Y%m%d')
            digits = ''.join(random.choices(string.digits, k=5))
            audit_no = f"AUD-{date_str}-{digits}"

            # Check if audit number already exists
            if not cls.query.filter_by(audit_no=audit_no).first():
                return audit_no

    @classmethod
    def get_planned_audits(cls):
        """Get all planned audits"""
        return cls.query.filter_by(status='planned').order_by(cls.planned_date).all()

    @classmethod
    def get_in_progress_audits(cls):
        """Get audits in progress"""
        return cls.query.filter_by(status='in_progress').order_by(cls.actual_date).all()

    @classmethod
    def get_overdue_audits(cls):
        """Get overdue audits"""
        today = datetime.now().date()
        return cls.query.filter(
            cls.status == 'planned',
            cls.planned_date < today
        ).order_by(cls.planned_date).all()

    @classmethod
    def get_today_audits(cls):
        """Get audits scheduled for today"""
        today = datetime.now().date()
        return cls.query.filter(
            cls.planned_date == today,
            cls.status.in_(['planned', 'in_progress'])
        ).order_by(cls.audit_type).all()

    @classmethod
    def get_audits_by_type(cls, audit_type, limit=50):
        """Get audits by type"""
        return cls.query.filter_by(audit_type=audit_type)\
                       .order_by(cls.planned_date.desc())\
                       .limit(limit).all()

    @classmethod
    def get_audits_by_department(cls, department_id, limit=50):
        """Get audits by department"""
        return cls.query.filter_by(department_id=department_id)\
                       .order_by(cls.planned_date.desc())\
                       .limit(limit).all()

    @classmethod
    def get_recently_completed_audits(cls, days=90):
        """Get recently completed audits"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return cls.query.filter(
            cls.status == 'completed',
            cls.completed_at >= cutoff_date
        ).order_by(cls.completed_at.desc()).all()

    @classmethod
    def get_audit_statistics(cls):
        """Get audit statistics"""
        total_audits = cls.query.count()
        planned_audits = cls.query.filter_by(status='planned').count()
        in_progress_audits = cls.query.filter_by(status='in_progress').count()
        completed_audits = cls.query.filter_by(status='completed').count()
        cancelled_audits = cls.query.filter_by(status='cancelled').count()
        
        overdue_audits = len(cls.get_overdue_audits())
        
        # Calculate average score for completed audits
        completed_with_score = cls.query.filter(
            cls.status == 'completed',
            cls.score.isnot(None)
        ).all()
        avg_score = sum(a.score for a in completed_with_score) / len(completed_with_score) if completed_with_score else 0
        
        return {
            'total_audits': total_audits,
            'planned_audits': planned_audits,
            'in_progress_audits': in_progress_audits,
            'completed_audits': completed_audits,
            'cancelled_audits': cancelled_audits,
            'overdue_audits': overdue_audits,
            'average_score': round(avg_score, 1) if avg_score > 0 else 0
        }
