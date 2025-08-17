from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import (Visit, ClinicalNote, Order, LabResult, RadiologyReport, 
                       Prescription, Invoice, Payment, Referral, QualityIncident, 
                       Survey, Staff, Department, Patient)
from app.extensions import db
from app.security import require_permission, audit_log
from datetime import datetime, timedelta
import json

medical_admin_bp = Blueprint('medical_admin', __name__, url_prefix='/medical-admin')

@medical_admin_bp.route('/')
@login_required
@require_permission('medical_admin.view')
def index():
    """Medical administration dashboard"""
    # Get today's statistics
    today = datetime.now().date()
    
    # Visit statistics
    today_visits = Visit.query.filter(Visit.visit_date == today).count()
    completed_visits = Visit.query.filter(Visit.visit_date == today, Visit.status == 'completed').count()
    pending_visits = Visit.query.filter(Visit.visit_date == today, Visit.status == 'in_progress').count()
    
    # Clinical statistics
    today_notes = ClinicalNote.query.filter(ClinicalNote.created_at >= today).count()
    today_orders = Order.query.filter(Order.created_at >= today).count()
    pending_results = LabResult.query.filter(LabResult.status == 'pending').count()
    
    # Financial statistics
    today_revenue = Payment.query.filter(Payment.payment_date == today).with_entities(
        db.func.sum(Payment.amount)).scalar() or 0
    
    # Quality indicators
    open_incidents = QualityIncident.get_reported_incidents().count()
    avg_satisfaction = Survey.query.with_entities(db.func.avg(Survey.overall_rating)).scalar() or 0
    
    return render_template('medical_admin/dashboard.html',
                         today_visits=today_visits,
                         completed_visits=completed_visits,
                         pending_visits=pending_visits,
                         today_notes=today_notes,
                         today_orders=today_orders,
                         pending_results=pending_results,
                         today_revenue=today_revenue,
                         open_incidents=open_incidents,
                         avg_satisfaction=round(avg_satisfaction, 1))

@medical_admin_bp.route('/clinical-oversight')
@login_required
@require_permission('medical_admin.view')
def clinical_oversight():
    """Clinical oversight and monitoring"""
    # Get recent clinical activities
    recent_notes = ClinicalNote.query.order_by(ClinicalNote.created_at.desc()).limit(10).all()
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    pending_results = LabResult.query.filter(LabResult.status == 'pending').limit(10).all()
    
    # Get provider statistics
    providers = Staff.query.filter(Staff.role.has(name='physician')).all()
    provider_stats = []
    
    for provider in providers:
        today_visits = Visit.query.filter(
            Visit.provider_id == provider.id,
            Visit.visit_date == datetime.now().date()
        ).count()
        
        today_notes = ClinicalNote.query.filter(
            ClinicalNote.provider_id == provider.id,
            ClinicalNote.created_at >= datetime.now().date()
        ).count()
        
        provider_stats.append({
            'provider': provider,
            'today_visits': today_visits,
            'today_notes': today_notes
        })
    
    return render_template('medical_admin/clinical_oversight.html',
                         recent_notes=recent_notes,
                         recent_orders=recent_orders,
                         pending_results=pending_results,
                         provider_stats=provider_stats)

@medical_admin_bp.route('/quality-monitoring')
@login_required
@require_permission('medical_admin.view')
def quality_monitoring():
    """Quality monitoring and incident management"""
    # Get recent incidents
    recent_incidents = QualityIncident.get_reported_incidents().limit(10).all()
    
    # Get satisfaction trends
    satisfaction_trends = Survey.get_satisfaction_trends(days=30)
    
    # Get clinical quality metrics
    total_visits = Visit.query.filter(Visit.visit_date >= datetime.now().date() - timedelta(days=30)).count()
    visits_with_notes = Visit.query.join(ClinicalNote).filter(
        Visit.visit_date >= datetime.now().date() - timedelta(days=30)
    ).count()
    
    documentation_rate = (visits_with_notes / total_visits * 100) if total_visits > 0 else 0
    
    # Get referral statistics
    total_referrals = Referral.query.filter(
        Referral.referral_date >= datetime.now().date() - timedelta(days=30)
    ).count()
    
    accepted_referrals = Referral.query.filter(
        Referral.referral_date >= datetime.now().date() - timedelta(days=30),
        Referral.status == 'accepted'
    ).count()
    
    referral_acceptance_rate = (accepted_referrals / total_referrals * 100) if total_referrals > 0 else 0
    
    return render_template('medical_admin/quality_monitoring.html',
                         recent_incidents=recent_incidents,
                         satisfaction_trends=satisfaction_trends,
                         documentation_rate=round(documentation_rate, 1),
                         referral_acceptance_rate=round(referral_acceptance_rate, 1))

