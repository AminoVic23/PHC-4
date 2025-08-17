"""
Pharmacy models for drug management, prescriptions, and inventory
"""
from datetime import datetime, timedelta
from app import db

class Drug(db.Model):
    """Drug model for medication information"""
    __tablename__ = 'drugs'

    id = db.Column(db.Integer, primary_key=True)
    atc_code = db.Column(db.String(20), index=True)  # Anatomical Therapeutic Chemical code
    name = db.Column(db.String(200), nullable=False, index=True)
    generic_name = db.Column(db.String(200), index=True)
    strength = db.Column(db.String(50))
    form = db.Column(db.String(50))  # tablet, capsule, syrup, injection, etc.
    pack_size = db.Column(db.String(50))
    manufacturer = db.Column(db.String(200))
    active_ingredient = db.Column(db.String(200))
    therapeutic_class = db.Column(db.String(100))
    storage_conditions = db.Column(db.String(100))
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    prescription_items = db.relationship('PrescriptionItem', backref='drug', lazy='dynamic')
    inventory_items = db.relationship('Inventory', backref='drug', lazy='dynamic')
    stock_moves = db.relationship('StockMove', backref='drug', lazy='dynamic')

    def __init__(self, **kwargs):
        super(Drug, self).__init__(**kwargs)

    @property
    def full_name(self):
        """Get drug's full name with strength and form"""
        parts = [self.name]
        if self.strength:
            parts.append(self.strength)
        if self.form:
            parts.append(self.form)
        return ' '.join(parts)

    @property
    def total_stock(self):
        """Get total stock across all locations"""
        return sum(item.on_hand for item in self.inventory_items)

    @property
    def is_low_stock(self):
        """Check if drug is low in stock"""
        return self.total_stock <= self.get_lowest_reorder_level()

    def get_lowest_reorder_level(self):
        """Get the lowest reorder level across all inventory items"""
        min_level = float('inf')
        for item in self.inventory_items:
            if item.reorder_level and item.reorder_level < min_level:
                min_level = item.reorder_level
        return min_level if min_level != float('inf') else 0

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'atc_code': self.atc_code,
            'name': self.name,
            'generic_name': self.generic_name,
            'full_name': self.full_name,
            'strength': self.strength,
            'form': self.form,
            'pack_size': self.pack_size,
            'manufacturer': self.manufacturer,
            'active_ingredient': self.active_ingredient,
            'therapeutic_class': self.therapeutic_class,
            'storage_conditions': self.storage_conditions,
            'active': self.active,
            'total_stock': self.total_stock,
            'is_low_stock': self.is_low_stock,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<Drug {self.full_name}>'

    @classmethod
    def find_by_name(cls, name):
        """Find drug by name"""
        return cls.query.filter_by(name=name, active=True).first()

    @classmethod
    def search_drugs(cls, query, limit=20):
        """Search drugs by name or generic name"""
        search_term = f"%{query}%"
        return cls.query.filter(
            db.or_(
                cls.name.ilike(search_term),
                cls.generic_name.ilike(search_term)
            ),
            cls.active == True
        ).limit(limit).all()

    @classmethod
    def get_active_drugs(cls):
        """Get all active drugs"""
        return cls.query.filter_by(active=True).order_by(cls.name).all()

    @classmethod
    def get_low_stock_drugs(cls):
        """Get drugs with low stock"""
        return [drug for drug in cls.get_active_drugs() if drug.is_low_stock]

