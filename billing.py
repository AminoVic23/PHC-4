"""
Billing models for pricing, invoicing, payments, and insurance
"""
from datetime import datetime, timedelta
from app import db

class PriceList(db.Model):
    """Price list model for service pricing"""
    __tablename__ = 'price_lists'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), index=True)
    service_code = db.Column(db.String(20), nullable=False, index=True)
    service_name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='USD')
    active = db.Column(db.Boolean, default=True, nullable=False)
    effective_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    expiry_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    department = db.relationship('Department', backref='price_lists')
    invoice_items = db.relationship('InvoiceItem', backref='price_list_item', lazy='dynamic')

    def __init__(self, **kwargs):
        super(PriceList, self).__init__(**kwargs)

    @property
    def is_active(self):
        """Check if price list is currently active"""
        today = datetime.now().date()
        if not self.active:
            return False
        if self.effective_date > today:
            return False
        if self.expiry_date and self.expiry_date < today:
            return False
        return True

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'department_id': self.department_id,
            'department_name': self.department.name if self.department else None,
            'service_code': self.service_code,
            'service_name': self.service_name,
            'price': float(self.price) if self.price else None,
            'currency': self.currency,
            'active': self.active,
            'is_active': self.is_active,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<PriceList {self.service_code}: {self.service_name} - {self.price}>'

    @classmethod
    def get_active_prices(cls):
        """Get all active price list items"""
        today = datetime.now().date()
        return cls.query.filter(
            cls.active == True,
            cls.effective_date <= today,
            db.or_(cls.expiry_date == None, cls.expiry_date >= today)
        ).all()

    @classmethod
    def get_department_prices(cls, department_id):
        """Get active prices for a department"""
        today = datetime.now().date()
        return cls.query.filter(
            cls.department_id == department_id,
            cls.active == True,
            cls.effective_date <= today,
            db.or_(cls.expiry_date == None, cls.expiry_date >= today)
        ).all()

    @classmethod
    def find_by_service_code(cls, service_code):
        """Find active price by service code"""
        today = datetime.now().date()
        return cls.query.filter(
            cls.service_code == service_code,
            cls.active == True,
            cls.effective_date <= today,
            db.or_(cls.expiry_date == None, cls.expiry_date >= today)
        ).first()

