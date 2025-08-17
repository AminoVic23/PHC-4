"""
Higher Authority dashboard for multi-facility comparison and oversight
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import (Facility, Visit, ClinicalNote, Order, LabResult, RadiologyReport,
                       Prescription, Invoice, Payment, Referral, QualityIncident,
                       Survey, Staff, Department, Patient, Asset, WorkOrder, Ticket)
from app.extensions import db
from app.security import require_permission, audit_log, require_role
from app.utils.session import get_current_facility_id
from datetime import datetime, timedelta
import json

higher_authority_bp = Blueprint('higher_authority', __name__, url_prefix='/higher-authority')

@higher_authority_bp.route('/')
@login_required
@require_role('superadmin')
def index():
    """Higher authority dashboard - overview of all facilities"""
    # Get date range for comparison
    start_date = request.args.get('start_date', 
                                 (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    # Get all facilities
    facilities = Facility.get_active_facilities()
    
    # Get facility statistics
    facility_stats = []
    for facility in facilities:
        stats = get_facility_statistics(facility.id, start_date, end_date)
        facility_stats.append({
            'facility': facility,
            'stats': stats
        })
    
    # Get overall statistics
    overall_stats = get_overall_statistics(start_date, end_date)
    
    return render_template('higher_authority/dashboard.html',
                         facility_stats=facility_stats,
                         overall_stats=overall_stats,
                         start_date=start_date,
                         end_date=end_date)

@higher_authority_bp.route('/facility-comparison')
@login_required
@require_role('superadmin')
def facility_comparison():
    """Facility comparison dashboard"""
    # Get date range
    start_date = request.args.get('start_date', 
                                 (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    # Get selected facilities for comparison
    facility_ids = request.args.getlist('facility_ids')
    if not facility_ids:
        # Default to all facilities
        facilities = Facility.get_active_facilities()
        facility_ids = [f.id for f in facilities]
    else:
        facility_ids = [int(fid) for fid in facility_ids]
        facilities = Facility.query.filter(Facility.id.in_(facility_ids)).all()
    
    # Get comparison data
    comparison_data = []
    for facility in facilities:
        data = get_facility_comparison_data(facility.id, start_date, end_date)
        comparison_data.append({
            'facility': facility,
            'data': data
        })
    
    # Get all facilities for selection
    all_facilities = Facility.get_active_facilities()
    
    return render_template('higher_authority/facility_comparison.html',
                         comparison_data=comparison_data,
                         all_facilities=all_facilities,
                         selected_facility_ids=facility_ids,
                         start_date=start_date,
                         end_date=end_date)

@higher_authority_bp.route('/time-period-comparison')
@login_required
@require_role('superadmin')
def time_period_comparison():
    """Compare performance across different time periods"""
    # Get time periods
    current_period_start = request.args.get('current_start', 
                                           (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    current_period_end = request.args.get('current_end', datetime.now().strftime('%Y-%m-%d'))
    previous_period_start = request.args.get('previous_start', 
                                           (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d'))
    previous_period_end = request.args.get('previous_end', 
                                         (datetime.now() - timedelta(days=31)).strftime('%Y-%m-%d'))
    
    # Get facility for comparison (or all facilities)
    facility_id = request.args.get('facility_id', type=int)
    
    if facility_id:
        facilities = [Facility.query.get(facility_id)]
    else:
        facilities = Facility.get_active_facilities()
    
    comparison_data = []
    for facility in facilities:
        current_data = get_facility_statistics(facility.id, current_period_start, current_period_end)
        previous_data = get_facility_statistics(facility.id, previous_period_start, previous_period_end)
        
        comparison_data.append({
            'facility': facility,
            'current_period': current_data,
            'previous_period': previous_data,
            'change_percentage': calculate_change_percentage(current_data, previous_data)
        })
    
    return render_template('higher_authority/time_period_comparison.html',
                         comparison_data=comparison_data,
                         current_period_start=current_period_start,
                         current_period_end=current_period_end,
                         previous_period_start=previous_period_start,
                         previous_period_end=previous_period_end,
                         facility_id=facility_id)

@higher_authority_bp.route('/performance-metrics')
@login_required
@require_role('superadmin')
def performance_metrics():
    """Detailed performance metrics across facilities"""
    # Get date range
    start_date = request.args.get('start_date', 
                                 (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    # Get metrics by facility
    facilities = Facility.get_active_facilities()
    metrics_data = []
    
    for facility in facilities:
        metrics = get_facility_performance_metrics(facility.id, start_date, end_date)
        metrics_data.append({
            'facility': facility,
            'metrics': metrics
        })
    
    return render_template('higher_authority/performance_metrics.html',
                         metrics_data=metrics_data,
                         start_date=start_date,
                         end_date=end_date)

@higher_authority_bp.route('/reports')
@login_required
@require_role('superadmin')
def reports():
    """Comprehensive reports for higher authority"""
    # Get date range
    start_date = request.args.get('start_date', 
                                 (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    # Get report type
    report_type = request.args.get('type', 'overview')
    
    if report_type == 'financial':
        report_data = get_financial_report(start_date, end_date)
    elif report_type == 'clinical':
        report_data = get_clinical_report(start_date, end_date)
    elif report_type == 'operational':
        report_data = get_operational_report(start_date, end_date)
    else:
        report_data = get_overview_report(start_date, end_date)
    
    return render_template('higher_authority/reports.html',
                         report_data=report_data,
                         report_type=report_type,
                         start_date=start_date,
                         end_date=end_date)

# Helper functions
def get_facility_statistics(facility_id, start_date, end_date):
    """Get comprehensive statistics for a facility"""
    start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Patient statistics
    total_patients = Patient.query.filter_by(facility_id=facility_id).count()
    new_patients = Patient.query.filter(
        Patient.facility_id == facility_id,
        Patient.created_at >= start_dt,
        Patient.created_at <= end_dt
    ).count()
    
    # Visit statistics
    total_visits = Visit.query.filter(
        Visit.facility_id == facility_id,
        Visit.visit_date >= start_dt,
        Visit.visit_date <= end_dt
    ).count()
    
    completed_visits = Visit.query.filter(
        Visit.facility_id == facility_id,
        Visit.visit_date >= start_dt,
        Visit.visit_date <= end_dt,
        Visit.status == 'closed'
    ).count()
    
    # Financial statistics
    total_revenue = Payment.query.join(Invoice).join(Visit).filter(
        Visit.facility_id == facility_id,
        Payment.payment_date >= start_dt,
        Payment.payment_date <= end_dt
    ).with_entities(db.func.sum(Payment.amount)).scalar() or 0
    
    # Quality indicators
    total_incidents = QualityIncident.query.join(Department).filter(
        Department.facility_id == facility_id,
        QualityIncident.incident_date >= start_dt,
        QualityIncident.incident_date <= end_dt
    ).count()
    
    avg_satisfaction = Survey.query.join(Visit).filter(
        Visit.facility_id == facility_id,
        Survey.survey_date >= start_dt,
        Survey.survey_date <= end_dt
    ).with_entities(db.func.avg(Survey.overall_rating)).scalar() or 0
    
    return {
        'total_patients': total_patients,
        'new_patients': new_patients,
        'total_visits': total_visits,
        'completed_visits': completed_visits,
        'completion_rate': (completed_visits / total_visits * 100) if total_visits > 0 else 0,
        'total_revenue': total_revenue,
        'total_incidents': total_incidents,
        'avg_satisfaction': round(avg_satisfaction, 1)
    }

def get_overall_statistics(start_date, end_date):
    """Get overall statistics across all facilities"""
    start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Overall totals
    total_patients = Patient.query.count()
    total_visits = Visit.query.filter(
        Visit.visit_date >= start_dt,
        Visit.visit_date <= end_dt
    ).count()
    
    total_revenue = Payment.query.filter(
        Payment.payment_date >= start_dt,
        Payment.payment_date <= end_dt
    ).with_entities(db.func.sum(Payment.amount)).scalar() or 0
    
    total_incidents = QualityIncident.query.filter(
        QualityIncident.incident_date >= start_dt,
        QualityIncident.incident_date <= end_dt
    ).count()
    
    avg_satisfaction = Survey.query.filter(
        Survey.survey_date >= start_dt,
        Survey.survey_date <= end_dt
    ).with_entities(db.func.avg(Survey.overall_rating)).scalar() or 0
    
    return {
        'total_patients': total_patients,
        'total_visits': total_visits,
        'total_revenue': total_revenue,
        'total_incidents': total_incidents,
        'avg_satisfaction': round(avg_satisfaction, 1)
    }

def get_facility_comparison_data(facility_id, start_date, end_date):
    """Get detailed comparison data for a facility"""
    stats = get_facility_statistics(facility_id, start_date, end_date)
    
    # Add additional metrics
    start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Staff productivity
    staff_count = Staff.query.join(StaffFacility).filter(
        StaffFacility.facility_id == facility_id,
        Staff.active == True
    ).count()
    
    visits_per_staff = stats['total_visits'] / staff_count if staff_count > 0 else 0
    
    # Revenue per visit
    revenue_per_visit = stats['total_revenue'] / stats['total_visits'] if stats['total_visits'] > 0 else 0
    
    return {
        **stats,
        'staff_count': staff_count,
        'visits_per_staff': round(visits_per_staff, 1),
        'revenue_per_visit': round(revenue_per_visit, 2)
    }

def calculate_change_percentage(current_data, previous_data):
    """Calculate percentage change between two periods"""
    changes = {}
    
    for key in current_data:
        if key in previous_data and previous_data[key] != 0:
            current_val = current_data[key]
            previous_val = previous_data[key]
            change = ((current_val - previous_val) / previous_val) * 100
            changes[key] = round(change, 1)
        else:
            changes[key] = 0
    
    return changes

def get_facility_performance_metrics(facility_id, start_date, end_date):
    """Get detailed performance metrics for a facility"""
    start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Clinical metrics
    total_visits = Visit.query.filter(
        Visit.facility_id == facility_id,
        Visit.visit_date >= start_dt,
        Visit.visit_date <= end_dt
    ).count()
    
    visits_with_notes = Visit.query.join(ClinicalNote).filter(
        Visit.facility_id == facility_id,
        Visit.visit_date >= start_dt,
        Visit.visit_date <= end_dt
    ).count()
    
    documentation_rate = (visits_with_notes / total_visits * 100) if total_visits > 0 else 0
    
    # Financial metrics
    total_revenue = Payment.query.join(Invoice).join(Visit).filter(
        Visit.facility_id == facility_id,
        Payment.payment_date >= start_dt,
        Payment.payment_date <= end_dt
    ).with_entities(db.func.sum(Payment.amount)).scalar() or 0
    
    # Quality metrics
    total_incidents = QualityIncident.query.join(Department).filter(
        Department.facility_id == facility_id,
        QualityIncident.incident_date >= start_dt,
        QualityIncident.incident_date <= end_dt
    ).count()
    
    return {
        'documentation_rate': round(documentation_rate, 1),
        'total_revenue': total_revenue,
        'total_incidents': total_incidents,
        'incident_rate_per_visit': (total_incidents / total_visits * 100) if total_visits > 0 else 0
    }

# API endpoints
@higher_authority_bp.route('/api/facility-stats')
@login_required
@require_role('superadmin')
def api_facility_stats():
    """Get facility statistics for API"""
    start_date = request.args.get('start_date', 
                                 (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    facilities = Facility.get_active_facilities()
    stats = []
    
    for facility in facilities:
        facility_stat = get_facility_statistics(facility.id, start_date, end_date)
        stats.append({
            'facility_id': facility.id,
            'facility_name': facility.name,
            'facility_code': facility.facility_code,
            'stats': facility_stat
        })
    
    return jsonify({'facilities': stats})

@higher_authority_bp.route('/api/comparison-data')
@login_required
@require_role('superadmin')
def api_comparison_data():
    """Get comparison data for API"""
    start_date = request.args.get('start_date', 
                                 (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    facility_ids = request.args.getlist('facility_ids')
    if not facility_ids:
        facilities = Facility.get_active_facilities()
        facility_ids = [f.id for f in facilities]
    else:
        facility_ids = [int(fid) for fid in facility_ids]
        facilities = Facility.query.filter(Facility.id.in_(facility_ids)).all()
    
    comparison_data = []
    for facility in facilities:
        data = get_facility_comparison_data(facility.id, start_date, end_date)
        comparison_data.append({
            'facility_id': facility.id,
            'facility_name': facility.name,
            'facility_code': facility.facility_code,
            'data': data
        })
    
    return jsonify({'comparison_data': comparison_data})
