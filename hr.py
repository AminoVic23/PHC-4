"""
HR models for staff scheduling and leave management
"""
from datetime import datetime, timedelta
from app import db

class Shift(db.Model):
    """Shift model for staff scheduling"""
    __tablename__ = 'shifts'

    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False, index=True)
    shift_date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    shift_type = db.Column(db.String(50), nullable=False, index=True)  # morning, afternoon, night, on_call
    status = db.Column(db.String(20), default='scheduled', nullable=False, index=True)  # scheduled, completed, absent, cancelled
    notes = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    staff_member = db.relationship('Staff', foreign_keys=[staff_id], backref='shifts')
    department = db.relationship('Department', backref='shifts')
    created_by = db.relationship('Staff', foreign_keys=[created_by_id], backref='created_shifts')

    def __init__(self, **kwargs):
        super(Shift, self).__init__(**kwargs)

    @property
    def duration_hours(self):
        """Calculate shift duration in hours"""
        if self.start_time and self.end_time:
            start_dt = datetime.combine(datetime.today(), self.start_time)
            end_dt = datetime.combine(datetime.today(), self.end_time)

            # Handle overnight shifts
            if end_dt < start_dt:
                end_dt += timedelta(days=1)

            duration = end_dt - start_dt
            return duration.total_seconds() / 3600
        return 0

    @property
    def is_today(self):
        """Check if shift is today"""
        return self.shift_date == datetime.now().date()

    @property
    def is_past(self):
        """Check if shift is in the past"""
        return self.shift_date < datetime.now().date()

    @property
    def is_future(self):
        """Check if shift is in the future"""
        return self.shift_date > datetime.now().date()

    @property
    def is_completed(self):
        """Check if shift is completed"""
        return self.status == 'completed'

    @property
    def is_absent(self):
        """Check if staff was absent"""
        return self.status == 'absent'

    def complete_shift(self):
        """Mark shift as completed"""
        self.status = 'completed'

    def mark_absent(self):
        """Mark staff as absent"""
        self.status = 'absent'

    def cancel_shift(self):
        """Cancel the shift"""
        self.status = 'cancelled'

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'staff_id': self.staff_id,
            'staff_name': self.staff_member.name if self.staff_member else None,
            'department_id': self.department_id,
            'department_name': self.department.name if self.department else None,
            'shift_date': self.shift_date.isoformat() if self.shift_date else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'shift_type': self.shift_type,
            'status': self.status,
            'notes': self.notes,
            'duration_hours': self.duration_hours,
            'is_today': self.is_today,
            'is_past': self.is_past,
            'is_future': self.is_future,
            'is_completed': self.is_completed,
            'is_absent': self.is_absent,
            'created_by_name': self.created_by.name if self.created_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<Shift {self.staff_member.name if self.staff_member else "Unknown"}: {self.shift_date} ({self.shift_type})>'

    @classmethod
    def get_today_shifts(cls, department_id=None):
        """Get today's shifts"""
        today = datetime.now().date()
        query = cls.query.filter_by(shift_date=today)

        if department_id:
            query = query.filter_by(department_id=department_id)

        return query.order_by(cls.start_time).all()

    @classmethod
    def get_staff_shifts(cls, staff_id, start_date=None, end_date=None):
        """Get shifts for a staff member"""
        query = cls.query.filter_by(staff_id=staff_id)

        if start_date:
            query = query.filter(cls.shift_date >= start_date)
        if end_date:
            query = query.filter(cls.shift_date <= end_date)

        return query.order_by(cls.shift_date, cls.start_time).all()

    @classmethod
    def get_department_shifts(cls, department_id, date=None):
        """Get shifts for a department"""
        query = cls.query.filter_by(department_id=department_id)

        if date:
            query = query.filter_by(shift_date=date)

        return query.order_by(cls.start_time).all()

    @classmethod
    def get_absent_shifts(cls, start_date=None, end_date=None):
        """Get absent shifts"""
        query = cls.query.filter_by(status='absent')

        if start_date:
            query = query.filter(cls.shift_date >= start_date)
        if end_date:
            query = query.filter(cls.shift_date <= end_date)

        return query.order_by(cls.shift_date.desc()).all()

    @classmethod
    def get_upcoming_shifts(cls, days=7):
        """Get upcoming shifts"""
        end_date = datetime.now().date() + timedelta(days=days)
        return cls.query.filter(
            cls.shift_date >= datetime.now().date(),
            cls.shift_date <= end_date,
            cls.status == 'scheduled'
        ).order_by(cls.shift_date, cls.start_time).all()

