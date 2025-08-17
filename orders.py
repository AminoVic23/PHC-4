"""
Order, LabResult, and RadiologyReport models for laboratory and radiology
"""
from datetime import datetime
from app import db

class Order(db.Model):
    """Order model for laboratory and radiology orders"""
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=False, index=True)
    ordered_by_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False, index=True)
    type = db.Column(db.String(20), nullable=False, index=True)  # lab, rad
    code = db.Column(db.String(20), nullable=False, index=True)
    description = db.Column(db.String(200), nullable=False)
    priority = db.Column(db.String(20), default='routine', nullable=False, index=True)  # routine, urgent, stat
    status = db.Column(db.String(20), default='ordered', nullable=False, index=True)  # ordered, in_progress, reported, cancelled
    clinical_indication = db.Column(db.Text)
    special_instructions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    visit = db.relationship('Visit', backref='orders')
    ordered_by = db.relationship('Staff', backref='orders')
    lab_result = db.relationship('LabResult', backref='order', uselist=False)
    radiology_report = db.relationship('RadiologyReport', backref='order', uselist=False)
    
    def __init__(self, **kwargs):
        super(Order, self).__init__(**kwargs)
    
    @property
    def is_lab_order(self):
        """Check if this is a laboratory order"""
        return self.type == 'lab'
    
    @property
    def is_radiology_order(self):
        """Check if this is a radiology order"""
        return self.type == 'rad'
    
    @property
    def is_urgent(self):
        """Check if order is urgent or stat"""
        return self.priority in ['urgent', 'stat']
    
    @property
    def is_completed(self):
        """Check if order is completed"""
        return self.status == 'reported'
    
    @property
    def turnaround_time(self):
        """Calculate turnaround time if completed"""
        if self.completed_at and self.created_at:
            return self.completed_at - self.created_at
        return None
    
    def start_processing(self):
        """Mark order as in progress"""
        self.status = 'in_progress'
    
    def complete_order(self):
        """Mark order as completed"""
        self.status = 'reported'
        self.completed_at = datetime.utcnow()
    
    def cancel_order(self):
        """Cancel the order"""
        self.status = 'cancelled'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'visit_id': self.visit_id,
            'visit_no': self.visit.visit_no if self.visit else None,
            'ordered_by_id': self.ordered_by_id,
            'ordered_by_name': self.ordered_by.name if self.ordered_by else None,
            'type': self.type,
            'code': self.code,
            'description': self.description,
            'priority': self.priority,
            'status': self.status,
            'clinical_indication': self.clinical_indication,
            'special_instructions': self.special_instructions,
            'is_lab_order': self.is_lab_order,
            'is_radiology_order': self.is_radiology_order,
            'is_urgent': self.is_urgent,
            'is_completed': self.is_completed,
            'turnaround_time': str(self.turnaround_time) if self.turnaround_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
    
    def __repr__(self):
        return f'<Order {self.code}: {self.description} ({self.status})>'
    
    @classmethod
    def get_pending_orders(cls, order_type=None):
        """Get pending orders, optionally filtered by type"""
        query = cls.query.filter(cls.status.in_(['ordered', 'in_progress']))
        if order_type:
            query = query.filter_by(type=order_type)
        return query.order_by(cls.priority.desc(), cls.created_at).all()
    
    @classmethod
    def get_urgent_orders(cls, order_type=None):
        """Get urgent orders"""
        query = cls.query.filter(
            cls.priority.in_(['urgent', 'stat']),
            cls.status.in_(['ordered', 'in_progress'])
        )
        if order_type:
            query = query.filter_by(type=order_type)
        return query.order_by(cls.created_at).all()
    
    @classmethod
    def get_visit_orders(cls, visit_id):
        """Get all orders for a visit"""
        return cls.query.filter_by(visit_id=visit_id)\
                       .order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_orders_by_provider(cls, provider_id, limit=20):
        """Get recent orders by a provider"""
        return cls.query.filter_by(ordered_by_id=provider_id)\
                       .order_by(cls.created_at.desc())\
                       .limit(limit).all()