@medical_admin_bp.route('/financial-oversight')
@login_required
@require_permission('medical_admin.view')
def financial_oversight():
    """Financial oversight and revenue monitoring"""
    # Get date range
    start_date = request.args.get('start_date', 
                                 (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    # Get revenue data
    payments = Payment.query.filter(
        Payment.payment_date >= start_date,
        Payment.payment_date <= end_date
    ).all()
    
    total_revenue = sum(p.amount for p in payments)
    
    # Revenue by payment method
    revenue_by_method = {}
    for payment in payments:
        method = payment.payment_method
        revenue_by_method[method] = revenue_by_method.get(method, 0) + payment.amount
    
    # Get outstanding invoices
    outstanding_invoices = Invoice.query.filter(Invoice.status == 'final').all()
    total_outstanding = sum(inv.total_amount - inv.paid_amount for inv in outstanding_invoices)
    
    # Get insurance claims
    pending_claims = Referral.query.filter(Referral.status == 'submitted').count()
    
    return render_template('medical_admin/financial_oversight.html',
                         total_revenue=total_revenue,
                         revenue_by_method=revenue_by_method,
                         total_outstanding=total_outstanding,
                         pending_claims=pending_claims,
                         start_date=start_date,
                         end_date=end_date)

@medical_admin_bp.route('/staff-management')
@login_required
@require_permission('medical_admin.view')
def staff_management():
    """Staff management and scheduling oversight"""
    # Get staff statistics by department
    departments = Department.query.all()
    dept_stats = []
    
    for dept in departments:
        staff_count = Staff.query.filter(Staff.department_id == dept.id).count()
        active_staff = Staff.query.filter(
            Staff.department_id == dept.id,
            Staff.is_active == True
        ).count()
        
        dept_stats.append({
            'department': dept,
            'total_staff': staff_count,
            'active_staff': active_staff
        })
    
    # Get recent staff activities
    recent_notes = ClinicalNote.query.order_by(ClinicalNote.created_at.desc()).limit(20).all()
    
    # Get provider performance
    providers = Staff.query.filter(Staff.role.has(name='physician')).all()
    provider_performance = []
    
    for provider in providers:
        # Get last 30 days performance
        start_date = datetime.now().date() - timedelta(days=30)
        
        visits_count = Visit.query.filter(
            Visit.provider_id == provider.id,
            Visit.visit_date >= start_date
        ).count()
        
        notes_count = ClinicalNote.query.filter(
            ClinicalNote.provider_id == provider.id,
            ClinicalNote.created_at >= start_date
        ).count()
        
        avg_satisfaction = Survey.query.filter(
            Survey.created_at >= start_date
        ).with_entities(db.func.avg(Survey.overall_rating)).scalar() or 0
        
        provider_performance.append({
            'provider': provider,
            'visits_count': visits_count,
            'notes_count': notes_count,
            'avg_satisfaction': round(avg_satisfaction, 1)
        })
    
    return render_template('medical_admin/staff_management.html',
                         dept_stats=dept_stats,
                         recent_notes=recent_notes,
                         provider_performance=provider_performance)

@medical_admin_bp.route('/reports')
@login_required
@require_permission('medical_admin.view')
def reports():
    """Medical administration reports"""
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
    
    return render_template('medical_admin/reports.html',
                         total_visits=total_visits,
                         completed_visits=completed_visits,
                         total_revenue=total_revenue,
                         total_incidents=total_incidents,
                         avg_satisfaction=round(avg_satisfaction, 1),
                         start_date=start_date,
                         end_date=end_date)

@medical_admin_bp.route('/approvals')
@login_required
@require_permission('medical_admin.approve')
def approvals():
    """Approval queue for medical administration"""
    # Get pending approvals
    pending_referrals = Referral.query.filter(Referral.status == 'pending').all()
    pending_incidents = QualityIncident.query.filter(QualityIncident.status == 'reported').all()
    
    # Get high-value invoices for approval
    high_value_invoices = Invoice.query.filter(
        Invoice.total_amount >= 1000,
        Invoice.status == 'final'
    ).limit(10).all()
    
    return render_template('medical_admin/approvals.html',
                         pending_referrals=pending_referrals,
                         pending_incidents=pending_incidents,
                         high_value_invoices=high_value_invoices)

# API endpoints
@medical_admin_bp.route('/api/dashboard-stats')
@login_required
@require_permission('medical_admin.view')
def api_dashboard_stats():
    """Get dashboard statistics"""
    today = datetime.now().date()
    
    # Visit statistics
    today_visits = Visit.query.filter(Visit.visit_date == today).count()
    completed_visits = Visit.query.filter(Visit.visit_date == today, Visit.status == 'completed').count()
    
    # Financial statistics
    today_revenue = Payment.query.filter(Payment.payment_date == today).with_entities(
        db.func.sum(Payment.amount)).scalar() or 0
    
    # Quality indicators
    open_incidents = QualityIncident.get_reported_incidents().count()
    avg_satisfaction = Survey.query.with_entities(db.func.avg(Survey.overall_rating)).scalar() or 0
    
    return jsonify({
        'today_visits': today_visits,
        'completed_visits': completed_visits,
        'today_revenue': today_revenue,
        'open_incidents': open_incidents,
        'avg_satisfaction': round(avg_satisfaction, 1)
    })

@medical_admin_bp.route('/api/clinical-metrics')
@login_required
@require_permission('medical_admin.view')
def api_clinical_metrics():
    """Get clinical quality metrics"""
    days = request.args.get('days', 30, type=int)
    start_date = datetime.now().date() - timedelta(days=days)
    
    # Documentation rate
    total_visits = Visit.query.filter(Visit.visit_date >= start_date).count()
    visits_with_notes = Visit.query.join(ClinicalNote).filter(
        Visit.visit_date >= start_date
    ).count()
    
    documentation_rate = (visits_with_notes / total_visits * 100) if total_visits > 0 else 0
    
    # Referral acceptance rate
    total_referrals = Referral.query.filter(Referral.referral_date >= start_date).count()
    accepted_referrals = Referral.query.filter(
        Referral.referral_date >= start_date,
        Referral.status == 'accepted'
    ).count()
    
    referral_acceptance_rate = (accepted_referrals / total_referrals * 100) if total_referrals > 0 else 0
    
    return jsonify({
        'documentation_rate': round(documentation_rate, 1),
        'referral_acceptance_rate': round(referral_acceptance_rate, 1),
        'total_visits': total_visits,
        'total_referrals': total_referrals
    })

@medical_admin_bp.route('/api/provider-performance')
@login_required
@require_permission('medical_admin.view')
def api_provider_performance():
    """Get provider performance data"""
    days = request.args.get('days', 30, type=int)
    start_date = datetime.now().date() - timedelta(days=days)
    
    providers = Staff.query.filter(Staff.role.has(name='physician')).all()
    performance_data = []
    
    for provider in providers:
        visits_count = Visit.query.filter(
            Visit.provider_id == provider.id,
            Visit.visit_date >= start_date
        ).count()
        
        notes_count = ClinicalNote.query.filter(
            ClinicalNote.provider_id == provider.id,
            ClinicalNote.created_at >= start_date
        ).count()
        
        performance_data.append({
            'provider_name': provider.full_name,
            'visits_count': visits_count,
            'notes_count': notes_count
        })
    
    return jsonify({'providers': performance_data})

@medical_admin_bp.route('/api/revenue-trends')
@login_required
@require_permission('medical_admin.view')
def api_revenue_trends():
    """Get revenue trends"""
    days = request.args.get('days', 30, type=int)
    start_date = datetime.now().date() - timedelta(days=days)
    
    # Get daily revenue for the period
    daily_revenue = db.session.query(
        Payment.payment_date,
        db.func.sum(Payment.amount).label('total')
    ).filter(
        Payment.payment_date >= start_date
    ).group_by(Payment.payment_date).order_by(Payment.payment_date).all()
    
    return jsonify({
        'daily_revenue': [
            {'date': str(day), 'amount': float(total)} 
            for day, total in daily_revenue
        ]
    })
