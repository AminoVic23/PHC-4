#!/usr/bin/env python3
"""
Database seeding script for Primary Healthcare HIS
Populates the database with initial data including roles, permissions, departments, and sample staff.
"""

import os
import sys
from datetime import datetime, date
from werkzeug.security import generate_password_hash

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app, db
from app.models import (
    Role, Permission, Staff, Department, Patient, Visit,
    ClinicalNote, Order, LabResult, RadiologyReport,
    Prescription, Drug, Inventory, Invoice, Payment,
    Referral, QualityIncident, Survey, Asset, WorkOrder,
    Ticket, Shift, LeaveRequest, Document, AuditLog,
    Facility, StaffFacility
)
from app.security import PERMISSIONS, ROLE_PERMISSIONS

def create_roles_and_permissions():
    """Create roles and permissions"""
    print("Creating roles and permissions...")
    
    # Create permissions
    for permission_name in PERMISSIONS:
        permission = Permission.query.filter_by(name=permission_name).first()
        if not permission:
            permission = Permission(name=permission_name)
            db.session.add(permission)
    
    db.session.commit()
    
    # Create roles and assign permissions
    for role_name, permission_list in ROLE_PERMISSIONS.items():
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            role = Role(name=role_name, description=f"{role_name.title()} role")
            db.session.add(role)
            db.session.flush()  # Get the ID
        
        # Assign permissions to role
        for permission_name in permission_list:
            permission = Permission.query.filter_by(name=permission_name).first()
            if permission and permission not in role.permissions:
                role.permissions.append(permission)
    
    db.session.commit()
    print("Roles and permissions created successfully!")

def create_facilities():
    """Create facilities"""
    print("Creating facilities...")

    facilities_data = [
        {
            'facility_code': 'PHC001',
            'name': 'Primary Healthcare Center - Main',
            'type': 'primary',
            'address': '123 Healthcare Avenue',
            'city': 'Healthcare City',
            'state': 'Health State',
            'country': 'Health Country',
            'postal_code': '12345',
            'phone': '+1234567890',
            'email': 'main@phc.com',
            'website': 'www.phc.com',
            'bed_count': 50,
            'emergency_beds': 10,
            'icu_beds': 5,
            'operating_rooms': 2,
            'license_number': 'LIC001',
            'accreditation': 'JCI Accredited',
            'established_date': date(2020, 1, 1)
        },
        {
            'facility_code': 'PHC002',
            'name': 'Primary Healthcare Center - North',
            'type': 'primary',
            'address': '456 North Street',
            'city': 'North City',
            'state': 'Health State',
            'country': 'Health Country',
            'postal_code': '12346',
            'phone': '+1234567891',
            'email': 'north@phc.com',
            'website': 'www.phc-north.com',
            'bed_count': 30,
            'emergency_beds': 8,
            'icu_beds': 3,
            'operating_rooms': 1,
            'license_number': 'LIC002',
            'accreditation': 'JCI Accredited',
            'established_date': date(2021, 3, 15)
        }
    ]

    for facility_data in facilities_data:
        facility = Facility.query.filter_by(facility_code=facility_data['facility_code']).first()
        if not facility:
            facility = Facility(**facility_data)
            db.session.add(facility)

    db.session.commit()
    print("Facilities created successfully!")

