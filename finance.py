"""
Finance routes for financial management
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.billing import Invoice, Payment, PriceList, InsurancePolicy, Claim
from app.models.visits import Visit
from app.models.patients import Patient
from app.security import require_permission, audit_log
from datetime import datetime, timedelta
import json

finance_bp = Blueprint('finance', __name__)

@finance_bp.route('/')
@login_required
@require_permission('reports_view')
def index():
    """Finance dashboard"""
    today = datetime.now().date()
    start_of_month = today.replace(day=1)
    
    # Financial statistics
    today_revenue = db.session.query(db.func.sum(Payment.amount))\
                              .filter(db.func.date(Payment.paid_at) == today)\
                              .scalar() or 0
    
    month_revenue = db.session.query(db.func.sum(Payment.amount))\
                              .filter(Payment.paid_at >= start_of_month)\
                              .scalar() or 0
    
    pending_invoices = Invoice.query.filter_by(status='finalized').count()
    total_outstanding = db.session.query(db.func.sum(Invoice.net_amount))\
                                 .filter(Invoice.status == 'finalized')\
                                 .scalar() or 0
    
    # Insurance statistics
    active_policies = InsurancePolicy.query.filter_by(active=True).count()
    pending_claims = Claim.query.filter_by(status='pending').count()
    
    # Recent transactions
    recent_payments = Payment.query.order_by(Payment.paid_at.desc()).limit(10).all()
    recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(10).all()
    
    return render_template('finance/index.html',
                         today_revenue=today_revenue,
                         month_revenue=month_revenue,
                         pending_invoices=pending_invoices,
                         total_outstanding=total_outstanding,
                         active_policies=active_policies,
                         pending_claims=pending_claims,
                         recent_payments=recent_payments,
                         recent_invoices=recent_invoices)

@finance_bp.route('/pricing')
@login_required
@require_permission('settings_manage')
def pricing():
    """Price list management"""
    services = PriceList.get_active_services()
    
    return render_template('finance/pricing.html', services=services)

@finance_bp.route('/pricing/new', methods=['GET', 'POST'])
@login_required
@require_permission('settings_manage')
def new_service():
    """Create new service"""
    if request.method == 'POST':
        try:
            # Create service
            service = PriceList(
                service_code=request.form.get('service_code'),
                description=request.form.get('description'),
                department_id=request.form.get('department_id'),
                unit_price=float(request.form.get('unit_price')),
                category=request.form.get('category')
            )
            
            db.session.add(service)
            db.session.commit()
            
            audit_log('service_create', 'PriceList', service.id, 
                     after_data=service.to_dict())
            
            flash('Service created successfully!', 'success')
            return redirect(url_for('finance.pricing'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating service: {str(e)}', 'error')
    
    # Get departments for form
    from app.models.departments import Department
    departments = Department.get_active_departments()
    
    return render_template('finance/new_service.html', departments=departments)

@finance_bp.route('/pricing/<int:service_id>/edit', methods=['GET', 'POST'])
@login_required
@require_permission('settings_manage')
def edit_service(service_id):
    """Edit service"""
    service = PriceList.query.get_or_404(service_id)
    
    if request.method == 'POST':
        try:
            before_data = service.to_dict()
            
            # Update service fields
            service.description = request.form.get('description')
            service.department_id = request.form.get('department_id')
            service.unit_price = float(request.form.get('unit_price'))
            service.category = request.form.get('category')
            
            db.session.commit()
            
            audit_log('service_update', 'PriceList', service.id, 
                     before_data=before_data, after_data=service.to_dict())
            
            flash('Service updated successfully!', 'success')
            return redirect(url_for('finance.pricing'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating service: {str(e)}', 'error')
    
    # Get departments for form
    from app.models.departments import Department
    departments = Department.get_active_departments()
    
    return render_template('finance/edit_service.html', service=service, departments=departments)

@finance_bp.route('/insurance')
@login_required
@require_permission('claims_manage')
def insurance():
    """Insurance management"""
    policies = InsurancePolicy.query.order_by(InsurancePolicy.created_at.desc()).limit(50).all()
    
    return render_template('finance/insurance.html', policies=policies)

@finance_bp.route('/insurance/<int:policy_id>')
@login_required
@require_permission('claims_manage')
def policy_detail(policy_id):
    """Insurance policy detail"""
    policy = InsurancePolicy.query.get_or_404(policy_id)
    
    # Get claims for this policy
    claims = policy.claims
    
    return render_template('finance/policy_detail.html', policy=policy, claims=claims)

@finance_bp.route('/claims')
@login_required
@require_permission('claims_manage')
def claims():
    """Insurance claims management"""
    status = request.args.get('status', 'all')
    
    if status == 'all':
        claims = Claim.query.order_by(Claim.created_at.desc()).limit(50).all()
    else:
        claims = Claim.query.filter_by(status=status)\
                          .order_by(Claim.created_at.desc())\
                          .limit(50).all()
    
    return render_template('finance/claims.html', claims=claims, status=status)

@finance_bp.route('/claims/<int:claim_id>')
@login_required
@require_permission('claims_manage')
def claim_detail(claim_id):
    """Insurance claim detail"""
    claim = Claim.query.get_or_404(claim_id)
    
    return render_template('finance/claim_detail.html', claim=claim)

@finance_bp.route('/claims/<int:claim_id>/submit', methods=['POST'])
@login_required
@require_permission('claims_manage')
def submit_claim(claim_id):
    """Submit insurance claim"""
    claim = Claim.query.get_or_404(claim_id)
    
    if claim.status != 'draft':
        flash('Only draft claims can be submitted.', 'error')
        return redirect(url_for('finance.claim_detail', claim_id=claim_id))
    
    try:
        before_data = claim.to_dict()
        claim.submit_claim()
        claim.submitted_by_id = current_user.id
        db.session.commit()
        
        audit_log('claim_submit', 'Claim', claim.id, 
                 before_data=before_data, after_data=claim.to_dict())
        
        flash('Claim submitted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error submitting claim: {str(e)}', 'error')
    
    return redirect(url_for('finance.claim_detail', claim_id=claim_id))

@finance_bp.route('/reports/revenue')
@login_required
@require_permission('reports_view')
def revenue_report():
    """Revenue report"""
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
    
    # Revenue by department
    revenue_by_department = db.session.query(
        db.func.coalesce(db.func.string_agg('departments.name', ', '), 'Unknown').label('department'),
        db.func.sum(Invoice.net_amount).label('amount')
    ).join(Invoice, db.func.departments.id == Invoice.visit.has(Visit.clinic_id))\
     .filter(
        Invoice.created_at >= start_date,
        Invoice.created_at <= end_date + timedelta(days=1)
    ).group_by(Invoice.visit.has(Visit.clinic_id)).all()
    
    return render_template('finance/revenue_report.html',
                         revenue_by_date=revenue_by_date,
                         revenue_by_method=revenue_by_method,
                         revenue_by_department=revenue_by_department,
                         start_date=start_date,
                         end_date=end_date)

@finance_bp.route('/reports/outstanding')
@login_required
@require_permission('reports_view')
def outstanding_report():
    """Outstanding invoices report"""
    # Outstanding invoices
    outstanding_invoices = Invoice.query.filter_by(status='finalized')\
                                      .order_by(Invoice.finalized_at.desc()).all()
    
    # Outstanding by patient
    outstanding_by_patient = db.session.query(
        Patient.full_name,
        db.func.sum(Invoice.net_amount).label('amount'),
        db.func.count(Invoice.id).label('count')
    ).join(Invoice, Patient.id == Invoice.patient_id)\
     .filter(Invoice.status == 'finalized')\
     .group_by(Patient.id, Patient.full_name)\
     .order_by(db.func.sum(Invoice.net_amount).desc()).all()
    
    # Outstanding by age
    outstanding_by_age = db.session.query(
        db.func.sum(Invoice.net_amount).label('amount')
    ).join(Patient, Invoice.patient_id == Patient.id)\
     .filter(
        Invoice.status == 'finalized',
        db.func.extract('year', db.func.age(Patient.dob)) < 30
    ).scalar() or 0
    
    return render_template('finance/outstanding_report.html',
                         outstanding_invoices=outstanding_invoices,
                         outstanding_by_patient=outstanding_by_patient,
                         outstanding_by_age=outstanding_by_age)

# API endpoints
@finance_bp.route('/api/revenue/daily')
@login_required
@require_permission('reports_view')
def api_daily_revenue():
    """Get daily revenue for charts"""
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

@finance_bp.route('/api/revenue/method')
@login_required
@require_permission('reports_view')
def api_revenue_by_method():
    """Get revenue by payment method"""
    days = int(request.args.get('days', 30))
    start_date = datetime.now().date() - timedelta(days=days)
    
    data = db.session.query(
        Payment.method,
        db.func.sum(Payment.amount).label('amount')
    ).filter(
        Payment.paid_at >= start_date
    ).group_by(Payment.method).all()
    
    return jsonify([{
        'method': row.method,
        'amount': float(row.amount) if row.amount else 0
    } for row in data])