class Invoice(db.Model):
    """Invoice model for billing"""
    __tablename__ = 'invoices'

    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(20), unique=True, nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), index=True)
    invoice_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='draft', nullable=False, index=True)  # draft, final, paid, cancelled
    subtotal = db.Column(db.Numeric(10, 2), default=0)
    tax_amount = db.Column(db.Numeric(10, 2), default=0)
    discount_amount = db.Column(db.Numeric(10, 2), default=0)
    total_amount = db.Column(db.Numeric(10, 2), default=0)
    currency = db.Column(db.String(3), default='USD')
    notes = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    finalized_at = db.Column(db.DateTime)
    paid_at = db.Column(db.DateTime)

    # Relationships
    patient = db.relationship('Patient', backref='invoices')
    visit = db.relationship('Visit', backref='invoices')
    created_by = db.relationship('Staff', backref='created_invoices')
    items = db.relationship('InvoiceItem', backref='invoice', lazy='dynamic', cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='invoice', lazy='dynamic')
    claims = db.relationship('Claim', backref='invoice', lazy='dynamic')

    def __init__(self, **kwargs):
        super(Invoice, self).__init__(**kwargs)
        if not self.invoice_no:
            self.invoice_no = self.generate_invoice_no()
        if not self.due_date:
            self.due_date = datetime.now().date() + timedelta(days=30)

    @property
    def is_draft(self):
        """Check if invoice is in draft status"""
        return self.status == 'draft'

    @property
    def is_final(self):
        """Check if invoice is finalized"""
        return self.status in ['final', 'paid']

    @property
    def is_paid(self):
        """Check if invoice is paid"""
        return self.status == 'paid'

    @property
    def is_overdue(self):
        """Check if invoice is overdue"""
        return self.due_date < datetime.now().date() and self.status != 'paid'

    @property
    def paid_amount(self):
        """Get total amount paid"""
        return sum(payment.amount for payment in self.payments)

    @property
    def balance_due(self):
        """Get remaining balance"""
        return self.total_amount - self.paid_amount

    def calculate_totals(self):
        """Calculate invoice totals"""
        self.subtotal = sum(item.total_amount for item in self.items)
        # Add tax calculation logic here if needed
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount

    def finalize(self):
        """Finalize the invoice"""
        self.calculate_totals()
        self.status = 'final'
        self.finalized_at = datetime.utcnow()

    def mark_paid(self):
        """Mark invoice as paid"""
        self.status = 'paid'
        self.paid_at = datetime.utcnow()

    def cancel(self):
        """Cancel the invoice"""
        self.status = 'cancelled'

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'invoice_no': self.invoice_no,
            'patient_id': self.patient_id,
            'patient_name': self.patient.full_name if self.patient else None,
            'visit_id': self.visit_id,
            'visit_no': self.visit.visit_no if self.visit else None,
            'invoice_date': self.invoice_date.isoformat() if self.invoice_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'status': self.status,
            'subtotal': float(self.subtotal) if self.subtotal else None,
            'tax_amount': float(self.tax_amount) if self.tax_amount else None,
            'discount_amount': float(self.discount_amount) if self.discount_amount else None,
            'total_amount': float(self.total_amount) if self.total_amount else None,
            'currency': self.currency,
            'notes': self.notes,
            'is_draft': self.is_draft,
            'is_final': self.is_final,
            'is_paid': self.is_paid,
            'is_overdue': self.is_overdue,
            'paid_amount': float(self.paid_amount),
            'balance_due': float(self.balance_due),
            'items': [item.to_dict() for item in self.items],
            'payments': [payment.to_dict() for payment in self.payments],
            'created_by_name': self.created_by.name if self.created_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'finalized_at': self.finalized_at.isoformat() if self.finalized_at else None,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None
        }

    def __repr__(self):
        return f'<Invoice {self.invoice_no}: {self.total_amount} ({self.status})>'

    @classmethod
    def generate_invoice_no(cls):
        """Generate a unique invoice number"""
        import random
        import string

        while True:
            # Generate invoice number in format: INV-YYYYMMDD-XXXXX
            date_str = datetime.now().strftime('%Y%m%d')
            digits = ''.join(random.choices(string.digits, k=5))
            invoice_no = f"INV-{date_str}-{digits}"

            # Check if invoice number already exists
            if not cls.query.filter_by(invoice_no=invoice_no).first():
                return invoice_no

    @classmethod
    def get_pending_invoices(cls):
        """Get pending invoices (final but not paid)"""
        return cls.query.filter_by(status='final').order_by(cls.due_date).all()

    @classmethod
    def get_overdue_invoices(cls):
        """Get overdue invoices"""
        today = datetime.now().date()
        return cls.query.filter(
            cls.due_date < today,
            cls.status.in_(['draft', 'final'])
        ).order_by(cls.due_date).all()

    @classmethod
    def get_patient_invoices(cls, patient_id, limit=20):
        """Get recent invoices for a patient"""
        return cls.query.filter_by(patient_id=patient_id)\
                       .order_by(cls.created_at.desc())\
                       .limit(limit).all()

class InvoiceItem(db.Model):
    """Invoice item model for individual line items"""
    __tablename__ = 'invoice_items'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False, index=True)
    price_list_id = db.Column(db.Integer, db.ForeignKey('price_lists.id'), index=True)
    service_code = db.Column(db.String(20), nullable=False)
    service_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    discount_percent = db.Column(db.Numeric(5, 2), default=0)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    invoice = db.relationship('Invoice', backref='invoice_items')
    price_list_item = db.relationship('PriceList', backref='invoice_items')

    def __init__(self, **kwargs):
        super(InvoiceItem, self).__init__(**kwargs)
        if not self.total_amount:
            self.calculate_total()

    def calculate_total(self):
        """Calculate total amount for this item"""
        subtotal = self.unit_price * self.quantity
        discount = subtotal * (self.discount_percent / 100)
        self.total_amount = subtotal - discount

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'price_list_id': self.price_list_id,
            'service_code': self.service_code,
            'service_name': self.service_name,
            'quantity': self.quantity,
            'unit_price': float(self.unit_price) if self.unit_price else None,
            'discount_percent': float(self.discount_percent) if self.discount_percent else None,
            'total_amount': float(self.total_amount) if self.total_amount else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<InvoiceItem {self.service_code}: {self.quantity} x {self.unit_price}>'