def create_departments():
    """Create departments"""
    print("Creating departments...")

    # Get facilities
    main_facility = Facility.query.filter_by(facility_code='PHC001').first()
    north_facility = Facility.query.filter_by(facility_code='PHC002').first()

    departments_data = [
        # Main facility departments
        {'name': 'Registration', 'type': 'administrative', 'location': 'Ground Floor', 'facility_id': main_facility.id if main_facility else 1},
        {'name': 'Physician Clinic A', 'type': 'clinical', 'location': 'First Floor', 'facility_id': main_facility.id if main_facility else 1},
        {'name': 'Physician Clinic B', 'type': 'clinical', 'location': 'First Floor', 'facility_id': main_facility.id if main_facility else 1},
        {'name': 'Dental Clinic', 'type': 'clinical', 'location': 'Second Floor', 'facility_id': main_facility.id if main_facility else 1},
        {'name': 'Emergency Department', 'type': 'emergency', 'location': 'Ground Floor', 'facility_id': main_facility.id if main_facility else 1},
        {'name': 'Laboratory', 'type': 'laboratory', 'location': 'Ground Floor', 'facility_id': main_facility.id if main_facility else 1},
        {'name': 'Radiology', 'type': 'radiology', 'location': 'Ground Floor', 'facility_id': main_facility.id if main_facility else 1},
        {'name': 'Pharmacy', 'type': 'pharmacy', 'location': 'Ground Floor', 'facility_id': main_facility.id if main_facility else 1},
        {'name': 'Cashier', 'type': 'administrative', 'location': 'Ground Floor', 'facility_id': main_facility.id if main_facility else 1},
        {'name': 'Finance', 'type': 'administrative', 'location': 'Second Floor', 'facility_id': main_facility.id if main_facility else 1},
        {'name': 'Human Resources', 'type': 'administrative', 'location': 'Second Floor', 'facility_id': main_facility.id if main_facility else 1},
        {'name': 'IT Helpdesk', 'type': 'support', 'location': 'Second Floor', 'facility_id': main_facility.id if main_facility else 1},
        {'name': 'Quality Management', 'type': 'administrative', 'location': 'Second Floor', 'facility_id': main_facility.id if main_facility else 1},
        {'name': 'Patient Satisfaction', 'type': 'administrative', 'location': 'Ground Floor', 'facility_id': main_facility.id if main_facility else 1},
        {'name': 'Medical Administration', 'type': 'administrative', 'location': 'Second Floor', 'facility_id': main_facility.id if main_facility else 1},
        {'name': 'Maintenance', 'type': 'support', 'location': 'Ground Floor', 'facility_id': main_facility.id if main_facility else 1},
        {'name': 'Facility Management', 'type': 'administrative', 'location': 'Second Floor', 'facility_id': main_facility.id if main_facility else 1},
        
        # North facility departments
        {'name': 'Registration', 'type': 'administrative', 'location': 'Ground Floor', 'facility_id': north_facility.id if north_facility else 2},
        {'name': 'Physician Clinic', 'type': 'clinical', 'location': 'First Floor', 'facility_id': north_facility.id if north_facility else 2},
        {'name': 'Emergency Department', 'type': 'emergency', 'location': 'Ground Floor', 'facility_id': north_facility.id if north_facility else 2},
        {'name': 'Laboratory', 'type': 'laboratory', 'location': 'Ground Floor', 'facility_id': north_facility.id if north_facility else 2},
        {'name': 'Pharmacy', 'type': 'pharmacy', 'location': 'Ground Floor', 'facility_id': north_facility.id if north_facility else 2},
        {'name': 'Cashier', 'type': 'administrative', 'location': 'Ground Floor', 'facility_id': north_facility.id if north_facility else 2},
        {'name': 'IT Helpdesk', 'type': 'support', 'location': 'Second Floor', 'facility_id': north_facility.id if north_facility else 2},
        {'name': 'Maintenance', 'type': 'support', 'location': 'Ground Floor', 'facility_id': north_facility.id if north_facility else 2}
    ]

    for dept_data in departments_data:
        dept = Department.query.filter_by(
            name=dept_data['name'], 
            facility_id=dept_data['facility_id']
        ).first()
        if not dept:
            dept = Department(**dept_data)
            db.session.add(dept)

    db.session.commit()
    print("Departments created successfully!")

