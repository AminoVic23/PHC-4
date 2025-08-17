from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import (Visit, ClinicalNote, Order, LabResult, RadiologyReport, 
                       Prescription, Invoice, Payment, Referral, QualityIncident, 
                       Survey, Staff, Department, Patient, Asset, WorkOrder, Ticket)
from app.extensions import db
from app.security import require_permission, audit_log, require_role
from datetime import datetime, timedelta
import json

facility_head_bp = Blueprint('facility_head', __name__, url_prefix='/facility-head')

@facility_head_bp.route('/')
@login_required
@require_role('facility_head')
def index():
    """Facility head dashboard - overview of all departments"""
    today = datetime.now().date()
    
    # Overall facility statistics
    total_visits = Visit.query.filter(Visit.visit_date == today).count()
    total_revenue = Payment.query.filter(Payment.payment_date == today).with_entities(
        db.func.sum(Payment.amount)).scalar() or 0
    
    # Department-wise statistics
    departments = Department.query.all()
    dept_stats = []
    
    for dept in departments:
        # Staff count
        staff_count = Staff.query.filter(Staff.department_id == dept.id).count()
        
        # Today's activities (if applicable)
        if dept.type == 'clinical':
            today_visits = Visit.query.filter(
                Visit.department_id == dept.id,
                Visit.visit_date == today
            ).count()
        else:
            today_visits = 0
        
        # Pending items
        if dept.type == 'laboratory':
            pending_items = LabResult.query.filter(LabResult.status == 'pending').count()
        elif dept.type == 'radiology':
            pending_items = RadiologyReport.query.filter(RadiologyReport.status == 'pending').count()
        elif dept.type == 'pharmacy':
            pending_items = Prescription.query.filter(Prescription.status == 'active').count()
        else:
            pending_items = 0
        
        dept_stats.append({
            'department': dept,
            'staff_count': staff_count,
            'today_visits': today_visits,
            'pending_items': pending_items
        })
    
    # Quality and safety indicators
    open_incidents = QualityIncident.get_reported_incidents().count()
    critical_incidents = QualityIncident.get_high_severity_incidents().count()
    avg_satisfaction = Survey.query.with_entities(db.func.avg(Survey.overall_rating)).scalar() or 0
    
    # Operational indicators
    pending_referrals = Referral.query.filter(Referral.status == 'pending').count()
    overdue_work_orders = WorkOrder.get_overdue_work_orders().count()
    open_tickets = Ticket.query.filter(Ticket.status == 'open').count()
    
    return render_template('facility_head/dashboard.html',
                         total_visits=total_visits,
                         total_revenue=total_revenue,
                         dept_stats=dept_stats,
                         open_incidents=open_incidents,
                         critical_incidents=critical_incidents,
                         avg_satisfaction=round(avg_satisfaction, 1),
                         pending_referrals=pending_referrals,
                         overdue_work_orders=overdue_work_orders,
                         open_tickets=open_tickets)

@facility_head_bp.route('/department-overview/<int:dept_id>')
@login_required
@require_role('facility_head')
def department_overview(dept_id):
    """Detailed overview of a specific department"""
    department = Department.query.get_or_404(dept_id)
    
    # Department staff
    staff = Staff.query.filter(Staff.department_id == dept_id).all()
    
    # Department-specific activities
    if department.type == 'clinical':
        # Clinical department
        today_visits = Visit.query.filter(
            Visit.department_id == dept_id,
            Visit.visit_date == datetime.now().date()
        ).all()
        
        recent_notes = ClinicalNote.query.join(Visit).filter(
            Visit.department_id == dept_id
        ).order_by(ClinicalNote.created_at.desc()).limit(10).all()
        
        activities = {
            'visits': today_visits,
            'notes': recent_notes
        }
        
    elif department.type == 'laboratory':
        # Laboratory department
        pending_results = LabResult.query.filter(LabResult.status == 'pending').limit(10).all()
        recent_results = LabResult.query.order_by(LabResult.created_at.desc()).limit(10).all()
        
        activities = {
            'pending_results': pending_results,
            'recent_results': recent_results
        }
        
    elif department.type == 'radiology':
        # Radiology department
        pending_reports = RadiologyReport.query.filter(RadiologyReport.status == 'pending').limit(10).all()
        recent_reports = RadiologyReport.query.order_by(RadiologyReport.created_at.desc()).limit(10).all()
        
        activities = {
            'pending_reports': pending_reports,
            'recent_reports': recent_reports
        }
        
    elif department.type == 'pharmacy':
        # Pharmacy department
        active_prescriptions = Prescription.query.filter(Prescription.status == 'active').limit(10).all()
        low_stock_drugs = db.session.query(Asset).filter(Asset.quantity <= Asset.reorder_level).limit(10).all()
        
        activities = {
            'active_prescriptions': active_prescriptions,
            'low_stock_drugs': low_stock_drugs
        }
        
    else:
        # Support department
        activities = {}
    
    return render_template('facility_head/department_overview.html',
                         department=department,
                         staff=staff,
                         activities=activities)

