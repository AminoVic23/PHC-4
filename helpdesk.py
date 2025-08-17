"""
Helpdesk models for IT support and ticketing
"""
from datetime import datetime, timedelta
from app import db

class Ticket(db.Model):
    """Helpdesk ticket model for IT support"""
    __tablename__ = 'tickets'

    id = db.Column(db.Integer, primary_key=True)
    ticket_no = db.Column(db.String(20), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)  # hardware, software, network, access, other
    priority = db.Column(db.String(20), default='medium', nullable=False, index=True)  # low, medium, high, critical
    status = db.Column(db.String(20), default='open', nullable=False, index=True)  # open, assigned, in_progress, resolved, closed
    opened_by_staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False, index=True)
    assigned_to = db.Column(db.Integer, db.ForeignKey('staff.id'), index=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), index=True)
    opened_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    assigned_at = db.Column(db.DateTime)
    resolved_at = db.Column(db.DateTime)
    closed_at = db.Column(db.DateTime)
    sla_target_hours = db.Column(db.Integer, default=24)  # Service Level Agreement target in hours
    resolution_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    opened_by = db.relationship('Staff', foreign_keys=[opened_by_staff_id], backref='opened_tickets')
    assigned_to_staff = db.relationship('Staff', foreign_keys=[assigned_to], backref='assigned_tickets')
    department = db.relationship('Department', backref='tickets')

    def __init__(self, **kwargs):
        super(Ticket, self).__init__(**kwargs)
        if not self.ticket_no:
            self.ticket_no = self.generate_ticket_no()

    @property
    def is_open(self):
        """Check if ticket is open"""
        return self.status == 'open'

    @property
    def is_assigned(self):
        """Check if ticket is assigned"""
        return self.status == 'assigned'

    @property
    def is_in_progress(self):
        """Check if ticket is in progress"""
        return self.status == 'in_progress'

    @property
    def is_resolved(self):
        """Check if ticket is resolved"""
        return self.status == 'resolved'

    @property
    def is_closed(self):
        """Check if ticket is closed"""
        return self.status == 'closed'

    @property
    def is_critical(self):
        """Check if ticket is critical priority"""
        return self.priority == 'critical'

    @property
    def is_high_priority(self):
        """Check if ticket is high or critical priority"""
        return self.priority in ['high', 'critical']

    @property
    def age_hours(self):
        """Get ticket age in hours"""
        if self.opened_at:
            return (datetime.utcnow() - self.opened_at).total_seconds() / 3600
        return 0

    @property
    def age_days(self):
        """Get ticket age in days"""
        if self.opened_at:
            return (datetime.utcnow() - self.opened_at).days
        return 0

    @property
    def is_overdue(self):
        """Check if ticket is overdue based on SLA"""
        if self.status in ['resolved', 'closed']:
            return False
        return self.age_hours > self.sla_target_hours

    @property
    def time_to_resolution(self):
        """Get time to resolution in hours"""
        if self.resolved_at and self.opened_at:
            return (self.resolved_at - self.opened_at).total_seconds() / 3600
        return None

    @property
    def sla_breach_hours(self):
        """Get SLA breach time in hours"""
        if self.is_overdue:
            return self.age_hours - self.sla_target_hours
        return 0

    def assign_ticket(self, assigned_to_id):
        """Assign ticket to staff member"""
        self.assigned_to = assigned_to_id
        self.status = 'assigned'
        self.assigned_at = datetime.utcnow()

    def start_work(self):
        """Start working on the ticket"""
        self.status = 'in_progress'

    def resolve_ticket(self, resolution_notes=None):
        """Resolve the ticket"""
        self.status = 'resolved'
        self.resolved_at = datetime.utcnow()
        if resolution_notes:
            self.resolution_notes = resolution_notes

    def close_ticket(self):
        """Close the ticket"""
        self.status = 'closed'
        self.closed_at = datetime.utcnow()

    def reopen_ticket(self):
        """Reopen a closed ticket"""
        self.status = 'open'
        self.closed_at = None

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'ticket_no': self.ticket_no,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'priority': self.priority,
            'status': self.status,
            'opened_by_staff_id': self.opened_by_staff_id,
            'opened_by_name': self.opened_by.name if self.opened_by else None,
            'assigned_to': self.assigned_to,
            'assigned_to_name': self.assigned_to_staff.name if self.assigned_to_staff else None,
            'department_id': self.department_id,
            'department_name': self.department.name if self.department else None,
            'opened_at': self.opened_at.isoformat() if self.opened_at else None,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'sla_target_hours': self.sla_target_hours,
            'resolution_notes': self.resolution_notes,
            'is_open': self.is_open,
            'is_assigned': self.is_assigned,
            'is_in_progress': self.is_in_progress,
            'is_resolved': self.is_resolved,
            'is_closed': self.is_closed,
            'is_critical': self.is_critical,
            'is_high_priority': self.is_high_priority,
            'age_hours': self.age_hours,
            'age_days': self.age_days,
            'is_overdue': self.is_overdue,
            'time_to_resolution': self.time_to_resolution,
            'sla_breach_hours': self.sla_breach_hours,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<Ticket {self.ticket_no}: {self.title} ({self.status})>'

    @classmethod
    def generate_ticket_no(cls):
        """Generate a unique ticket number"""
        import random
        import string

        while True:
            # Generate ticket number in format: TKT-YYYYMMDD-XXXXX
            date_str = datetime.now().strftime('%Y%m%d')
            digits = ''.join(random.choices(string.digits, k=5))
            ticket_no = f"TKT-{date_str}-{digits}"

            # Check if ticket number already exists
            if not cls.query.filter_by(ticket_no=ticket_no).first():
                return ticket_no

    @classmethod
    def get_open_tickets(cls):
        """Get all open tickets"""
        return cls.query.filter_by(status='open').order_by(cls.priority.desc(), cls.opened_at).all()

    @classmethod
    def get_assigned_tickets(cls, staff_id=None):
        """Get assigned tickets"""
        query = cls.query.filter_by(status='assigned')
        if staff_id:
            query = query.filter_by(assigned_to=staff_id)
        return query.order_by(cls.priority.desc(), cls.assigned_at).all()

    @classmethod
    def get_in_progress_tickets(cls, staff_id=None):
        """Get tickets in progress"""
        query = cls.query.filter_by(status='in_progress')
        if staff_id:
            query = query.filter_by(assigned_to=staff_id)
        return query.order_by(cls.priority.desc(), cls.opened_at).all()

    @classmethod
    def get_overdue_tickets(cls):
        """Get overdue tickets"""
        return [ticket for ticket in cls.query.filter(
            cls.status.in_(['open', 'assigned', 'in_progress'])
        ).all() if ticket.is_overdue]

    @classmethod
    def get_critical_tickets(cls):
        """Get critical priority tickets"""
        return cls.query.filter_by(priority='critical').order_by(cls.opened_at).all()

    @classmethod
    def get_high_priority_tickets(cls):
        """Get high priority tickets"""
        return cls.query.filter(
            cls.priority.in_(['high', 'critical'])
        ).order_by(cls.priority.desc(), cls.opened_at).all()

    @classmethod
    def get_tickets_by_category(cls, category, limit=50):
        """Get tickets by category"""
        return cls.query.filter_by(category=category)\
                       .order_by(cls.opened_at.desc())\
                       .limit(limit).all()

    @classmethod
    def get_tickets_by_department(cls, department_id, limit=50):
        """Get tickets by department"""
        return cls.query.filter_by(department_id=department_id)\
                       .order_by(cls.opened_at.desc())\
                       .limit(limit).all()

    @classmethod
    def get_staff_tickets(cls, staff_id, limit=20):
        """Get tickets opened by a staff member"""
        return cls.query.filter_by(opened_by_staff_id=staff_id)\
                       .order_by(cls.opened_at.desc())\
                       .limit(limit).all()

    @classmethod
    def get_assigned_staff_tickets(cls, staff_id, limit=20):
        """Get tickets assigned to a staff member"""
        return cls.query.filter_by(assigned_to=staff_id)\
                       .order_by(cls.priority.desc(), cls.opened_at)\
                       .limit(limit).all()

    @classmethod
    def get_recently_resolved_tickets(cls, days=7):
        """Get recently resolved tickets"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return cls.query.filter(
            cls.status == 'resolved',
            cls.resolved_at >= cutoff_date
        ).order_by(cls.resolved_at.desc()).all()

    @classmethod
    def get_sla_breach_tickets(cls):
        """Get tickets that have breached SLA"""
        return cls.get_overdue_tickets()

    @classmethod
    def get_ticket_statistics(cls):
        """Get ticket statistics"""
        total_tickets = cls.query.count()
        open_tickets = cls.query.filter_by(status='open').count()
        assigned_tickets = cls.query.filter_by(status='assigned').count()
        in_progress_tickets = cls.query.filter_by(status='in_progress').count()
        resolved_tickets = cls.query.filter_by(status='resolved').count()
        closed_tickets = cls.query.filter_by(status='closed').count()
        
        critical_tickets = cls.query.filter_by(priority='critical').count()
        high_priority_tickets = cls.query.filter_by(priority='high').count()
        
        overdue_tickets = len(cls.get_overdue_tickets())
        
        return {
            'total_tickets': total_tickets,
            'open_tickets': open_tickets,
            'assigned_tickets': assigned_tickets,
            'in_progress_tickets': in_progress_tickets,
            'resolved_tickets': resolved_tickets,
            'closed_tickets': closed_tickets,
            'critical_tickets': critical_tickets,
            'high_priority_tickets': high_priority_tickets,
            'overdue_tickets': overdue_tickets
        }