def create_sample_staff():
    """Create sample staff members"""
    print("Creating sample staff...")
    
    # Get facilities
    main_facility = Facility.query.filter_by(facility_code='PHC001').first()
    north_facility = Facility.query.filter_by(facility_code='PHC002').first()
    
    # Get roles
    superadmin_role = Role.query.filter_by(name='superadmin').first()
    facility_head_role = Role.query.filter_by(name='facility_head').first()
    physician_role = Role.query.filter_by(name='physician').first()
    registration_role = Role.query.filter_by(name='registration').first()
    laboratory_role = Role.query.filter_by(name='laboratory').first()
    pharmacy_role = Role.query.filter_by(name='pharmacy').first()
    cashier_role = Role.query.filter_by(name='cashier').first()
    hr_role = Role.query.filter_by(name='hr').first()
    helpdesk_role = Role.query.filter_by(name='helpdesk').first()
    quality_role = Role.query.filter_by(name='quality').first()
    satisfaction_role = Role.query.filter_by(name='satisfaction').first()
    medical_admin_role = Role.query.filter_by(name='medical_admin').first()
    maintenance_role = Role.query.filter_by(name='maintenance').first()
    
    # Get departments by facility
    registration_dept_main = Department.query.filter_by(name='Registration', facility_id=main_facility.id).first()
    clinic_a_dept = Department.query.filter_by(name='Physician Clinic A', facility_id=main_facility.id).first()
    clinic_b_dept = Department.query.filter_by(name='Physician Clinic B', facility_id=main_facility.id).first()
    dental_dept = Department.query.filter_by(name='Dental Clinic', facility_id=main_facility.id).first()
    lab_dept_main = Department.query.filter_by(name='Laboratory', facility_id=main_facility.id).first()
    radiology_dept = Department.query.filter_by(name='Radiology', facility_id=main_facility.id).first()
    pharmacy_dept_main = Department.query.filter_by(name='Pharmacy', facility_id=main_facility.id).first()
    cashier_dept_main = Department.query.filter_by(name='Cashier', facility_id=main_facility.id).first()
    finance_dept = Department.query.filter_by(name='Finance', facility_id=main_facility.id).first()
    hr_dept = Department.query.filter_by(name='Human Resources', facility_id=main_facility.id).first()
    helpdesk_dept_main = Department.query.filter_by(name='IT Helpdesk', facility_id=main_facility.id).first()
    quality_dept = Department.query.filter_by(name='Quality Management', facility_id=main_facility.id).first()
    satisfaction_dept = Department.query.filter_by(name='Patient Satisfaction', facility_id=main_facility.id).first()
    medical_admin_dept = Department.query.filter_by(name='Medical Administration', facility_id=main_facility.id).first()
    maintenance_dept = Department.query.filter_by(name='Maintenance', facility_id=main_facility.id).first()
    facility_dept = Department.query.filter_by(name='Facility Management', facility_id=main_facility.id).first()
    
    # North facility departments
    registration_dept_north = Department.query.filter_by(name='Registration', facility_id=north_facility.id).first()
    clinic_north = Department.query.filter_by(name='Physician Clinic', facility_id=north_facility.id).first()
    lab_dept_north = Department.query.filter_by(name='Laboratory', facility_id=north_facility.id).first()
    pharmacy_dept_north = Department.query.filter_by(name='Pharmacy', facility_id=north_facility.id).first()
    cashier_dept_north = Department.query.filter_by(name='Cashier', facility_id=north_facility.id).first()
    helpdesk_dept_north = Department.query.filter_by(name='IT Helpdesk', facility_id=north_facility.id).first()
    
    staff_data = [
        {
            'employee_id': 'EMP001',
            'name': 'Dr. John Smith',
            'email': 'john.smith@healthcare.com',
            'phone': '+1234567890',
            'department_id': clinic_a_dept.id if clinic_a_dept else None,
            'role_id': physician_role.id if physician_role else None,
            'position': 'Senior Physician',
            'hire_date': date(2020, 1, 15),
            'is_active': True
        },
        {
            'employee_id': 'EMP002',
            'name': 'Dr. Sarah Johnson',
            'email': 'sarah.johnson@healthcare.com',
            'phone': '+1234567891',
            'department_id': clinic_b_dept.id if clinic_b_dept else None,
            'role_id': physician_role.id if physician_role else None,
            'position': 'Physician',
            'hire_date': date(2021, 3, 20),
            'is_active': True
        },
        {
            'employee_id': 'EMP003',
            'name': 'Dr. Michael Brown',
            'email': 'michael.brown@healthcare.com',
            'phone': '+1234567892',
            'department_id': dental_dept.id if dental_dept else None,
            'role_id': physician_role.id if physician_role else None,
            'position': 'Dentist',
            'hire_date': date(2019, 8, 10),
            'is_active': True
        },
        {
            'employee_id': 'EMP004',
            'name': 'Maria Garcia',
            'email': 'maria.garcia@healthcare.com',
            'phone': '+1234567893',
            'department_id': registration_dept_main.id if registration_dept_main else None,
            'role_id': registration_role.id if registration_role else None,
            'position': 'Registration Clerk',
            'hire_date': date(2022, 1, 5),
            'is_active': True
        },
        {
            'employee_id': 'EMP005',
            'name': 'Robert Wilson',
            'email': 'robert.wilson@healthcare.com',
            'phone': '+1234567894',
            'department_id': lab_dept_main.id if lab_dept_main else None,
            'role_id': laboratory_role.id if laboratory_role else None,
            'position': 'Lab Technician',
            'hire_date': date(2021, 6, 15),
            'is_active': True
        },
        {
            'employee_id': 'EMP006',
            'name': 'Lisa Davis',
            'email': 'lisa.davis@healthcare.com',
            'phone': '+1234567895',
            'department_id': pharmacy_dept_main.id if pharmacy_dept_main else None,
            'role_id': pharmacy_role.id if pharmacy_role else None,
            'position': 'Pharmacist',
            'hire_date': date(2020, 11, 8),
            'is_active': True
        },
        {
            'employee_id': 'EMP007',
            'name': 'David Miller',
            'email': 'david.miller@healthcare.com',
            'phone': '+1234567896',
            'department_id': cashier_dept_main.id if cashier_dept_main else None,
            'role_id': cashier_role.id if cashier_role else None,
            'position': 'Cashier',
            'hire_date': date(2022, 2, 12),
            'is_active': True
        },
        {
            'employee_id': 'EMP008',
            'name': 'Jennifer Taylor',
            'email': 'jennifer.taylor@healthcare.com',
            'phone': '+1234567897',
            'department_id': hr_dept.id if hr_dept else None,
            'role_id': hr_role.id if hr_role else None,
            'position': 'HR Manager',
            'hire_date': date(2019, 4, 22),
            'is_active': True
        },
        {
            'employee_id': 'EMP009',
            'name': 'James Anderson',
            'email': 'james.anderson@healthcare.com',
            'phone': '+1234567898',
            'department_id': helpdesk_dept_main.id if helpdesk_dept_main else None,
            'role_id': helpdesk_role.id if helpdesk_role else None,
            'position': 'IT Support Specialist',
            'hire_date': date(2021, 9, 3),
            'is_active': True
        },
        {
            'employee_id': 'EMP010',
            'name': 'Dr. Emily White',
            'email': 'emily.white@healthcare.com',
            'phone': '+1234567899',
            'department_id': facility_dept.id if facility_dept else None,
            'role_id': facility_head_role.id if facility_head_role else None,
            'position': 'Facility Head',
            'hire_date': date(2018, 12, 1),
            'is_active': True
        },
        {
            'employee_id': 'ADMIN001',
            'name': 'System Administrator',
            'email': 'admin@healthcare.com',
            'phone': '+1234567800',
            'department_id': facility_dept.id if facility_dept else None,
            'role_id': superadmin_role.id if superadmin_role else None,
            'position': 'System Administrator',
            'hire_date': date(2018, 1, 1),
            'is_active': True
        },
        # North facility staff
        {
            'employee_id': 'EMP011',
            'name': 'Dr. Alex Chen',
            'email': 'alex.chen@healthcare.com',
            'phone': '+1234567801',
            'department_id': clinic_north.id if clinic_north else None,
            'role_id': physician_role.id if physician_role else None,
            'position': 'Physician',
            'hire_date': date(2021, 5, 10),
            'is_active': True
        },
        {
            'employee_id': 'EMP012',
            'name': 'Sofia Rodriguez',
            'email': 'sofia.rodriguez@healthcare.com',
            'phone': '+1234567802',
            'department_id': registration_dept_north.id if registration_dept_north else None,
            'role_id': registration_role.id if registration_role else None,
            'position': 'Registration Clerk',
            'hire_date': date(2022, 3, 15),
            'is_active': True
        },
        {
            'employee_id': 'EMP013',
            'name': 'Kevin Thompson',
            'email': 'kevin.thompson@healthcare.com',
            'phone': '+1234567803',
            'department_id': lab_dept_north.id if lab_dept_north else None,
            'role_id': laboratory_role.id if laboratory_role else None,
            'position': 'Lab Technician',
            'hire_date': date(2021, 8, 20),
            'is_active': True
        },
        {
            'employee_id': 'EMP014',
            'name': 'Amanda Lee',
            'email': 'amanda.lee@healthcare.com',
            'phone': '+1234567804',
            'department_id': pharmacy_dept_north.id if pharmacy_dept_north else None,
            'role_id': pharmacy_role.id if pharmacy_role else None,
            'position': 'Pharmacist',
            'hire_date': date(2021, 12, 5),
            'is_active': True
        },
        {
            'employee_id': 'EMP015',
            'name': 'Carlos Martinez',
            'email': 'carlos.martinez@healthcare.com',
            'phone': '+1234567805',
            'department_id': cashier_dept_north.id if cashier_dept_north else None,
            'role_id': cashier_role.id if cashier_role else None,
            'position': 'Cashier',
            'hire_date': date(2022, 4, 8),
            'is_active': True
        }
    ]
    
    created_staff = []
    for staff_data_item in staff_data:
        staff = Staff.query.filter_by(email=staff_data_item['email']).first()
        if not staff:
            staff = Staff(**staff_data_item)
            staff.set_password('password123')  # Default password
            db.session.add(staff)
            created_staff.append(staff)
    
    db.session.commit()
    
    # Create facility access for staff
    print("Creating facility access for staff...")
    for staff in created_staff:
        # Determine which facility this staff member belongs to based on their department
        if staff.department_id:
            dept = Department.query.get(staff.department_id)
            if dept and dept.facility_id:
                # Check if staff-facility relationship already exists
                existing = StaffFacility.query.filter_by(
                    staff_id=staff.id,
                    facility_id=dept.facility_id
                ).first()
                
                if not existing:
                    staff_facility = StaffFacility(
                        staff_id=staff.id,
                        facility_id=dept.facility_id,
                        can_access=True,
                        can_manage_staff=staff.role.name in ['superadmin', 'facility_head'],
                        can_manage_facility=staff.role.name in ['superadmin', 'facility_head'],
                        can_view_reports=True,
                        can_export_data=staff.role.name in ['superadmin', 'facility_head'],
                        assigned_by_id=1  # Admin
                    )
                    db.session.add(staff_facility)
    
    # Give superadmin access to all facilities
    admin = Staff.query.filter_by(email='admin@healthcare.com').first()
    if admin:
        for facility in [main_facility, north_facility]:
            if facility:
                existing = StaffFacility.query.filter_by(
                    staff_id=admin.id,
                    facility_id=facility.id
                ).first()
                
                if not existing:
                    staff_facility = StaffFacility(
                        staff_id=admin.id,
                        facility_id=facility.id,
                        can_access=True,
                        can_manage_staff=True,
                        can_manage_facility=True,
                        can_view_reports=True,
                        can_export_data=True,
                        assigned_by_id=admin.id
                    )
                    db.session.add(staff_facility)
    
    db.session.commit()
    print("Sample staff created successfully!")