class Prescription(db.Model):
    """Prescription model for medication orders"""
    __tablename__ = 'prescriptions'

    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=False, index=True)
    prescriber_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False, index=True)
    prescription_no = db.Column(db.String(20), unique=True, nullable=False, index=True)
    prescription_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    status = db.Column(db.String(20), default='active', nullable=False, index=True)  # active, dispensed, cancelled
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    dispensed_at = db.Column(db.DateTime)

    # Relationships
    visit = db.relationship('Visit', backref='prescriptions')
    prescriber = db.relationship('Staff', backref='prescriptions')
    items = db.relationship('PrescriptionItem', backref='prescription', lazy='dynamic', cascade='all, delete-orphan')

    def __init__(self, **kwargs):
        super(Prescription, self).__init__(**kwargs)
        if not self.prescription_no:
            self.prescription_no = self.generate_prescription_no()

    @property
    def is_active(self):
        """Check if prescription is active"""
        return self.status == 'active'

    @property
    def is_dispensed(self):
        """Check if prescription is dispensed"""
        return self.status == 'dispensed'

    @property
    def total_items(self):
        """Get total number of items in prescription"""
        return self.items.count()

    def dispense(self):
        """Mark prescription as dispensed"""
        self.status = 'dispensed'
        self.dispensed_at = datetime.utcnow()

    def cancel(self):
        """Cancel prescription"""
        self.status = 'cancelled'

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'visit_id': self.visit_id,
            'visit_no': self.visit.visit_no if self.visit else None,
            'prescriber_id': self.prescriber_id,
            'prescriber_name': self.prescriber.name if self.prescriber else None,
            'prescription_no': self.prescription_no,
            'prescription_date': self.prescription_date.isoformat() if self.prescription_date else None,
            'status': self.status,
            'notes': self.notes,
            'is_active': self.is_active,
            'is_dispensed': self.is_dispensed,
            'total_items': self.total_items,
            'items': [item.to_dict() for item in self.items],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'dispensed_at': self.dispensed_at.isoformat() if self.dispensed_at else None
        }

    def __repr__(self):
        return f'<Prescription {self.prescription_no}: {self.status}>'

    @classmethod
    def generate_prescription_no(cls):
        """Generate a unique prescription number"""
        import random
        import string

        while True:
            # Generate prescription number in format: RX-YYYYMMDD-XXXXX
            date_str = datetime.now().strftime('%Y%m%d')
            digits = ''.join(random.choices(string.digits, k=5))
            prescription_no = f"RX-{date_str}-{digits}"

            # Check if prescription number already exists
            if not cls.query.filter_by(prescription_no=prescription_no).first():
                return prescription_no

    @classmethod
    def get_active_prescriptions(cls):
        """Get all active prescriptions"""
        return cls.query.filter_by(status='active').order_by(cls.created_at.desc()).all()

    @classmethod
    def get_visit_prescriptions(cls, visit_id):
        """Get all prescriptions for a visit"""
        return cls.query.filter_by(visit_id=visit_id).order_by(cls.created_at.desc()).all()

    @classmethod
    def get_prescriber_prescriptions(cls, prescriber_id, limit=20):
        """Get recent prescriptions by a prescriber"""
        return cls.query.filter_by(prescriber_id=prescriber_id)\
                       .order_by(cls.created_at.desc())\
                       .limit(limit).all()

class PrescriptionItem(db.Model):
    """Prescription item model for individual medications in a prescription"""
    __tablename__ = 'prescription_items'

    id = db.Column(db.Integer, primary_key=True)
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescriptions.id'), nullable=False, index=True)
    drug_id = db.Column(db.Integer, db.ForeignKey('drugs.id'), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False)
    dosage = db.Column(db.String(100))  # e.g., "1 tablet"
    frequency = db.Column(db.String(100))  # e.g., "twice daily"
    duration = db.Column(db.String(100))  # e.g., "7 days"
    instructions = db.Column(db.Text)
    dispensed_quantity = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    prescription = db.relationship('Prescription', backref='prescription_items')
    drug = db.relationship('Drug', backref='prescription_items')

    def __init__(self, **kwargs):
        super(PrescriptionItem, self).__init__(**kwargs)

    @property
    def remaining_quantity(self):
        """Get remaining quantity to be dispensed"""
        return self.quantity - self.dispensed_quantity

    @property
    def is_fully_dispensed(self):
        """Check if item is fully dispensed"""
        return self.dispensed_quantity >= self.quantity

    def dispense_quantity(self, quantity):
        """Dispense a quantity of this item"""
        if quantity <= self.remaining_quantity:
            self.dispensed_quantity += quantity
            return True
        return False

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'prescription_id': self.prescription_id,
            'drug_id': self.drug_id,
            'drug_name': self.drug.full_name if self.drug else None,
            'quantity': self.quantity,
            'dosage': self.dosage,
            'frequency': self.frequency,
            'duration': self.duration,
            'instructions': self.instructions,
            'dispensed_quantity': self.dispensed_quantity,
            'remaining_quantity': self.remaining_quantity,
            'is_fully_dispensed': self.is_fully_dispensed,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<PrescriptionItem {self.drug.name if self.drug else "Unknown"}: {self.quantity}>'

