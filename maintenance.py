"""
Maintenance models for facility maintenance and asset management
"""
from datetime import datetime, timedelta
from app import db

class Asset(db.Model):
    """Asset model for facility equipment and assets"""
    __tablename__ = 'assets'

    id = db.Column(db.Integer, primary_key=True)
    asset_no = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), nullable=False, index=True)  # medical_equipment, furniture, hvac, electrical, etc.
    type = db.Column(db.String(100), nullable=False, index=True)  # specific type within category
    location = db.Column(db.String(100), nullable=False, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), index=True)
    manufacturer = db.Column(db.String(200))
    model = db.Column(db.String(100))
    serial_number = db.Column(db.String(100), index=True)
    purchase_date = db.Column(db.Date, index=True)
    warranty_expiry = db.Column(db.Date, index=True)
    purchase_cost = db.Column(db.Numeric(10, 2))
    current_value = db.Column(db.Numeric(10, 2))
    status = db.Column(db.String(20), default='operational', nullable=False, index=True)  # operational, maintenance, out_of_service, retired
    condition = db.Column(db.String(20), default='good', nullable=False, index=True)  # excellent, good, fair, poor, critical
    last_maintenance_date = db.Column(db.Date, index=True)
    next_maintenance_date = db.Column(db.Date, index=True)
    maintenance_frequency_days = db.Column(db.Integer, default=365)  # Days between maintenance
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    department = db.relationship('Department', backref='assets')
    work_orders = db.relationship('WorkOrder', backref='asset', lazy='dynamic')

    def __init__(self, **kwargs):
        super(Asset, self).__init__(**kwargs)
        if not self.asset_no:
            self.asset_no = self.generate_asset_no()

    @property
    def is_operational(self):
        """Check if asset is operational"""
        return self.status == 'operational'

    @property
    def is_under_maintenance(self):
        """Check if asset is under maintenance"""
        return self.status == 'maintenance'

    @property
    def is_out_of_service(self):
        """Check if asset is out of service"""
        return self.status == 'out_of_service'

    @property
    def is_retired(self):
        """Check if asset is retired"""
        return self.status == 'retired'

    @property
    def is_warranty_active(self):
        """Check if asset is under warranty"""
        if not self.warranty_expiry:
            return False
        return self.warranty_expiry >= datetime.now().date()

    @property
    def is_maintenance_due(self):
        """Check if maintenance is due"""
        if not self.next_maintenance_date:
            return False
        return self.next_maintenance_date <= datetime.now().date()

    @property
    def is_maintenance_overdue(self):
        """Check if maintenance is overdue"""
        if not self.next_maintenance_date:
            return False
        return self.next_maintenance_date < datetime.now().date()

    @property
    def age_years(self):
        """Calculate asset age in years"""
        if self.purchase_date:
            return (datetime.now().date() - self.purchase_date).days / 365.25
        return None

    @property
    def days_since_last_maintenance(self):
        """Get days since last maintenance"""
        if self.last_maintenance_date:
            return (datetime.now().date() - self.last_maintenance_date).days
        return None

    @property
    def days_until_next_maintenance(self):
        """Get days until next maintenance"""
        if self.next_maintenance_date:
            days = (self.next_maintenance_date - datetime.now().date()).days
            return max(0, days)
        return None

    def schedule_maintenance(self, maintenance_date=None):
        """Schedule next maintenance"""
        if maintenance_date:
            self.next_maintenance_date = maintenance_date
        else:
            # Calculate based on frequency
            if self.last_maintenance_date:
                self.next_maintenance_date = self.last_maintenance_date + timedelta(days=self.maintenance_frequency_days)
            else:
                self.next_maintenance_date = datetime.now().date() + timedelta(days=self.maintenance_frequency_days)

    def complete_maintenance(self):
        """Mark maintenance as completed"""
        self.last_maintenance_date = datetime.now().date()
        self.status = 'operational'
        self.schedule_maintenance()

    def retire_asset(self):
        """Retire the asset"""
        self.status = 'retired'
        self.current_value = 0

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'asset_no': self.asset_no,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'type': self.type,
            'location': self.location,
            'department_id': self.department_id,
            'department_name': self.department.name if self.department else None,
            'manufacturer': self.manufacturer,
            'model': self.model,
            'serial_number': self.serial_number,
            'purchase_date': self.purchase_date.isoformat() if self.purchase_date else None,
            'warranty_expiry': self.warranty_expiry.isoformat() if self.warranty_expiry else None,
            'purchase_cost': float(self.purchase_cost) if self.purchase_cost else None,
            'current_value': float(self.current_value) if self.current_value else None,
            'status': self.status,
            'condition': self.condition,
            'last_maintenance_date': self.last_maintenance_date.isoformat() if self.last_maintenance_date else None,
            'next_maintenance_date': self.next_maintenance_date.isoformat() if self.next_maintenance_date else None,
            'maintenance_frequency_days': self.maintenance_frequency_days,
            'notes': self.notes,
            'is_operational': self.is_operational,
            'is_under_maintenance': self.is_under_maintenance,
            'is_out_of_service': self.is_out_of_service,
            'is_retired': self.is_retired,
            'is_warranty_active': self.is_warranty_active,
            'is_maintenance_due': self.is_maintenance_due,
            'is_maintenance_overdue': self.is_maintenance_overdue,
            'age_years': round(self.age_years, 1) if self.age_years else None,
            'days_since_last_maintenance': self.days_since_last_maintenance,
            'days_until_next_maintenance': self.days_until_next_maintenance,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<Asset {self.asset_no}: {self.name} ({self.status})>'

    @classmethod
    def generate_asset_no(cls):
        """Generate a unique asset number"""
        import random
        import string

        while True:
            # Generate asset number in format: AST-YYYYMMDD-XXXXX
            date_str = datetime.now().strftime('%Y%m%d')
            digits = ''.join(random.choices(string.digits, k=5))
            asset_no = f"AST-{date_str}-{digits}"

            # Check if asset number already exists
            if not cls.query.filter_by(asset_no=asset_no).first():
                return asset_no

    @classmethod
    def get_operational_assets(cls):
        """Get all operational assets"""
        return cls.query.filter_by(status='operational').order_by(cls.name).all()

    @classmethod
    def get_maintenance_due_assets(cls):
        """Get assets due for maintenance"""
        return [asset for asset in cls.query.filter_by(status='operational').all() if asset.is_maintenance_due]

    @classmethod
    def get_assets_by_category(cls, category, limit=50):
        """Get assets by category"""
        return cls.query.filter_by(category=category)\
                       .order_by(cls.name)\
                       .limit(limit).all()

    @classmethod
    def get_assets_by_department(cls, department_id, limit=50):
        """Get assets by department"""
        return cls.query.filter_by(department_id=department_id)\
                       .order_by(cls.name)\
                       .limit(limit).all()

    @classmethod
    def get_assets_by_location(cls, location, limit=50):
        """Get assets by location"""
        return cls.query.filter_by(location=location)\
                       .order_by(cls.name)\
                       .limit(limit).all()

    @classmethod
    def get_assets_by_condition(cls, condition, limit=50):
        """Get assets by condition"""
        return cls.query.filter_by(condition=condition)\
                       .order_by(cls.name)\
                       .limit(limit).all()

    @classmethod
    def get_warranty_expiring_assets(cls, days=30):
        """Get assets with warranty expiring soon"""
        cutoff_date = datetime.now().date() + timedelta(days=days)
        return cls.query.filter(
            cls.warranty_expiry <= cutoff_date,
            cls.warranty_expiry >= datetime.now().date()
        ).order_by(cls.warranty_expiry).all()

    @classmethod
    def get_asset_statistics(cls):
        """Get asset statistics"""
        total_assets = cls.query.count()
        operational_assets = cls.query.filter_by(status='operational').count()
        maintenance_assets = cls.query.filter_by(status='maintenance').count()
        out_of_service_assets = cls.query.filter_by(status='out_of_service').count()
        retired_assets = cls.query.filter_by(status='retired').count()
        
        maintenance_due = len(cls.get_maintenance_due_assets())
        
        # Calculate total value
        total_value = cls.query.with_entities(db.func.sum(cls.current_value)).scalar() or 0
        
        return {
            'total_assets': total_assets,
            'operational_assets': operational_assets,
            'maintenance_assets': maintenance_assets,
            'out_of_service_assets': out_of_service_assets,
            'retired_assets': retired_assets,
            'maintenance_due': maintenance_due,
            'total_value': float(total_value)
        }