def create_sample_patients():
    """Create sample patients"""
    print("Creating sample patients...")
    
    # Get facilities
    main_facility = Facility.query.filter_by(facility_code='PHC001').first()
    north_facility = Facility.query.filter_by(facility_code='PHC002').first()
    
    patients_data = [
        # Main facility patients
        {
            'mrn': Patient.generate_mrn('PHC001'),
            'national_id': '1234567890123456',
            'passport_id': None,
            'first_name': 'Alice',
            'last_name': 'Johnson',
            'middle_name': None,
            'dob': date(1985, 5, 15),
            'sex': 'F',
            'nationality': 'Country',
            'phone': '+1234567001',
            'email': 'alice.johnson@email.com',
            'address': '123 Main St, City, State 12345',
            'facility_id': main_facility.id if main_facility else 1
        },
        {
            'mrn': Patient.generate_mrn('PHC001'),
            'national_id': '1234567890123457',
            'passport_id': None,
            'first_name': 'Bob',
            'last_name': 'Williams',
            'middle_name': None,
            'dob': date(1978, 8, 22),
            'sex': 'M',
            'nationality': 'Country',
            'phone': '+1234567002',
            'email': 'bob.williams@email.com',
            'address': '456 Oak Ave, City, State 12345',
            'facility_id': main_facility.id if main_facility else 1
        },
        {
            'mrn': Patient.generate_mrn('PHC001'),
            'national_id': '1234567890123458',
            'passport_id': None,
            'first_name': 'Carol',
            'last_name': 'Davis',
            'middle_name': None,
            'dob': date(1992, 3, 10),
            'sex': 'F',
            'nationality': 'Country',
            'phone': '+1234567003',
            'email': 'carol.davis@email.com',
            'address': '789 Pine Rd, City, State 12345',
            'facility_id': main_facility.id if main_facility else 1
        },
        # North facility patients
        {
            'mrn': Patient.generate_mrn('PHC002'),
            'national_id': '1234567890123459',
            'passport_id': None,
            'first_name': 'David',
            'last_name': 'Miller',
            'middle_name': None,
            'dob': date(1965, 11, 5),
            'sex': 'M',
            'nationality': 'Country',
            'phone': '+1234567004',
            'email': 'david.miller@email.com',
            'address': '321 Elm St, City, State 12345',
            'facility_id': north_facility.id if north_facility else 2
        },
        {
            'mrn': Patient.generate_mrn('PHC002'),
            'national_id': '1234567890123460',
            'passport_id': None,
            'first_name': 'Eva',
            'last_name': 'Garcia',
            'middle_name': None,
            'dob': date(1989, 7, 18),
            'sex': 'F',
            'nationality': 'Country',
            'phone': '+1234567005',
            'email': 'eva.garcia@email.com',
            'address': '654 Maple Dr, City, State 12345',
            'facility_id': north_facility.id if north_facility else 2
        },
        {
            'mrn': Patient.generate_mrn('PHC002'),
            'national_id': None,
            'passport_id': 'P123456789',
            'first_name': 'Maria',
            'last_name': 'Rodriguez',
            'middle_name': None,
            'dob': date(1982, 12, 3),
            'sex': 'F',
            'nationality': 'Spain',
            'phone': '+1234567006',
            'email': 'maria.rodriguez@email.com',
            'address': '987 Cedar Ln, City, State 12345',
            'facility_id': north_facility.id if north_facility else 2
        }
    ]
    
    for patient_data in patients_data:
        # Check if patient already exists by national_id or passport_id
        existing_patient = None
        if patient_data['national_id']:
            existing_patient = Patient.query.filter_by(
                national_id=patient_data['national_id'],
                facility_id=patient_data['facility_id']
            ).first()
        elif patient_data['passport_id']:
            existing_patient = Patient.query.filter_by(
                passport_id=patient_data['passport_id'],
                facility_id=patient_data['facility_id']
            ).first()
        
        if not existing_patient:
            patient = Patient(**patient_data)
            db.session.add(patient)
    
    db.session.commit()
    print("Sample patients created successfully!")