class Inventory(db.Model):
    """Inventory model for drug stock management"""
    __tablename__ = 'inventory'

    id = db.Column(db.Integer, primary_key=True)
    drug_id = db.Column(db.Integer, db.ForeignKey('drugs.id'), nullable=False, index=True)
    location = db.Column(db.String(100), nullable=False, index=True)  # Main Pharmacy, Ward A, etc.
    batch_no = db.Column(db.String(50), nullable=False, index=True)
    expiry_date = db.Column(db.Date, nullable=False, index=True)
    on_hand = db.Column(db.Integer, default=0, nullable=False)
    reorder_level = db.Column(db.Integer, default=0)
    reorder_quantity = db.Column(db.Integer, default=0)
    unit_cost = db.Column(db.Numeric(10, 2))
    supplier = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    drug = db.relationship('Drug', backref='inventory_items')
    stock_moves = db.relationship('StockMove', backref='inventory_item', lazy='dynamic')

    def __init__(self, **kwargs):
        super(Inventory, self).__init__(**kwargs)

    @property
    def is_low_stock(self):
        """Check if inventory is low"""
        return self.on_hand <= self.reorder_level

    @property
    def is_expired(self):
        """Check if inventory is expired"""
        return self.expiry_date < datetime.now().date()

    @property
    def is_expiring_soon(self):
        """Check if inventory is expiring within 30 days"""
        return self.expiry_date <= (datetime.now().date() + timedelta(days=30))

    def add_stock(self, quantity, move_type='in', reference=None):
        """Add stock to inventory"""
        if move_type == 'in':
            self.on_hand += quantity
        elif move_type == 'out':
            if self.on_hand >= quantity:
                self.on_hand -= quantity
            else:
                raise ValueError("Insufficient stock")
        elif move_type == 'adjust':
            self.on_hand = quantity

        # Create stock move record
        stock_move = StockMove(
            inventory_id=self.id,
            move_type=move_type,
            quantity=quantity,
            reference=reference
        )
        return stock_move

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'drug_id': self.drug_id,
            'drug_name': self.drug.full_name if self.drug else None,
            'location': self.location,
            'batch_no': self.batch_no,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'on_hand': self.on_hand,
            'reorder_level': self.reorder_level,
            'reorder_quantity': self.reorder_quantity,
            'unit_cost': float(self.unit_cost) if self.unit_cost else None,
            'supplier': self.supplier,
            'is_low_stock': self.is_low_stock,
            'is_expired': self.is_expired,
            'is_expiring_soon': self.is_expiring_soon,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<Inventory {self.drug.name if self.drug else "Unknown"}: {self.on_hand} at {self.location}>'

    @classmethod
    def get_low_stock_items(cls):
        """Get all low stock items"""
        return cls.query.filter(cls.on_hand <= cls.reorder_level).all()

    @classmethod
    def get_expired_items(cls):
        """Get all expired items"""
        return cls.query.filter(cls.expiry_date < datetime.now().date()).all()

    @classmethod
    def get_expiring_soon_items(cls):
        """Get items expiring within 30 days"""
        expiry_date = datetime.now().date() + timedelta(days=30)
        return cls.query.filter(cls.expiry_date <= expiry_date).all()

    @classmethod
    def get_drug_inventory(cls, drug_id):
        """Get all inventory items for a drug"""
        return cls.query.filter_by(drug_id=drug_id).all()

class StockMove(db.Model):
    """Stock move model for tracking inventory transactions"""
    __tablename__ = 'stock_moves'

    id = db.Column(db.Integer, primary_key=True)
    inventory_id = db.Column(db.Integer, db.ForeignKey('inventory.id'), nullable=False, index=True)
    drug_id = db.Column(db.Integer, db.ForeignKey('drugs.id'), nullable=False, index=True)
    move_type = db.Column(db.String(20), nullable=False, index=True)  # in, out, adjust
    quantity = db.Column(db.Integer, nullable=False)
    reference = db.Column(db.String(100))  # prescription_no, purchase_order, etc.
    reference_id = db.Column(db.Integer)  # ID of the reference document
    notes = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relationships
    inventory_item = db.relationship('Inventory', backref='stock_moves')
    drug = db.relationship('Drug', backref='stock_moves')
    created_by = db.relationship('Staff', backref='stock_moves')

    def __init__(self, **kwargs):
        super(StockMove, self).__init__(**kwargs)

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'inventory_id': self.inventory_id,
            'drug_id': self.drug_id,
            'drug_name': self.drug.full_name if self.drug else None,
            'move_type': self.move_type,
            'quantity': self.quantity,
            'reference': self.reference,
            'reference_id': self.reference_id,
            'notes': self.notes,
            'created_by_id': self.created_by_id,
            'created_by_name': self.created_by.name if self.created_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<StockMove {self.move_type}: {self.quantity} of {self.drug.name if self.drug else "Unknown"}>'

    @classmethod
    def get_recent_moves(cls, limit=50):
        """Get recent stock moves"""
        return cls.query.order_by(cls.created_at.desc()).limit(limit).all()

    @classmethod
    def get_drug_moves(cls, drug_id, limit=50):
        """Get stock moves for a specific drug"""
        return cls.query.filter_by(drug_id=drug_id)\
                       .order_by(cls.created_at.desc())\
                       .limit(limit).all()

    @classmethod
    def get_moves_by_type(cls, move_type, limit=50):
        """Get stock moves by type"""
        return cls.query.filter_by(move_type=move_type)\
                       .order_by(cls.created_at.desc())\
                       .limit(limit).all()