class WorkOrder(db.Model):
    """Work order model for maintenance tasks"""
    __tablename__ = 'work_orders'

    id = db.Column(db.Integer, primary_key=True)
    work_order_no = db.Column(db.String(20), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), index=True)
    category = db.Column(db.String(50), nullable=False, index=True)  # preventive, corrective, emergency, inspection
    priority = db.Column(db.String(20), default='medium', nullable=False, index=True)  # low, medium, high, critical
    status = db.Column(db.String(20), default='open', nullable=False, index=True)  # open, assigned, in_progress, completed, cancelled
    opened_by_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False, index=True)
    assigned_to = db.Column(db.Integer, db.ForeignKey('staff.id'), index=True)
    location = db.Column(db.String(100), nullable=False, index=True)
    requested_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date, index=True)
    scheduled_date = db.Column(db.Date, index=True)
    started_date = db.Column(db.Date, index=True)
    completed_date = db.Column(db.Date, index=True)
    estimated_hours = db.Column(db.Numeric(5, 2))
    actual_hours = db.Column(db.Numeric(5, 2))
    parts_used = db.Column(db.Text)
    labor_cost = db.Column(db.Numeric(10, 2))
    parts_cost = db.Column(db.Numeric(10, 2))
    total_cost = db.Column(db.Numeric(10, 2))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    asset = db.relationship('Asset', backref='work_orders')
    opened_by = db.relationship('Staff', foreign_keys=[opened_by_id], backref='opened_work_orders')
    assigned_to_staff = db.relationship('Staff', foreign_keys=[assigned_to], backref='assigned_work_orders')

    def __init__(self, **kwargs):
        super(WorkOrder, self).__init__(**kwargs)
        if not self.work_order_no:
            self.work_order_no = self.generate_work_order_no()

    @property
    def is_open(self):
        """Check if work order is open"""
        return self.status == 'open'

    @property
    def is_assigned(self):
        """Check if work order is assigned"""
        return self.status == 'assigned'

    @property
    def is_in_progress(self):
        """Check if work order is in progress"""
        return self.status == 'in_progress'

    @property
    def is_completed(self):
        """Check if work order is completed"""
        return self.status == 'completed'

    @property
    def is_cancelled(self):
        """Check if work order is cancelled"""
        return self.status == 'cancelled'

    @property
    def is_critical(self):
        """Check if work order is critical priority"""
        return self.priority == 'critical'

    @property
    def is_high_priority(self):
        """Check if work order is high or critical priority"""
        return self.priority in ['high', 'critical']

    @property
    def is_emergency(self):
        """Check if work order is emergency category"""
        return self.category == 'emergency'

    @property
    def is_overdue(self):
        """Check if work order is overdue"""
        if self.scheduled_date and self.status not in ['completed', 'cancelled']:
            return self.scheduled_date < datetime.now().date()
        return False

    @property
    def age_days(self):
        """Get work order age in days"""
        if self.requested_date:
            return (datetime.now().date() - self.requested_date).days
        return 0

    @property
    def duration_hours(self):
        """Calculate actual duration in hours"""
        if self.actual_hours:
            return float(self.actual_hours)
        return None

    @property
    def total_cost_calculated(self):
        """Calculate total cost"""
        labor = float(self.labor_cost) if self.labor_cost else 0
        parts = float(self.parts_cost) if self.parts_cost else 0
        return labor + parts

    def assign_work_order(self, assigned_to_id, scheduled_date=None):
        """Assign work order to staff member"""
        self.assigned_to = assigned_to_id
        self.status = 'assigned'
        if scheduled_date:
            self.scheduled_date = scheduled_date

    def start_work(self):
        """Start work on the order"""
        self.status = 'in_progress'
        self.started_date = datetime.now().date()

    def complete_work(self, actual_hours=None, parts_used=None, notes=None):
        """Complete the work order"""
        self.status = 'completed'
        self.completed_date = datetime.now().date()
        if actual_hours:
            self.actual_hours = actual_hours
        if parts_used:
            self.parts_used = parts_used
        if notes:
            self.notes = notes
        self.total_cost = self.total_cost_calculated

    def cancel_work_order(self):
        """Cancel the work order"""
        self.status = 'cancelled'

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'work_order_no': self.work_order_no,
            'title': self.title,
            'description': self.description,
            'asset_id': self.asset_id,
            'asset_name': self.asset.name if self.asset else None,
            'category': self.category,
            'priority': self.priority,
            'status': self.status,
            'opened_by_id': self.opened_by_id,
            'opened_by_name': self.opened_by.name if self.opened_by else None,
            'assigned_to': self.assigned_to,
            'assigned_to_name': self.assigned_to_staff.name if self.assigned_to_staff else None,
            'location': self.location,
            'requested_date': self.requested_date.isoformat() if self.requested_date else None,
            'scheduled_date': self.scheduled_date.isoformat() if self.scheduled_date else None,
            'started_date': self.started_date.isoformat() if self.started_date else None,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None,
            'estimated_hours': float(self.estimated_hours) if self.estimated_hours else None,
            'actual_hours': float(self.actual_hours) if self.actual_hours else None,
            'parts_used': self.parts_used,
            'labor_cost': float(self.labor_cost) if self.labor_cost else None,
            'parts_cost': float(self.parts_cost) if self.parts_cost else None,
            'total_cost': float(self.total_cost) if self.total_cost else None,
            'notes': self.notes,
            'is_open': self.is_open,
            'is_assigned': self.is_assigned,
            'is_in_progress': self.is_in_progress,
            'is_completed': self.is_completed,
            'is_cancelled': self.is_cancelled,
            'is_critical': self.is_critical,
            'is_high_priority': self.is_high_priority,
            'is_emergency': self.is_emergency,
            'is_overdue': self.is_overdue,
            'age_days': self.age_days,
            'duration_hours': self.duration_hours,
            'total_cost_calculated': self.total_cost_calculated,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<WorkOrder {self.work_order_no}: {self.title} ({self.status})>'

    @classmethod
    def generate_work_order_no(cls):
        """Generate a unique work order number"""
        import random
        import string

        while True:
            # Generate work order number in format: WO-YYYYMMDD-XXXXX
            date_str = datetime.now().strftime('%Y%m%d')
            digits = ''.join(random.choices(string.digits, k=5))
            work_order_no = f"WO-{date_str}-{digits}"

            # Check if work order number already exists
            if not cls.query.filter_by(work_order_no=work_order_no).first():
                return work_order_no

    @classmethod
    def get_open_work_orders(cls):
        """Get all open work orders"""
        return cls.query.filter_by(status='open').order_by(cls.priority.desc(), cls.requested_date).all()

    @classmethod
    def get_assigned_work_orders(cls, staff_id=None):
        """Get assigned work orders"""
        query = cls.query.filter_by(status='assigned')
        if staff_id:
            query = query.filter_by(assigned_to=staff_id)
        return query.order_by(cls.priority.desc(), cls.scheduled_date).all()

    @classmethod
    def get_in_progress_work_orders(cls, staff_id=None):
        """Get work orders in progress"""
        query = cls.query.filter_by(status='in_progress')
        if staff_id:
            query = query.filter_by(assigned_to=staff_id)
        return query.order_by(cls.priority.desc(), cls.started_date).all()

    @classmethod
    def get_overdue_work_orders(cls):
        """Get overdue work orders"""
        return [wo for wo in cls.query.filter(
            cls.status.in_(['open', 'assigned', 'in_progress'])
        ).all() if wo.is_overdue]

    @classmethod
    def get_emergency_work_orders(cls):
        """Get emergency work orders"""
        return cls.query.filter_by(category='emergency').order_by(cls.requested_date).all()

    @classmethod
    def get_critical_work_orders(cls):
        """Get critical priority work orders"""
        return cls.query.filter_by(priority='critical').order_by(cls.requested_date).all()

    @classmethod
    def get_work_orders_by_category(cls, category, limit=50):
        """Get work orders by category"""
        return cls.query.filter_by(category=category)\
                       .order_by(cls.requested_date.desc())\
                       .limit(limit).all()

    @classmethod
    def get_work_orders_by_asset(cls, asset_id, limit=20):
        """Get work orders for a specific asset"""
        return cls.query.filter_by(asset_id=asset_id)\
                       .order_by(cls.requested_date.desc())\
                       .limit(limit).all()

    @classmethod
    def get_recently_completed_work_orders(cls, days=30):
        """Get recently completed work orders"""
        cutoff_date = datetime.now().date() - timedelta(days=days)
        return cls.query.filter(
            cls.status == 'completed',
            cls.completed_date >= cutoff_date
        ).order_by(cls.completed_date.desc()).all()

    @classmethod
    def get_work_order_statistics(cls):
        """Get work order statistics"""
        total_work_orders = cls.query.count()
        open_work_orders = cls.query.filter_by(status='open').count()
        assigned_work_orders = cls.query.filter_by(status='assigned').count()
        in_progress_work_orders = cls.query.filter_by(status='in_progress').count()
        completed_work_orders = cls.query.filter_by(status='completed').count()
        cancelled_work_orders = cls.query.filter_by(status='cancelled').count()
        
        critical_work_orders = cls.query.filter_by(priority='critical').count()
        emergency_work_orders = cls.query.filter_by(category='emergency').count()
        overdue_work_orders = len(cls.get_overdue_work_orders())
        
        return {
            'total_work_orders': total_work_orders,
            'open_work_orders': open_work_orders,
            'assigned_work_orders': assigned_work_orders,
            'in_progress_work_orders': in_progress_work_orders,
            'completed_work_orders': completed_work_orders,
            'cancelled_work_orders': cancelled_work_orders,
            'critical_work_orders': critical_work_orders,
            'emergency_work_orders': emergency_work_orders,
            'overdue_work_orders': overdue_work_orders
        }