def create_sample_drugs():
    """Create sample drugs"""
    print("Creating sample drugs...")
    
    drugs_data = [
        {
            'name': 'Paracetamol',
            'generic_name': 'Acetaminophen',
            'strength': '500mg',
            'form': 'tablet',
            'manufacturer': 'Generic Pharma',
            'atc_code': 'N02BE01',
            'is_active': True
        },
        {
            'name': 'Ibuprofen',
            'generic_name': 'Ibuprofen',
            'strength': '400mg',
            'form': 'tablet',
            'manufacturer': 'Generic Pharma',
            'atc_code': 'M01AE01',
            'is_active': True
        },
        {
            'name': 'Amoxicillin',
            'generic_name': 'Amoxicillin',
            'strength': '500mg',
            'form': 'capsule',
            'manufacturer': 'Generic Pharma',
            'atc_code': 'J01CA04',
            'is_active': True
        },
        {
            'name': 'Omeprazole',
            'generic_name': 'Omeprazole',
            'strength': '20mg',
            'form': 'capsule',
            'manufacturer': 'Generic Pharma',
            'atc_code': 'A02BC01',
            'is_active': True
        },
        {
            'name': 'Metformin',
            'generic_name': 'Metformin',
            'strength': '500mg',
            'form': 'tablet',
            'manufacturer': 'Generic Pharma',
            'atc_code': 'A10BA02',
            'is_active': True
        }
    ]
    
    for drug_data in drugs_data:
        drug = Drug.query.filter_by(name=drug_data['name']).first()
        if not drug:
            drug = Drug(**drug_data)
            db.session.add(drug)
    
    db.session.commit()
    print("Sample drugs created successfully!")

def main():
    """Main seeding function"""
    app = create_app()
    
    with app.app_context():
        print("Starting database seeding...")
        
        # Create tables if they don't exist
        db.create_all()
        
        # Seed data in order
        create_roles_and_permissions()
        create_facilities()
        create_departments()
        create_sample_staff()
        create_sample_patients()
        create_sample_drugs()
        
        print("\nDatabase seeding completed successfully!")
        print("\nDefault login credentials:")
        print("Email: admin@healthcare.com")
        print("Password: password123")
        print("\nOther staff can login with their email and password: password123")

if __name__ == '__main__':
    main()