class LabResult(db.Model):
    """Laboratory result model"""
    __tablename__ = 'lab_results'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), unique=True, nullable=False, index=True)
    analyte = db.Column(db.String(50), nullable=False, index=True)
    value = db.Column(db.String(50), nullable=False)
    unit = db.Column(db.String(20))
    ref_range = db.Column(db.String(50))
    flag = db.Column(db.String(10), index=True)  # H, L, N, CRITICAL
    method = db.Column(db.String(100))
    instrument = db.Column(db.String(100))
    reported_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    reported_by_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    verified_at = db.Column(db.DateTime)
    verified_by_id = db.Column(db.Integer, db.ForeignKey('staff.id'))
    notes = db.Column(db.Text)
    
    # Relationships
    order = db.relationship('Order', backref='lab_result')
    reported_by = db.relationship('Staff', foreign_keys=[reported_by_id], backref='reported_lab_results')
    verified_by = db.relationship('Staff', foreign_keys=[verified_by_id], backref='verified_lab_results')
    
    def __init__(self, **kwargs):
        super(LabResult, self).__init__(**kwargs)
    
    @property
    def is_abnormal(self):
        """Check if result is abnormal"""
        return self.flag in ['H', 'L', 'CRITICAL']
    
    @property
    def is_critical(self):
        """Check if result is critical"""
        return self.flag == 'CRITICAL'
    
    @property
    def is_verified(self):
        """Check if result is verified"""
        return self.verified_at is not None
    
    def verify_result(self, verified_by_id):
        """Verify the result"""
        self.verified_at = datetime.utcnow()
        self.verified_by_id = verified_by_id
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'analyte': self.analyte,
            'value': self.value,
            'unit': self.unit,
            'ref_range': self.ref_range,
            'flag': self.flag,
            'method': self.method,
            'instrument': self.instrument,
            'is_abnormal': self.is_abnormal,
            'is_critical': self.is_critical,
            'is_verified': self.is_verified,
            'reported_at': self.reported_at.isoformat() if self.reported_at else None,
            'reported_by_name': self.reported_by.name if self.reported_by else None,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'verified_by_name': self.verified_by.name if self.verified_by else None,
            'notes': self.notes
        }
    
    def __repr__(self):
        return f'<LabResult {self.analyte}: {self.value} {self.unit} ({self.flag})>'
    
    @classmethod
    def get_unverified_results(cls):
        """Get unverified lab results"""
        return cls.query.filter_by(verified_at=None)\
                       .order_by(cls.reported_at.desc()).all()
    
    @classmethod
    def get_critical_results(cls):
        """Get critical lab results"""
        return cls.query.filter_by(flag='CRITICAL')\
                       .order_by(cls.reported_at.desc()).all()
    
    @classmethod
    def get_results_by_analyte(cls, analyte, limit=20):
        """Get results by analyte"""
        return cls.query.filter_by(analyte=analyte)\
                       .order_by(cls.reported_at.desc())\
                       .limit(limit).all()

class RadiologyReport(db.Model):
    """Radiology report model"""
    __tablename__ = 'radiology_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), unique=True, nullable=False, index=True)
    modality = db.Column(db.String(20), nullable=False, index=True)  # XR, CT, MRI, US, etc.
    report_text = db.Column(db.Text, nullable=False)
    impression = db.Column(db.Text)
    findings = db.Column(db.Text)
    images_link = db.Column(db.String(500))
    reported_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    reported_by_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    verified_at = db.Column(db.DateTime)
    verified_by_id = db.Column(db.Integer, db.ForeignKey('staff.id'))
    notes = db.Column(db.Text)
    
    # Relationships
    order = db.relationship('Order', backref='radiology_report')
    reported_by = db.relationship('Staff', foreign_keys=[reported_by_id], backref='reported_radiology_reports')
    verified_by = db.relationship('Staff', foreign_keys=[verified_by_id], backref='verified_radiology_reports')
    
    def __init__(self, **kwargs):
        super(RadiologyReport, self).__init__(**kwargs)
    
    @property
    def is_verified(self):
        """Check if report is verified"""
        return self.verified_at is not None
    
    def verify_report(self, verified_by_id):
        """Verify the report"""
        self.verified_at = datetime.utcnow()
        self.verified_by_id = verified_by_id
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'modality': self.modality,
            'report_text': self.report_text,
            'impression': self.impression,
            'findings': self.findings,
            'images_link': self.images_link,
            'is_verified': self.is_verified,
            'reported_at': self.reported_at.isoformat() if self.reported_at else None,
            'reported_by_name': self.reported_by.name if self.reported_by else None,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'verified_by_name': self.verified_by.name if self.verified_by else None,
            'notes': self.notes
        }
    
    def __repr__(self):
        return f'<RadiologyReport {self.modality}: {self.impression[:50] if self.impression else "No impression"}>'
    
    @classmethod
    def get_unverified_reports(cls):
        """Get unverified radiology reports"""
        return cls.query.filter_by(verified_at=None)\
                       .order_by(cls.reported_at.desc()).all()
    
    @classmethod
    def get_reports_by_modality(cls, modality, limit=20):
        """Get reports by modality"""
        return cls.query.filter_by(modality=modality)\
                       .order_by(cls.reported_at.desc())\
                       .limit(limit).all()