@facility_head_bp.route('/quality-safety')
@login_required
@require_role('facility_head')
def quality_safety():
    """Quality and safety oversight"""
    # Recent incidents
    recent_incidents = QualityIncident.get_reported_incidents().limit(10).all()
    critical_incidents = QualityIncident.get_high_severity_incidents().limit(10).all()
    
    # Satisfaction trends
    satisfaction_trends = Survey.get_satisfaction_trends(days=30)
    
    # Clinical quality metrics
    total_visits = Visit.query.filter(Visit.visit_date >= datetime.now().date() - timedelta(days=30)).count()
    visits_with_notes = Visit.query.join(ClinicalNote).filter(
        Visit.visit_date >= datetime.now().date() - timedelta(days=30)
    ).count()
    
    documentation_rate = (visits_with_notes / total_visits * 100) if total_visits > 0 else 0
    
    # Safety indicators
    pending_results = LabResult.query.filter(LabResult.status == 'pending').count()
    unverified_reports = RadiologyReport.query.filter(RadiologyReport.status == 'pending').count()
    
    return render_template('facility_head/quality_safety.html',
                         recent_incidents=recent_incidents,
                         critical_incidents=critical_incidents,
                         satisfaction_trends=satisfaction_trends,
                         documentation_rate=round(documentation_rate, 1),
                         pending_results=pending_results,
                         unverified_reports=unverified_reports)