class Payment(db.Model):
    """Payment model for tracking payments"""
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False, index=True)
    payment_no = db.Column(db.String(20), unique=True, nullable=False, index=True)
    payment_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False, index=True)  # cash, card, bank_transfer, insurance
    reference_no = db.Column(db.String(100))  # transaction reference
    currency = db.Column(db.String(3), default='USD')
    notes = db.Column(db.Text)
    cashier_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    invoice = db.relationship('Invoice', backref='payments')
    cashier = db.relationship('Staff', backref='processed_payments')

    def __init__(self, **kwargs):
        super(Payment, self).__init__(**kwargs)
        if not self.payment_no:
            self.payment_no = self.generate_payment_no()

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'invoice_no': self.invoice.invoice_no if self.invoice else None,
            'payment_no': self.payment_no,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'amount': float(self.amount) if self.amount else None,
            'payment_method': self.payment_method,
            'reference_no': self.reference_no,
            'currency': self.currency,
            'notes': self.notes,
            'cashier_id': self.cashier_id,
            'cashier_name': self.cashier.name if self.cashier else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<Payment {self.payment_no}: {self.amount} ({self.payment_method})>'

    @classmethod
    def generate_payment_no(cls):
        """Generate a unique payment number"""
        import random
        import string

        while True:
            # Generate payment number in format: PAY-YYYYMMDD-XXXXX
            date_str = datetime.now().strftime('%Y%m%d')
            digits = ''.join(random.choices(string.digits, k=5))
            payment_no = f"PAY-{date_str}-{digits}"

            # Check if payment number already exists
            if not cls.query.filter_by(payment_no=payment_no).first():
                return payment_no

    @classmethod
    def get_today_payments(cls):
        """Get today's payments"""
        today = datetime.now().date()
        return cls.query.filter_by(payment_date=today).order_by(cls.created_at.desc()).all()

    @classmethod
    def get_payments_by_method(cls, payment_method, limit=50):
        """Get payments by method"""
        return cls.query.filter_by(payment_method=payment_method)\
                       .order_by(cls.created_at.desc())\
                       .limit(limit).all()

