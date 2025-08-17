"""
Dashboard routes for system-wide views and reports
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.visits import Visit, Appointment
from app.models.patients import Patient
from app.models.billing import Invoice, Payment
from app.models.orders import Order
from app.models.pharmacy import Prescription
from app.models.helpdesk import Ticket
from app.models.quality import QualityIncident
from app.security import require_permission, audit_log
from datetime import datetime, timedelta
import json

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
@require_permission('reports_view')
def index():
    """Main dashboard"""
    today = datetime.now().date()
    start_of_month = today.replace(day=1)
    
    # Patient statistics
    total_patients = Patient.query.filter_by(active=True).count()
    new_patients_this_month = Patient.query.filter(
        Patient.created_at >= start_of_month,
        Patient.active == True
    ).count()
    
    # Visit statistics
    total_visits_today = Visit.query.filter_by(visit_date=today).count()
    open_visits = Visit.query.filter_by(status='open').count()
    total_visits_this_month = Visit.query.filter(
        Visit.visit_date >= start_of_month
    ).count()
    
    # Appointment statistics
    today_appointments = Appointment.get_today_appointments()
    overdue_appointments = Appointment.get_no_shows(start_date=today - timedelta(days=7))
    
    # Financial statistics
    today_revenue = db.session.query(db.func.sum(Payment.amount))\
                              .filter(db.func.date(Payment.paid_at) == today)\
                              .scalar() or 0
    
    month_revenue = db.session.query(db.func.sum(Payment.amount))\
                              .filter(Payment.paid_at >= start_of_month)\
                              .scalar() or 0
    
    pending_invoices = Invoice.query.filter_by(status='finalized').count()
    
    # Clinical statistics
    pending_orders = Order.query.filter(Order.status.in_(['ordered', 'in_progress'])).count()
    pending_prescriptions = Prescription.query.filter_by(status='signed').count()
    
    # Support statistics
    open_tickets = Ticket.query.filter_by(status='open').count()
    quality_incidents = QualityIncident.query.filter(
        QualityIncident.created_at >= start_of_month
    ).count()
    
    return render_template('dashboard/index.html',
                         total_patients=total_patients,
                         new_patients_this_month=new_patients_this_month,
                         total_visits_today=total_visits_today,
                         open_visits=open_visits,
                         total_visits_this_month=total_visits_this_month,
                         today_appointments=today_appointments,
                         overdue_appointments=overdue_appointments,
                         today_revenue=today_revenue,
                         month_revenue=month_revenue,
                         pending_invoices=pending_invoices,
                         pending_orders=pending_orders,
                         pending_prescriptions=pending_prescriptions,
                         open_tickets=open_tickets,
                         quality_incidents=quality_incidents)

@dashboard_bp.route('/reports/patient')
@login_required
@require_permission('reports_view')
def patient_report():
    """Patient statistics report"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        start_date = datetime.now().date() - timedelta(days=30)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        end_date = datetime.now().date()
    
    # New patients by date
    new_patients = db.session.query(
        db.func.date(Patient.created_at).label('date'),
        db.func.count(Patient.id).label('count')
    ).filter(
        Patient.created_at >= start_date,
        Patient.created_at <= end_date + timedelta(days=1),
        Patient.active == True
    ).group_by(db.func.date(Patient.created_at)).all()
    
    # Patients by age group
    age_groups = db.session.query(
        Patient.age_group,
        db.func.count(Patient.id).label('count')
    ).filter(
        Patient.active == True
    ).group_by(Patient.age_group).all()
    
    # Patients by sex
    sex_distribution = db.session.query(
        Patient.sex,
        db.func.count(Patient.id).label('count')
    ).filter(
        Patient.active == True
    ).group_by(Patient.sex).all()
    
    return render_template('dashboard/patient_report.html',
                         new_patients=new_patients,
                         age_groups=age_groups,
                         sex_distribution=sex_distribution,
                         start_date=start_date,
                         end_date=end_date)

@dashboard_bp.route('/reports/clinical')
@login_required
@require_permission('reports_view')
def clinical_report():
    """Clinical activity report"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        start_date = datetime.now().date() - timedelta(days=30)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        end_date = datetime.now().date()
    
    # Visits by date
    visits_by_date = db.session.query(
        Visit.visit_date,
        db.func.count(Visit.id).label('count')
    ).filter(
        Visit.visit_date >= start_date,
        Visit.visit_date <= end_date
    ).group_by(Visit.visit_date).all()
    
    # Visits by clinic
    visits_by_clinic = db.session.query(
        db.func.coalesce(db.func.string_agg('departments.name', ', '), 'Unknown').label('clinic'),
        db.func.count(Visit.id).label('count')
    ).outerjoin(db.func.departments, Visit.clinic_id == db.func.departments.id)\
     .filter(
        Visit.visit_date >= start_date,
        Visit.visit_date <= end_date
    ).group_by(Visit.clinic_id).all()
    
    # Orders by type
    orders_by_type = db.session.query(
        Order.type,
        db.func.count(Order.id).label('count')
    ).filter(
        Order.created_at >= start_date,
        Order.created_at <= end_date + timedelta(days=1)
    ).group_by(Order.type).all()
    
    return render_template('dashboard/clinical_report.html',
                         visits_by_date=visits_by_date,
                         visits_by_clinic=visits_by_clinic,
                         orders_by_type=orders_by_type,
                         start_date=start_date,
                         end_date=end_date)

@dashboard_bp.route('/reports/financial')
@login_required
@require_permission('reports_view')
def financial_report():
    """Financial report"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        start_date = datetime.now().date() - timedelta(days=30)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        end_date = datetime.now().date()
    
    # Revenue by date
    revenue_by_date = db.session.query(
        db.func.date(Payment.paid_at).label('date'),
        db.func.sum(Payment.amount).label('amount')
    ).filter(
        Payment.paid_at >= start_date,
        Payment.paid_at <= end_date + timedelta(days=1)
    ).group_by(db.func.date(Payment.paid_at)).all()
    
    # Revenue by payment method
    revenue_by_method = db.session.query(
        Payment.method,
        db.func.sum(Payment.amount).label('amount')
    ).filter(
        Payment.paid_at >= start_date,
        Payment.paid_at <= end_date + timedelta(days=1)
    ).group_by(Payment.method).all()
    
    # Invoice status distribution
    invoice_status = db.session.query(
        Invoice.status,
        db.func.count(Invoice.id).label('count'),
        db.func.sum(Invoice.net_amount).label('amount')
    ).filter(
        Invoice.created_at >= start_date,
        Invoice.created_at <= end_date + timedelta(days=1)
    ).group_by(Invoice.status).all()
    
    return render_template('dashboard/financial_report.html',
                         revenue_by_date=revenue_by_date,
                         revenue_by_method=revenue_by_method,
                         invoice_status=invoice_status,
                         start_date=start_date,
                         end_date=end_date)