@facility_head_bp.route('/financial-overview')
@login_required
@require_role('facility_head')
def financial_overview():
    """Financial overview and performance"""
    # Get date range
    start_date = request.args.get('start_date', 
                                 (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    # Revenue analysis
    payments = Payment.query.filter(
        Payment.payment_date >= start_date,
        Payment.payment_date <= end_date
    ).all()
    
    total_revenue = sum(p.amount for p in payments)
    
    # Revenue by department (through visits)
    revenue_by_dept = {}
    for payment in payments:
        if payment.invoice and payment.invoice.visit:
            dept_name = payment.invoice.visit.department.name
            revenue_by_dept[dept_name] = revenue_by_dept.get(dept_name, 0) + payment.amount
    
    # Outstanding receivables
    outstanding_invoices = Invoice.query.filter(Invoice.status == 'final').all()
    total_outstanding = sum(inv.total_amount - inv.paid_amount for inv in outstanding_invoices)
    
    # Insurance claims
    pending_claims = Referral.query.filter(Referral.status == 'submitted').count()
    approved_claims = Referral.query.filter(Referral.status == 'accepted').count()
    
    return render_template('facility_head/financial_overview.html',
                         total_revenue=total_revenue,
                         revenue_by_dept=revenue_by_dept,
                         total_outstanding=total_outstanding,
                         pending_claims=pending_claims,
                         approved_claims=approved_claims,
                         start_date=start_date,
                         end_date=end_date)

@facility_head_bp.route('/operational-status')
@login_required
@require_role('facility_head')
def operational_status():
    """Operational status and capacity"""
    # Staff availability
    departments = Department.query.all()
    staff_status = []
    
    for dept in departments:
        total_staff = Staff.query.filter(Staff.department_id == dept.id).count()
        active_staff = Staff.query.filter(
            Staff.department_id == dept.id,
            Staff.is_active == True
        ).count()
        
        staff_status.append({
            'department': dept,
            'total_staff': total_staff,
            'active_staff': active_staff,
            'availability_rate': (active_staff / total_staff * 100) if total_staff > 0 else 0
        })
    
    # Equipment status
    total_assets = Asset.query.count()
    operational_assets = Asset.query.filter(Asset.condition == 'operational').count()
    maintenance_due = Asset.get_maintenance_due_assets().count()
    
    # Work order status
    open_work_orders = WorkOrder.query.filter(WorkOrder.status == 'open').count()
    in_progress_orders = WorkOrder.get_in_progress_work_orders().count()
    overdue_orders = WorkOrder.get_overdue_work_orders().count()
    
    # IT system status
    open_tickets = Ticket.query.filter(Ticket.status == 'open').count()
    critical_tickets = Ticket.get_critical_tickets().count()
    
    return render_template('facility_head/operational_status.html',
                         staff_status=staff_status,
                         total_assets=total_assets,
                         operational_assets=operational_assets,
                         maintenance_due=maintenance_due,
                         open_work_orders=open_work_orders,
                         in_progress_orders=in_progress_orders,
                         overdue_orders=overdue_orders,
                         open_tickets=open_tickets,
                         critical_tickets=critical_tickets)

@facility_head_bp.route('/approvals')
@login_required
@require_role('facility_head')
def approvals():
    """Approval queue for facility head"""
    # High-value financial approvals
    high_value_invoices = Invoice.query.filter(
        Invoice.total_amount >= 5000,
        Invoice.status == 'final'
    ).limit(10).all()
    
    # Critical incident approvals
    critical_incidents = QualityIncident.get_high_severity_incidents().limit(10).all()
    
    # Major referral approvals
    major_referrals = Referral.query.filter(
        Referral.referral_type.in_(['specialist', 'tertiary']),
        Referral.status == 'pending'
    ).limit(10).all()
    
    # Asset purchase approvals
    asset_purchases = Asset.query.filter(
        Asset.purchase_cost >= 10000
    ).order_by(Asset.created_at.desc()).limit(10).all()
    
    return render_template('facility_head/approvals.html',
                         high_value_invoices=high_value_invoices,
                         critical_incidents=critical_incidents,
                         major_referrals=major_referrals,
                         asset_purchases=asset_purchases)

@facility_head_bp.route('/reports')
@login_required
@require_role('facility_head')
def reports():
    """Comprehensive facility reports"""
    # Get date range
    start_date = request.args.get('start_date', 
                                 (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    # Clinical reports
    total_visits = Visit.query.filter(
        Visit.visit_date >= start_date,
        Visit.visit_date <= end_date
    ).count()
    
    completed_visits = Visit.query.filter(
        Visit.visit_date >= start_date,
        Visit.visit_date <= end_date,
        Visit.status == 'completed'
    ).count()
    
    # Financial reports
    total_revenue = Payment.query.filter(
        Payment.payment_date >= start_date,
        Payment.payment_date <= end_date
    ).with_entities(db.func.sum(Payment.amount)).scalar() or 0
    
    # Quality reports
    total_incidents = QualityIncident.query.filter(
        QualityIncident.incident_date >= start_date,
        QualityIncident.incident_date <= end_date
    ).count()
    
    avg_satisfaction = Survey.query.filter(
        Survey.survey_date >= start_date,
        Survey.survey_date <= end_date
    ).with_entities(db.func.avg(Survey.overall_rating)).scalar() or 0
    
    # Operational reports
    total_work_orders = WorkOrder.query.filter(
        WorkOrder.created_at >= start_date
    ).count()
    
    completed_work_orders = WorkOrder.query.filter(
        WorkOrder.completed_date >= start_date,
        WorkOrder.completed_date <= end_date
    ).count()
    
    return render_template('facility_head/reports.html',
                         total_visits=total_visits,
                         completed_visits=completed_visits,
                         total_revenue=total_revenue,
                         total_incidents=total_incidents,
                         avg_satisfaction=round(avg_satisfaction, 1),
                         total_work_orders=total_work_orders,
                         completed_work_orders=completed_work_orders,
                         start_date=start_date,
                         end_date=end_date)

# API endpoints
@facility_head_bp.route('/api/dashboard-stats')
@login_required
@require_role('facility_head')
def api_dashboard_stats():
    """Get facility-wide dashboard statistics"""
    today = datetime.now().date()
    
    # Overall statistics
    total_visits = Visit.query.filter(Visit.visit_date == today).count()
    total_revenue = Payment.query.filter(Payment.payment_date == today).with_entities(
        db.func.sum(Payment.amount)).scalar() or 0
    
    # Quality indicators
    open_incidents = QualityIncident.get_reported_incidents().count()
    critical_incidents = QualityIncident.get_high_severity_incidents().count()
    avg_satisfaction = Survey.query.with_entities(db.func.avg(Survey.overall_rating)).scalar() or 0
    
    # Operational indicators
    pending_referrals = Referral.query.filter(Referral.status == 'pending').count()
    overdue_work_orders = WorkOrder.get_overdue_work_orders().count()
    open_tickets = Ticket.query.filter(Ticket.status == 'open').count()
    
    return jsonify({
        'total_visits': total_visits,
        'total_revenue': total_revenue,
        'open_incidents': open_incidents,
        'critical_incidents': critical_incidents,
        'avg_satisfaction': round(avg_satisfaction, 1),
        'pending_referrals': pending_referrals,
        'overdue_work_orders': overdue_work_orders,
        'open_tickets': open_tickets
    })

@facility_head_bp.route('/api/department-stats')
@login_required
@require_role('facility_head')
def api_department_stats():
    """Get department-wise statistics"""
    departments = Department.query.all()
    dept_stats = []
    
    for dept in departments:
        staff_count = Staff.query.filter(Staff.department_id == dept.id).count()
        
        if dept.type == 'clinical':
            today_visits = Visit.query.filter(
                Visit.department_id == dept.id,
                Visit.visit_date == datetime.now().date()
            ).count()
        else:
            today_visits = 0
        
        dept_stats.append({
            'department_name': dept.name,
            'department_type': dept.type,
            'staff_count': staff_count,
            'today_visits': today_visits
        })
    
    return jsonify({'departments': dept_stats})

@facility_head_bp.route('/api/quality-metrics')
@login_required
@require_role('facility_head')
def api_quality_metrics():
    """Get quality and safety metrics"""
    days = request.args.get('days', 30, type=int)
    start_date = datetime.now().date() - timedelta(days=days)
    
    # Documentation rate
    total_visits = Visit.query.filter(Visit.visit_date >= start_date).count()
    visits_with_notes = Visit.query.join(ClinicalNote).filter(
        Visit.visit_date >= start_date
    ).count()
    
    documentation_rate = (visits_with_notes / total_visits * 100) if total_visits > 0 else 0
    
    # Incident statistics
    total_incidents = QualityIncident.query.filter(
        QualityIncident.incident_date >= start_date
    ).count()
    
    critical_incidents = QualityIncident.get_high_severity_incidents().count()
    
    # Satisfaction trends
    satisfaction_trends = Survey.get_satisfaction_trends(days=days)
    
    return jsonify({
        'documentation_rate': round(documentation_rate, 1),
        'total_incidents': total_incidents,
        'critical_incidents': critical_incidents,
        'satisfaction_trends': satisfaction_trends
    })

@facility_head_bp.route('/api/revenue-analysis')
@login_required
@require_role('facility_head')
def api_revenue_analysis():
    """Get revenue analysis by department"""
    days = request.args.get('days', 30, type=int)
    start_date = datetime.now().date() - timedelta(days=days)
    
    # Get revenue by department through visits
    revenue_by_dept = db.session.query(
        Department.name,
        db.func.sum(Payment.amount).label('total_revenue')
    ).join(Visit, Department.id == Visit.department_id)\
     .join(Invoice, Visit.id == Invoice.visit_id)\
     .join(Payment, Invoice.id == Payment.invoice_id)\
     .filter(Payment.payment_date >= start_date)\
     .group_by(Department.name)\
     .all()
    
    return jsonify({
        'revenue_by_department': [
            {'department': dept, 'revenue': float(revenue)} 
            for dept, revenue in revenue_by_dept
        ]
    })
