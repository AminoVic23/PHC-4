"""
Radiology routes for imaging operations
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.orders import Order, RadiologyReport
from app.models.visits import Visit
from app.models.patients import Patient
from app.security import require_permission, audit_log
from datetime import datetime, timedelta
import json

radiology_bp = Blueprint('radiology', __name__)

@radiology_bp.route('/')
@login_required
@require_permission('orders_read')
def index():
    """Radiology dashboard"""
    today = datetime.now().date()
    
    # Get pending radiology orders
    pending_orders = Order.get_pending_orders(order_type='rad')
    
    # Get urgent orders
    urgent_orders = Order.get_urgent_orders(order_type='rad')
    
    # Get unverified reports
    unverified_reports = RadiologyReport.get_unverified_reports()
    
    return render_template('radiology/index.html',
                         pending_orders=pending_orders,
                         urgent_orders=urgent_orders,
                         unverified_reports=unverified_reports)

@radiology_bp.route('/orders')
@login_required
@require_permission('orders_read')
def orders():
    """Radiology orders list"""
    status = request.args.get('status', 'pending')
    
    if status == 'pending':
        orders = Order.get_pending_orders(order_type='rad')
    elif status == 'urgent':
        orders = Order.get_urgent_orders(order_type='rad')
    elif status == 'completed':
        orders = Order.query.filter_by(type='rad', status='reported')\
                           .order_by(Order.completed_at.desc())\
                           .limit(50).all()
    else:
        orders = Order.query.filter_by(type='rad')\
                           .order_by(Order.created_at.desc())\
                           .limit(50).all()
    
    return render_template('radiology/orders.html', orders=orders, status=status)

@radiology_bp.route('/orders/<int:order_id>')
@login_required
@require_permission('orders_read')
def order_detail(order_id):
    """Radiology order detail"""
    order = Order.query.get_or_404(order_id)
    
    if order.type != 'rad':
        flash('This is not a radiology order.', 'error')
        return redirect(url_for('radiology.orders'))
    
    # Get radiology report if exists
    radiology_report = order.radiology_report
    
    return render_template('radiology/order_detail.html', 
                         order=order, radiology_report=radiology_report)

@radiology_bp.route('/orders/<int:order_id>/start', methods=['POST'])
@login_required
@require_permission('orders_update')
def start_order(order_id):
    """Start processing a radiology order"""
    order = Order.query.get_or_404(order_id)
    
    if order.type != 'rad':
        flash('This is not a radiology order.', 'error')
        return redirect(url_for('radiology.orders'))
    
    try:
        order.start_processing()
        db.session.commit()
        
        audit_log('orders_update', 'Order', order.id, 
                 after_data={'status': 'in_progress'})
        
        flash('Order processing started!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error starting order: {str(e)}', 'error')
    
    return redirect(url_for('radiology.order_detail', order_id=order_id))

@radiology_bp.route('/orders/<int:order_id>/report', methods=['GET', 'POST'])
@login_required
@require_permission('results_post')
def post_report(order_id):
    """Post radiology report"""
    order = Order.query.get_or_404(order_id)
    
    if order.type != 'rad':
        flash('This is not a radiology order.', 'error')
        return redirect(url_for('radiology.orders'))
    
    if request.method == 'POST':
        try:
            # Create or update radiology report
            if order.radiology_report:
                report = order.radiology_report
                before_data = report.to_dict()
            else:
                report = RadiologyReport(order_id=order_id, reported_by_id=current_user.id)
                before_data = None
            
            # Update report fields
            report.modality = request.form.get('modality')
            report.report_text = request.form.get('report_text')
            report.impression = request.form.get('impression')
            report.findings = request.form.get('findings')
            report.images_link = request.form.get('images_link')
            report.notes = request.form.get('notes')
            
            if not order.radiology_report:
                db.session.add(report)
            
            # Complete the order
            order.complete_order()
            
            db.session.commit()
            
            audit_log('results_post', 'RadiologyReport', report.id, 
                     before_data=before_data, after_data=report.to_dict())
            
            flash('Radiology report posted successfully!', 'success')
            return redirect(url_for('radiology.order_detail', order_id=order_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error posting report: {str(e)}', 'error')
    
    return render_template('radiology/post_report.html', order=order)

@radiology_bp.route('/reports/<int:report_id>/verify', methods=['POST'])
@login_required
@require_permission('results_post')
def verify_report(report_id):
    """Verify a radiology report"""
    report = RadiologyReport.query.get_or_404(report_id)
    
    try:
        report.verify_report(current_user.id)
        db.session.commit()
        
        audit_log('results_verify', 'RadiologyReport', report.id, 
                 after_data={'verified_at': datetime.utcnow().isoformat()})
        
        flash('Report verified successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error verifying report: {str(e)}', 'error')
    
    return redirect(url_for('radiology.order_detail', order_id=report.order_id))

@radiology_bp.route('/reports')
@login_required
@require_permission('orders_read')
def reports():
    """Radiology reports list"""
    status = request.args.get('status', 'all')
    modality = request.args.get('modality', '')
    
    if status == 'unverified':
        reports = RadiologyReport.get_unverified_reports()
    elif modality:
        reports = RadiologyReport.get_reports_by_modality(modality)
    else:
        reports = RadiologyReport.query.order_by(RadiologyReport.reported_at.desc()).limit(50).all()
    
    return render_template('radiology/reports.html', reports=reports, status=status, modality=modality)

@radiology_bp.route('/reports/<int:report_id>')
@login_required
@require_permission('orders_read')
def report_detail(report_id):
    """Radiology report detail"""
    report = RadiologyReport.query.get_or_404(report_id)
    
    return render_template('radiology/report_detail.html', report=report)

# API endpoints
@radiology_bp.route('/api/orders/pending')
@login_required
@require_permission('orders_read')
def api_pending_orders():
    """Get pending orders for AJAX"""
    orders = Order.get_pending_orders(order_type='rad')
    return jsonify([{
        'id': o.id,
        'visit_no': o.visit.visit_no if o.visit else None,
        'patient_name': o.visit.patient.full_name if o.visit and o.visit.patient else None,
        'description': o.description,
        'priority': o.priority,
        'created_at': o.created_at.isoformat() if o.created_at else None
    } for o in orders])

@radiology_bp.route('/api/reports/unverified')
@login_required
@require_permission('orders_read')
def api_unverified_reports():
    """Get unverified reports for AJAX"""
    reports = RadiologyReport.get_unverified_reports()
    return jsonify([{
        'id': r.id,
        'modality': r.modality,
        'patient_name': r.order.visit.patient.full_name if r.order and r.order.visit and r.order.visit.patient else None,
        'reported_at': r.reported_at.isoformat() if r.reported_at else None
    } for r in reports])