class InsurancePolicy(db.Model):
    """Insurance policy model"""
    __tablename__ = 'insurance_policies'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)
    policy_number = db.Column(db.String(50), nullable=False, index=True)
    insurance_company = db.Column(db.String(200), nullable=False)
    policy_type = db.Column(db.String(50))  # individual, family, group
    coverage_type = db.Column(db.String(50))  # comprehensive, basic, etc.
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    premium_amount = db.Column(db.Numeric(10, 2))
    coverage_limit = db.Column(db.Numeric(10, 2))
    copay_percent = db.Column(db.Numeric(5, 2), default=0)
    deductible_amount = db.Column(db.Numeric(10, 2), default=0)
    active = db.Column(db.Boolean, default=True, nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    patient = db.relationship('Patient', backref='insurance_policies')
    claims = db.relationship('Claim', backref='insurance_policy', lazy='dynamic')

    def __init__(self, **kwargs):
        super(InsurancePolicy, self).__init__(**kwargs)

    @property
    def is_active(self):
        """Check if policy is currently active"""
        today = datetime.now().date()
        if not self.active:
            return False
        if self.start_date > today:
            return False
        if self.end_date and self.end_date < today:
            return False
        return True

    def calculate_coverage(self, invoice_amount):
        """Calculate insurance coverage for an invoice amount"""
        if not self.is_active:
            return 0

        # Apply deductible
        remaining_amount = max(0, invoice_amount - self.deductible_amount)
        
        # Apply coverage percentage
        covered_amount = remaining_amount * (1 - self.copay_percent / 100)
        
        # Apply coverage limit
        if self.coverage_limit:
            covered_amount = min(covered_amount, self.coverage_limit)
        
        return covered_amount

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'patient_name': self.patient.full_name if self.patient else None,
            'policy_number': self.policy_number,
            'insurance_company': self.insurance_company,
            'policy_type': self.policy_type,
            'coverage_type': self.coverage_type,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'premium_amount': float(self.premium_amount) if self.premium_amount else None,
            'coverage_limit': float(self.coverage_limit) if self.coverage_limit else None,
            'copay_percent': float(self.copay_percent) if self.copay_percent else None,
            'deductible_amount': float(self.deductible_amount) if self.deductible_amount else None,
            'active': self.active,
            'is_active': self.is_active,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<InsurancePolicy {self.policy_number}: {self.insurance_company}>'

    @classmethod
    def get_active_policies(cls):
        """Get all active insurance policies"""
        today = datetime.now().date()
        return cls.query.filter(
            cls.active == True,
            cls.start_date <= today,
            db.or_(cls.end_date == None, cls.end_date >= today)
        ).all()

    @classmethod
    def get_patient_policies(cls, patient_id):
        """Get all policies for a patient"""
        return cls.query.filter_by(patient_id=patient_id).order_by(cls.start_date.desc()).all()

class Claim(db.Model):
    """Insurance claim model"""
    __tablename__ = 'claims'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False, index=True)
    insurance_policy_id = db.Column(db.Integer, db.ForeignKey('insurance_policies.id'), nullable=False, index=True)
    claim_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    claim_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    status = db.Column(db.String(20), default='submitted', nullable=False, index=True)  # submitted, approved, rejected, paid
    claim_amount = db.Column(db.Numeric(10, 2), nullable=False)
    approved_amount = db.Column(db.Numeric(10, 2))
    rejection_reason = db.Column(db.Text)
    submitted_by_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = db.Column(db.DateTime)

    # Relationships
    invoice = db.relationship('Invoice', backref='claims')
    insurance_policy = db.relationship('InsurancePolicy', backref='claims')
    submitted_by = db.relationship('Staff', backref='submitted_claims')

    def __init__(self, **kwargs):
        super(Claim, self).__init__(**kwargs)
        if not self.claim_number:
            self.claim_number = self.generate_claim_number()

    @property
    def is_submitted(self):
        """Check if claim is submitted"""
        return self.status == 'submitted'

    @property
    def is_approved(self):
        """Check if claim is approved"""
        return self.status == 'approved'

    @property
    def is_rejected(self):
        """Check if claim is rejected"""
        return self.status == 'rejected'

    @property
    def is_paid(self):
        """Check if claim is paid"""
        return self.status == 'paid'

    def approve(self, approved_amount):
        """Approve the claim"""
        self.status = 'approved'
        self.approved_amount = approved_amount
        self.processed_at = datetime.utcnow()

    def reject(self, rejection_reason):
        """Reject the claim"""
        self.status = 'rejected'
        self.rejection_reason = rejection_reason
        self.processed_at = datetime.utcnow()

    def mark_paid(self):
        """Mark claim as paid"""
        self.status = 'paid'
        self.processed_at = datetime.utcnow()

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'invoice_no': self.invoice.invoice_no if self.invoice else None,
            'insurance_policy_id': self.insurance_policy_id,
            'policy_number': self.insurance_policy.policy_number if self.insurance_policy else None,
            'claim_number': self.claim_number,
            'claim_date': self.claim_date.isoformat() if self.claim_date else None,
            'status': self.status,
            'claim_amount': float(self.claim_amount) if self.claim_amount else None,
            'approved_amount': float(self.approved_amount) if self.approved_amount else None,
            'rejection_reason': self.rejection_reason,
            'is_submitted': self.is_submitted,
            'is_approved': self.is_approved,
            'is_rejected': self.is_rejected,
            'is_paid': self.is_paid,
            'submitted_by_name': self.submitted_by.name if self.submitted_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None
        }

    def __repr__(self):
        return f'<Claim {self.claim_number}: {self.claim_amount} ({self.status})>'

    @classmethod
    def generate_claim_number(cls):
        """Generate a unique claim number"""
        import random
        import string

        while True:
            # Generate claim number in format: CLM-YYYYMMDD-XXXXX
            date_str = datetime.now().strftime('%Y%m%d')
            digits = ''.join(random.choices(string.digits, k=5))
            claim_number = f"CLM-{date_str}-{digits}"

            # Check if claim number already exists
            if not cls.query.filter_by(claim_number=claim_number).first():
                return claim_number

    @classmethod
    def get_pending_claims(cls):
        """Get pending claims (submitted but not processed)"""
        return cls.query.filter_by(status='submitted').order_by(cls.created_at).all()

    @classmethod
    def get_approved_claims(cls):
        """Get approved claims"""
        return cls.query.filter_by(status='approved').order_by(cls.created_at.desc()).all()

    @classmethod
    def get_rejected_claims(cls):
        """Get rejected claims"""
        return cls.query.filter_by(status='rejected').order_by(cls.created_at.desc()).all()