class LeaveRequest(db.Model):
    """Leave request model for staff leave management"""
    __tablename__ = 'leave_requests'

    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False, index=True)
    leave_type = db.Column(db.String(50), nullable=False, index=True)  # annual, sick, maternity, paternity, unpaid
    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, nullable=False, index=True)
    days_requested = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False, index=True)  # pending, approved, rejected, cancelled
    approved_by_id = db.Column(db.Integer, db.ForeignKey('staff.id'))
    approved_at = db.Column(db.DateTime)
    rejection_reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    staff_member = db.relationship('Staff', foreign_keys=[staff_id], backref='leave_requests')
    approved_by = db.relationship('Staff', foreign_keys=[approved_by_id], backref='approved_leave_requests')

    def __init__(self, **kwargs):
        super(LeaveRequest, self).__init__(**kwargs)
        if not self.days_requested and self.start_date and self.end_date:
            self.calculate_days()

    @property
    def is_pending(self):
        """Check if leave request is pending"""
        return self.status == 'pending'

    @property
    def is_approved(self):
        """Check if leave request is approved"""
        return self.status == 'approved'

    @property
    def is_rejected(self):
        """Check if leave request is rejected"""
        return self.status == 'rejected'

    @property
    def is_cancelled(self):
        """Check if leave request is cancelled"""
        return self.status == 'cancelled'

    @property
    def is_current(self):
        """Check if leave is currently active"""
        today = datetime.now().date()
        return self.is_approved and self.start_date <= today <= self.end_date

    @property
    def is_future(self):
        """Check if leave is in the future"""
        return self.start_date > datetime.now().date()

    @property
    def is_past(self):
        """Check if leave is in the past"""
        return self.end_date < datetime.now().date()

    def calculate_days(self):
        """Calculate number of days requested"""
        if self.start_date and self.end_date:
            delta = self.end_date - self.start_date
            self.days_requested = delta.days + 1  # Include both start and end dates

    def approve_leave(self, approved_by_id):
        """Approve the leave request"""
        self.status = 'approved'
        self.approved_by_id = approved_by_id
        self.approved_at = datetime.utcnow()

    def reject_leave(self, approved_by_id, rejection_reason):
        """Reject the leave request"""
        self.status = 'rejected'
        self.approved_by_id = approved_by_id
        self.approved_at = datetime.utcnow()
        self.rejection_reason = rejection_reason

    def cancel_leave(self):
        """Cancel the leave request"""
        self.status = 'cancelled'

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'staff_id': self.staff_id,
            'staff_name': self.staff_member.name if self.staff_member else None,
            'leave_type': self.leave_type,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'days_requested': self.days_requested,
            'reason': self.reason,
            'status': self.status,
            'approved_by_id': self.approved_by_id,
            'approved_by_name': self.approved_by.name if self.approved_by else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'rejection_reason': self.rejection_reason,
            'is_pending': self.is_pending,
            'is_approved': self.is_approved,
            'is_rejected': self.is_rejected,
            'is_cancelled': self.is_cancelled,
            'is_current': self.is_current,
            'is_future': self.is_future,
            'is_past': self.is_past,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<LeaveRequest {self.staff_member.name if self.staff_member else "Unknown"}: {self.leave_type} ({self.status})>'

    @classmethod
    def get_pending_requests(cls):
        """Get all pending leave requests"""
        return cls.query.filter_by(status='pending').order_by(cls.created_at).all()

    @classmethod
    def get_staff_requests(cls, staff_id, limit=20):
        """Get recent leave requests for a staff member"""
        return cls.query.filter_by(staff_id=staff_id)\
                       .order_by(cls.created_at.desc())\
                       .limit(limit).all()

    @classmethod
    def get_current_leave(cls):
        """Get currently active leave requests"""
        today = datetime.now().date()
        return cls.query.filter(
            cls.status == 'approved',
            cls.start_date <= today,
            cls.end_date >= today
        ).order_by(cls.start_date).all()

    @classmethod
    def get_upcoming_leave(cls, days=30):
        """Get upcoming approved leave requests"""
        end_date = datetime.now().date() + timedelta(days=days)
        return cls.query.filter(
            cls.status == 'approved',
            cls.start_date >= datetime.now().date(),
            cls.start_date <= end_date
        ).order_by(cls.start_date).all()

    @classmethod
    def get_leave_by_type(cls, leave_type, limit=50):
        """Get leave requests by type"""
        return cls.query.filter_by(leave_type=leave_type)\
                       .order_by(cls.created_at.desc())\
                       .limit(limit).all()

    @classmethod
    def get_approved_leave(cls, start_date=None, end_date=None):
        """Get approved leave requests"""
        query = cls.query.filter_by(status='approved')

        if start_date:
            query = query.filter(cls.start_date >= start_date)
        if end_date:
            query = query.filter(cls.end_date <= end_date)

        return query.order_by(cls.start_date).all()
