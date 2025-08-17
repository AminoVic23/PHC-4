"""
Facility management models for multi-facility HIS
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.extensions import db

class Facility(db.Model):
    """Facility model for multi-facility support"""
    __tablename__ = 'facilities'
    
    id = Column(Integer, primary_key=True)
    facility_code = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)  # primary, secondary, tertiary, specialty
    address = Column(Text, nullable=False)
    city = Column(String(50), nullable=False)
    state = Column(String(50), nullable=False)
    country = Column(String(50), nullable=False, default='Country')
    postal_code = Column(String(20))
    phone = Column(String(20))
    email = Column(String(100))
    website = Column(String(200))
    
    # Facility details
    bed_count = Column(Integer, default=0)
    emergency_beds = Column(Integer, default=0)
    icu_beds = Column(Integer, default=0)
    operating_rooms = Column(Integer, default=0)
    
    # Administrative info
    license_number = Column(String(50))
    accreditation = Column(String(100))
    established_date = Column(DateTime)
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    departments = relationship('Department', back_populates='facility')
    staff_facilities = relationship('StaffFacility', back_populates='facility')
    patients = relationship('Patient', back_populates='facility')
    visits = relationship('Visit', back_populates='facility')
    
    def __repr__(self):
        return f'<Facility {self.facility_code}: {self.name}>'
    
    @classmethod
    def get_active_facilities(cls):
        """Get all active facilities"""
        return cls.query.filter(cls.is_active == True).order_by(cls.name).all()
    
    @classmethod
    def get_by_code(cls, facility_code):
        """Get facility by code"""
        return cls.query.filter_by(facility_code=facility_code, is_active=True).first()
    
    @classmethod
    def get_facility_statistics(cls, facility_id=None):
        """Get facility statistics"""
        from app.models import Patient, Visit, Staff
        
        if facility_id:
            facilities = [cls.query.get(facility_id)]
        else:
            facilities = cls.get_active_facilities()
        
        stats = []
        for facility in facilities:
            if not facility:
                continue
                
            patient_count = Patient.query.filter_by(facility_id=facility.id).count()
            staff_count = Staff.query.join(StaffFacility).filter(
                StaffFacility.facility_id == facility.id,
                Staff.is_active == True
            ).count()
            
            # Today's visits
            today = datetime.now().date()
            today_visits = Visit.query.filter(
                Visit.facility_id == facility.id,
                Visit.visit_date == today
            ).count()
            
            stats.append({
                'facility': facility,
                'patient_count': patient_count,
                'staff_count': staff_count,
                'today_visits': today_visits
            })
        
        return stats

class StaffFacility(db.Model):
    """Staff-Facility relationship for multi-facility access"""
    __tablename__ = 'staff_facilities'
    
    id = Column(Integer, primary_key=True)
    staff_id = Column(Integer, ForeignKey('staff.id'), nullable=False)
    facility_id = Column(Integer, ForeignKey('facilities.id'), nullable=False)
    
    # Access permissions for this facility
    can_access = Column(Boolean, default=True)
    can_manage_staff = Column(Boolean, default=False)
    can_manage_facility = Column(Boolean, default=False)
    can_view_reports = Column(Boolean, default=True)
    can_export_data = Column(Boolean, default=False)
    
    # Assignment details
    assigned_date = Column(DateTime, default=datetime.utcnow)
    assigned_by_id = Column(Integer, ForeignKey('staff.id'))
    notes = Column(Text)
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    staff = relationship('Staff', foreign_keys=[staff_id], back_populates='facility_access')
    facility = relationship('Facility', back_populates='staff_facilities')
    assigned_by = relationship('Staff', foreign_keys=[assigned_by_id])
    
    __table_args__ = (
        UniqueConstraint('staff_id', 'facility_id', name='uq_staff_facility'),
    )
    
    def __repr__(self):
        return f'<StaffFacility {self.staff_id}:{self.facility_id}>'
    
    @classmethod
    def get_staff_facilities(cls, staff_id):
        """Get all facilities a staff member has access to"""
        return cls.query.filter(
            cls.staff_id == staff_id,
            cls.can_access == True,
            cls.is_active == True
        ).join(Facility).filter(Facility.is_active == True).all()
    
    @classmethod
    def get_facility_staff(cls, facility_id):
        """Get all staff members with access to a facility"""
        return cls.query.filter(
            cls.facility_id == facility_id,
            cls.can_access == True,
            cls.is_active == True
        ).join(Staff).filter(Staff.is_active == True).all()
    
    @classmethod
    def has_access(cls, staff_id, facility_id):
        """Check if staff has access to facility"""
        return cls.query.filter(
            cls.staff_id == staff_id,
            cls.facility_id == facility_id,
            cls.can_access == True,
            cls.is_active == True
        ).first() is not None
