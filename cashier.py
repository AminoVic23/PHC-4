"""
Cashier routes for billing and payments
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.billing import Invoice, InvoiceItem, Payment, PriceList
from app.models.visits import Visit
from app.models.patients import Patient
from app.security import require_permission, audit_log
from datetime import datetime, timedelta
import json

cashier_bp = Blueprint('cashier', __name__)

@cashier_bp.route('/')
@login_required
@require_permission('invoice_read')
def index():
    """Cashier dashboard"""
    today = datetime.now().date()
    
    # Get pending invoices
    pending_invoices = Invoice.get_pending_invoices()
    
    # Get today's payments
    today_payments = Payment.query.filter(
        db.func.date(Payment.paid_at) == today
    ).all()
    
    # Calculate today's revenue
    today_revenue = sum(payment.amount for payment in today_payments)
    
    # Get recent invoices
    recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(10).all()
    
    return render_template('cashier/index.html',
                         pending_invoices=pending_invoices,
                         today_payments=today_payments,
                         today_revenue=today_revenue,
                         recent_invoices=recent_invoices)

@cashier_bp.route('/invoices')
@login_required
@require_permission('invoice_read')
def invoices():
    """Invoices list"""
    status = request.args.get('status', 'pending')
    
    if status == 'pending':
        invoices = Invoice.get_pending_invoices()
    elif status == 'paid':
        invoices = Invoice.query.filter_by(status='paid')\
                               .order_by(Invoice.paid_at.desc())\
                               .limit(50).all()
    else:
        invoices = Invoice.query.order_by(Invoice.created_at.desc())\
                               .limit(50).all()
    
    return render_template('cashier/invoices.html', invoices=invoices, status=status)

@cashier_bp.route('/invoices/<int:invoice_id>')
@login_required
@require_permission('invoice_read')
def invoice_detail(invoice_id):
    """Invoice detail"""
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Get invoice items
    items = invoice.items.all()
    
    # Get payments
    payments = Payment.get_payments_by_invoice(invoice_id)
    
    return render_template('cashier/invoice_detail.html', 
                         invoice=invoice, items=items, payments=payments)

@cashier_bp.route('/invoices/<int:invoice_id>/payment', methods=['GET', 'POST'])
@login_required
@require_permission('payment_process')
def process_payment(invoice_id):
    """Process payment for invoice"""
    invoice = Invoice.query.get_or_404(invoice_id)
    
    if invoice.status == 'void':
        flash('Cannot process payment for voided invoice.', 'error')
        return redirect(url_for('cashier.invoice_detail', invoice_id=invoice_id))
    
    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount'))
            method = request.form.get('method')
            reference_no = request.form.get('reference_no')
            notes = request.form.get('notes')
            
            # Validate payment amount
            if amount <= 0:
                flash('Payment amount must be greater than zero.', 'error')
                return redirect(url_for('cashier.process_payment', invoice_id=invoice_id))
            
            if amount > invoice.balance_due:
                flash('Payment amount cannot exceed balance due.', 'error')
                return redirect(url_for('cashier.process_payment', invoice_id=invoice_id))
            
            # Create payment record
            payment = Payment(
                invoice_id=invoice_id,
                method=method,
                amount=amount,
                reference_no=reference_no,
                cashier_id=current_user.id,
                notes=notes
            )
            
            db.session.add(payment)
            
            # Check if invoice is fully paid
            if invoice.balance_due - amount <= 0:
                invoice.mark_as_paid()
            
            db.session.commit()
            
            audit_log('payment_process', 'Payment', payment.id, 
                     after_data=payment.to_dict())
            
            flash('Payment processed successfully!', 'success')
            return redirect(url_for('cashier.invoice_detail', invoice_id=invoice_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error processing payment: {str(e)}', 'error')
    
    return render_template('cashier/process_payment.html', invoice=invoice)

@cashier_bp.route('/invoices/new', methods=['GET', 'POST'])
@login_required
@require_permission('invoice_create')
def new_invoice():
    """Create new invoice"""
    if request.method == 'POST':
        try:
            visit_id = request.form.get('visit_id')
            payer_type = request.form.get('payer_type', 'cash')
            
            # Get visit
            visit = Visit.query.get_or_404(visit_id)
            
            # Create invoice
            invoice = Invoice(
                visit_id=visit_id,
                patient_id=visit.patient_id,
                payer_type=payer_type,
                notes=request.form.get('notes')
            )
            
            db.session.add(invoice)
            db.session.flush()  # Get invoice ID
            
            # Add invoice items
            service_codes = request.form.getlist('service_code[]')
            descriptions = request.form.getlist('description[]')
            qtys = request.form.getlist('qty[]')
            unit_prices = request.form.getlist('unit_price[]')
            
            for i in range(len(service_codes)):
                if service_codes[i] and descriptions[i]:
                    item = InvoiceItem(
                        invoice_id=invoice.id,
                        service_code=service_codes[i],
                        description=descriptions[i],
                        qty=int(qtys[i]) if qtys[i] else 1,
                        unit_price=float(unit_prices[i]) if unit_prices[i] else 0
                    )
                    item.calculate_amount()
                    db.session.add(item)
            
            # Calculate totals
            invoice.calculate_totals()
            
            db.session.commit()
            
            audit_log('invoice_create', 'Invoice', invoice.id, 
                     after_data=invoice.to_dict())
            
            flash('Invoice created successfully!', 'success')
            return redirect(url_for('cashier.invoice_detail', invoice_id=invoice.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating invoice: {str(e)}', 'error')
    
    # Get visits and services for form
    visits = Visit.query.filter_by(status='closed').order_by(Visit.closed_at.desc()).limit(20).all()
    services = PriceList.get_active_services()
    
    return render_template('cashier/new_invoice.html', visits=visits, services=services)

@cashier_bp.route('/invoices/<int:invoice_id>/finalize', methods=['POST'])
@login_required
@require_permission('invoice_finalize')
def finalize_invoice(invoice_id):
    """Finalize an invoice"""
    invoice = Invoice.query.get_or_404(invoice_id)
    
    if invoice.status != 'draft':
        flash('Only draft invoices can be finalized.', 'error')
        return redirect(url_for('cashier.invoice_detail', invoice_id=invoice_id))
    
    try:
        before_data = invoice.to_dict()
        invoice.finalize_invoice()
        db.session.commit()
        
        audit_log('invoice_finalize', 'Invoice', invoice.id, 
                 before_data=before_data, after_data=invoice.to_dict())
        
        flash('Invoice finalized successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error finalizing invoice: {str(e)}', 'error')
    
    return redirect(url_for('cashier.invoice_detail', invoice_id=invoice_id))

@cashier_bp.route('/invoices/<int:invoice_id>/void', methods=['POST'])
@login_required
@require_permission('invoice_finalize')
def void_invoice(invoice_id):
    """Void an invoice"""
    invoice = Invoice.query.get_or_404(invoice_id)
    
    if invoice.status == 'paid':
        flash('Cannot void a paid invoice.', 'error')
        return redirect(url_for('cashier.invoice_detail', invoice_id=invoice_id))
    
    try:
        before_data = invoice.to_dict()
        invoice.void_invoice()
        db.session.commit()
        
        audit_log('invoice_void', 'Invoice', invoice.id, 
                 before_data=before_data, after_data=invoice.to_dict())
        
        flash('Invoice voided successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error voiding invoice: {str(e)}', 'error')
    
    return redirect(url_for('cashier.invoice_detail', invoice_id=invoice_id))

@cashier_bp.route('/payments')
@login_required
@require_permission('payment_process')
def payments():
    """Payments list"""
    date = request.args.get('date')
    if date:
        date = datetime.strptime(date, '%Y-%m-%d').date()
    else:
        date = datetime.now().date()
    
    payments = Payment.query.filter(
        db.func.date(Payment.paid_at) == date
    ).order_by(Payment.paid_at.desc()).all()
    
    return render_template('cashier/payments.html', payments=payments, selected_date=date)

@cashier_bp.route('/payments/<int:payment_id>')
@login_required
@require_permission('payment_process')
def payment_detail(payment_id):
    """Payment detail"""
    payment = Payment.query.get_or_404(payment_id)
    
    return render_template('cashier/payment_detail.html', payment=payment)

@cashier_bp.route('/patients/<int:patient_id>/billing')
@login_required
@require_permission('patient_read')
def patient_billing(patient_id):
    """Patient billing history"""
    patient = Patient.query.get_or_404(patient_id)
    
    # Get patient's invoices
    invoices = Invoice.get_invoices_by_patient(patient_id)
    
    # Get patient's payments
    payments = Payment.query.join(Invoice)\
                           .filter(Invoice.patient_id == patient_id)\
                           .order_by(Payment.paid_at.desc())\
                           .limit(20).all()
    
    return render_template('cashier/patient_billing.html',
                         patient=patient,
                         invoices=invoices,
                         payments=payments)

@cashier_bp.route('/reports/daily')
@login_required
@require_permission('reports_view')
def daily_report():
    """Daily cashier report"""
    date = request.args.get('date')
    if date:
        date = datetime.strptime(date, '%Y-%m-%d').date()
    else:
        date = datetime.now().date()
    
    # Get payments for the date
    payments = Payment.query.filter(
        db.func.date(Payment.paid_at) == date
    ).order_by(Payment.paid_at).all()
    
    # Calculate totals by payment method
    method_totals = {}
    total_revenue = 0
    
    for payment in payments:
        method = payment.method
        if method not in method_totals:
            method_totals[method] = 0
        method_totals[method] += float(payment.amount)
        total_revenue += float(payment.amount)
    
    # Get invoices finalized on the date
    invoices = Invoice.query.filter(
        db.func.date(Invoice.finalized_at) == date
    ).all()
    
    return render_template('cashier/daily_report.html',
                         date=date,
                         payments=payments,
                         method_totals=method_totals,
                         total_revenue=total_revenue,
                         invoices=invoices)

# API endpoints
@cashier_bp.route('/api/visits/search')
@login_required
@require_permission('invoice_create')
def api_visit_search():
    """Search visits for invoice creation"""
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    
    visits = Visit.query.filter(
        db.or_(
            Visit.visit_no.ilike(f'%{query}%'),
            Visit.patient.has(Patient.first_name.ilike(f'%{query}%')),
            Visit.patient.has(Patient.last_name.ilike(f'%{query}%'))
        ),
        Visit.status == 'closed'
    ).limit(10).all()
    
    return jsonify([{
        'id': v.id,
        'visit_no': v.visit_no,
        'patient_name': v.patient.full_name if v.patient else None,
        'visit_date': v.visit_date.isoformat() if v.visit_date else None,
        'clinic_name': v.clinic.name if v.clinic else None
    } for v in visits])

@cashier_bp.route('/api/services/search')
@login_required
@require_permission('invoice_create')
def api_service_search():
    """Search services for invoice items"""
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    
    services = PriceList.query.filter(
        db.or_(
            PriceList.service_code.ilike(f'%{query}%'),
            PriceList.description.ilike(f'%{query}%')
        ),
        PriceList.active == True
    ).limit(10).all()
    
    return jsonify([{
        'id': s.id,
        'service_code': s.service_code,
        'description': s.description,
        'unit_price': float(s.unit_price) if s.unit_price else 0,
        'category': s.category
    } for s in services])

@cashier_bp.route('/api/invoices/pending')
@login_required
@require_permission('invoice_read')
def api_pending_invoices():
    """Get pending invoices for AJAX"""
    invoices = Invoice.get_pending_invoices()
    return jsonify([{
        'id': i.id,
        'invoice_no': i.invoice_no,
        'patient_name': i.patient.full_name if i.patient else None,
        'net_amount': float(i.net_amount) if i.net_amount else 0,
        'balance_due': float(i.balance_due),
        'finalized_at': i.finalized_at.isoformat() if i.finalized_at else None
    } for i in invoices])