@dashboard_bp.route('/reports/operational')
@login_required
@require_permission('reports_view')
def operational_report():
    """Operational metrics report"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        start_date = datetime.now().date() - timedelta(days=30)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        end_date = datetime.now().date()
    
    # Appointment statistics
    appointment_stats = db.session.query(
        Appointment.status,
        db.func.count(Appointment.id).label('count')
    ).filter(
        Appointment.start_dt >= start_date,
        Appointment.start_dt <= end_date + timedelta(days=1)
    ).group_by(Appointment.status).all()
    
    # Order turnaround time
    completed_orders = Order.query.filter(
        Order.completed_at.isnot(None),
        Order.created_at >= start_date,
        Order.created_at <= end_date + timedelta(days=1)
    ).all()
    
    avg_turnaround = 0
    if completed_orders:
        total_time = sum((o.completed_at - o.created_at).total_seconds() / 3600 for o in completed_orders)
        avg_turnaround = total_time / len(completed_orders)
    
    # Prescription dispensing time
    dispensed_prescriptions = Prescription.query.filter(
        Prescription.dispensed_at.isnot(None),
        Prescription.signed_at >= start_date,
        Prescription.signed_at <= end_date + timedelta(days=1)
    ).all()
    
    avg_dispensing_time = 0
    if dispensed_prescriptions:
        total_time = sum((p.dispensed_at - p.signed_at).total_seconds() / 3600 for p in dispensed_prescriptions)
        avg_dispensing_time = total_time / len(dispensed_prescriptions)
    
    return render_template('dashboard/operational_report.html',
                         appointment_stats=appointment_stats,
                         avg_turnaround=avg_turnaround,
                         avg_dispensing_time=avg_dispensing_time,
                         start_date=start_date,
                         end_date=end_date)

# API endpoints for charts
@dashboard_bp.route('/api/charts/patient-growth')
@login_required
@require_permission('reports_view')
def api_patient_growth():
    """Patient growth chart data"""
    days = int(request.args.get('days', 30))
    start_date = datetime.now().date() - timedelta(days=days)
    
    data = db.session.query(
        db.func.date(Patient.created_at).label('date'),
        db.func.count(Patient.id).label('count')
    ).filter(
        Patient.created_at >= start_date,
        Patient.active == True
    ).group_by(db.func.date(Patient.created_at)).all()
    
    return jsonify([{
        'date': str(row.date),
        'count': row.count
    } for row in data])

@dashboard_bp.route('/api/charts/revenue')
@login_required
@require_permission('reports_view')
def api_revenue():
    """Revenue chart data"""
    days = int(request.args.get('days', 30))
    start_date = datetime.now().date() - timedelta(days=days)
    
    data = db.session.query(
        db.func.date(Payment.paid_at).label('date'),
        db.func.sum(Payment.amount).label('amount')
    ).filter(
        Payment.paid_at >= start_date
    ).group_by(db.func.date(Payment.paid_at)).all()
    
    return jsonify([{
        'date': str(row.date),
        'amount': float(row.amount) if row.amount else 0
    } for row in data])

@dashboard_bp.route('/api/charts/visits')
@login_required
@require_permission('reports_view')
def api_visits():
    """Visits chart data"""
    days = int(request.args.get('days', 30))
    start_date = datetime.now().date() - timedelta(days=days)
    
    data = db.session.query(
        Visit.visit_date,
        db.func.count(Visit.id).label('count')
    ).filter(
        Visit.visit_date >= start_date
    ).group_by(Visit.visit_date).all()
    
    return jsonify([{
        'date': str(row.visit_date),
        'count': row.count
    } for row in data])

@dashboard_bp.route('/api/charts/department-activity')
@login_required
@require_permission('reports_view')
def api_department_activity():
    """Department activity chart data"""
    days = int(request.args.get('days', 30))
    start_date = datetime.now().date() - timedelta(days=days)
    
    data = db.session.query(
        db.func.coalesce(db.func.string_agg('departments.name', ', '), 'Unknown').label('department'),
        db.func.count(Visit.id).label('count')
    ).outerjoin(db.func.departments, Visit.clinic_id == db.func.departments.id)\
     .filter(
        Visit.visit_date >= start_date
    ).group_by(Visit.clinic_id).all()
    
    return jsonify([{
        'department': row.department,
        'count': row.count
    } for row in data])
