"""
Laboratory routes for lab operations
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.orders import Order, LabResult
from app.models.pharmacy import Drug, Inventory, StockMove
from app.models.visits import Visit
from app.models.patients import Patient
from app.security import require_permission, audit_log
from datetime import datetime, timedelta
import json

lab_bp = Blueprint('laboratory', __name__)

@lab_bp.route('/')
@login_required
@require_permission('orders_read')
def index():
    """Laboratory dashboard"""
    today = datetime.now().date()
    
    # Get pending lab orders
    pending_orders = Order.get_pending_orders(order_type='lab')
    
    # Get urgent orders
    urgent_orders = Order.get_urgent_orders(order_type='lab')
    
    # Get unverified results
    unverified_results = LabResult.get_unverified_results()
    
    # Get critical results
    critical_results = LabResult.get_critical_results()
    
    return render_template('laboratory/index.html',
                         pending_orders=pending_orders,
                         urgent_orders=urgent_orders,
                         unverified_results=unverified_results,
                         critical_results=critical_results)

@lab_bp.route('/orders')
@login_required
@require_permission('orders_read')
def orders():
    """Lab orders list"""
    status = request.args.get('status', 'pending')
    
    if status == 'pending':
        orders = Order.get_pending_orders(order_type='lab')
    elif status == 'urgent':
        orders = Order.get_urgent_orders(order_type='lab')
    elif status == 'completed':
        orders = Order.query.filter_by(type='lab', status='reported')\
                           .order_by(Order.completed_at.desc())\
                           .limit(50).all()
    else:
        orders = Order.query.filter_by(type='lab')\
                           .order_by(Order.created_at.desc())\
                           .limit(50).all()
    
    return render_template('laboratory/orders.html', orders=orders, status=status)

@lab_bp.route('/orders/<int:order_id>')
@login_required
@require_permission('orders_read')
def order_detail(order_id):
    """Lab order detail"""
    order = Order.query.get_or_404(order_id)
    
    if order.type != 'lab':
        flash('This is not a laboratory order.', 'error')
        return redirect(url_for('laboratory.orders'))
    
    # Get lab result if exists
    lab_result = order.lab_result
    
    return render_template('laboratory/order_detail.html', 
                         order=order, lab_result=lab_result)

@lab_bp.route('/orders/<int:order_id>/start', methods=['POST'])
@login_required
@require_permission('orders_update')
def start_order(order_id):
    """Start processing a lab order"""
    order = Order.query.get_or_404(order_id)
    
    if order.type != 'lab':
        flash('This is not a laboratory order.', 'error')
        return redirect(url_for('laboratory.orders'))
    
    try:
        order.start_processing()
        db.session.commit()
        
        audit_log('orders_update', 'Order', order.id, 
                 after_data={'status': 'in_progress'})
        
        flash('Order processing started!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error starting order: {str(e)}', 'error')
    
    return redirect(url_for('laboratory.order_detail', order_id=order_id))

@lab_bp.route('/orders/<int:order_id>/result', methods=['GET', 'POST'])
@login_required
@require_permission('results_post')
def post_result(order_id):
    """Post lab result"""
    order = Order.query.get_or_404(order_id)
    
    if order.type != 'lab':
        flash('This is not a laboratory order.', 'error')
        return redirect(url_for('laboratory.orders'))
    
    if request.method == 'POST':
        try:
            # Create or update lab result
            if order.lab_result:
                result = order.lab_result
                before_data = result.to_dict()
            else:
                result = LabResult(order_id=order_id, reported_by_id=current_user.id)
                before_data = None
            
            # Update result fields
            result.analyte = request.form.get('analyte')
            result.value = request.form.get('value')
            result.unit = request.form.get('unit')
            result.ref_range = request.form.get('ref_range')
            result.flag = request.form.get('flag')
            result.method = request.form.get('method')
            result.instrument = request.form.get('instrument')
            result.notes = request.form.get('notes')
            
            if not order.lab_result:
                db.session.add(result)
            
            # Complete the order
            order.complete_order()
            
            db.session.commit()
            
            audit_log('results_post', 'LabResult', result.id, 
                     before_data=before_data, after_data=result.to_dict())
            
            flash('Lab result posted successfully!', 'success')
            return redirect(url_for('laboratory.order_detail', order_id=order_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error posting result: {str(e)}', 'error')
    
    return render_template('laboratory/post_result.html', order=order)

@lab_bp.route('/results/<int:result_id>/verify', methods=['POST'])
@login_required
@require_permission('results_post')
def verify_result(result_id):
    """Verify a lab result"""
    result = LabResult.query.get_or_404(result_id)
    
    try:
        result.verify_result(current_user.id)
        db.session.commit()
        
        audit_log('results_verify', 'LabResult', result.id, 
                 after_data={'verified_at': datetime.utcnow().isoformat()})
        
        flash('Result verified successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error verifying result: {str(e)}', 'error')
    
    return redirect(url_for('laboratory.order_detail', order_id=result.order_id))

@lab_bp.route('/results')
@login_required
@require_permission('orders_read')
def results():
    """Lab results list"""
    status = request.args.get('status', 'all')
    analyte = request.args.get('analyte', '')
    
    if status == 'unverified':
        results = LabResult.get_unverified_results()
    elif status == 'critical':
        results = LabResult.get_critical_results()
    elif analyte:
        results = LabResult.get_results_by_analyte(analyte)
    else:
        results = LabResult.query.order_by(LabResult.reported_at.desc()).limit(50).all()
    
    return render_template('laboratory/results.html', results=results, status=status, analyte=analyte)

@lab_bp.route('/inventory')
@login_required
@require_permission('inventory_manage')
def inventory():
    """Laboratory inventory management"""
    # Get lab supplies (drugs used in lab)
    lab_supplies = Drug.query.filter(
        Drug.therapeutic_class.contains('Laboratory'),
        Drug.active == True
    ).all()
    
    # Get low stock items
    low_stock_items = Inventory.get_low_stock_items()
    
    # Get expiring items
    expiring_items = Inventory.get_expiring_items(days=30)
    
    return render_template('laboratory/inventory.html',
                         lab_supplies=lab_supplies,
                         low_stock_items=low_stock_items,
                         expiring_items=expiring_items)

@lab_bp.route('/inventory/<int:drug_id>')
@login_required
@require_permission('inventory_manage')
def drug_inventory(drug_id):
    """Drug inventory detail"""
    drug = Drug.query.get_or_404(drug_id)
    inventory_items = drug.inventory_items.all()
    stock_moves = StockMove.get_drug_moves(drug_id)
    
    return render_template('laboratory/drug_inventory.html',
                         drug=drug,
                         inventory_items=inventory_items,
                         stock_moves=stock_moves)

@lab_bp.route('/inventory/<int:drug_id>/add', methods=['GET', 'POST'])
@login_required
@require_permission('inventory_manage')
def add_stock(drug_id):
    """Add stock to inventory"""
    drug = Drug.query.get_or_404(drug_id)
    
    if request.method == 'POST':
        try:
            qty = int(request.form.get('qty'))
            batch_no = request.form.get('batch_no')
            expiry_dt = datetime.strptime(request.form.get('expiry_dt'), '%Y-%m-%d').date()
            cost_price = float(request.form.get('cost_price', 0))
            location_id = int(request.form.get('location_id'))
            
            # Find or create inventory item
            inventory_item = Inventory.query.filter_by(
                drug_id=drug_id,
                location_id=location_id
            ).first()
            
            if not inventory_item:
                inventory_item = Inventory(
                    drug_id=drug_id,
                    location_id=location_id,
                    on_hand=0,
                    reorder_level=int(request.form.get('reorder_level', 0)),
                    reorder_qty=int(request.form.get('reorder_qty', 0))
                )
                db.session.add(inventory_item)
            
            # Add stock
            inventory_item.add_stock(qty, batch_no, expiry_dt, cost_price)
            
            # Create stock move record
            stock_move = StockMove(
                drug_id=drug_id,
                qty=qty,
                move_type='in',
                ref='Manual Entry',
                batch_no=batch_no,
                expiry_dt=expiry_dt,
                cost_price=cost_price,
                notes=request.form.get('notes'),
                created_by_id=current_user.id
            )
            db.session.add(stock_move)
            
            db.session.commit()
            
            audit_log('inventory_add', 'Inventory', inventory_item.id, 
                     after_data={'qty_added': qty})
            
            flash(f'Added {qty} units to inventory!', 'success')
            return redirect(url_for('laboratory.drug_inventory', drug_id=drug_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding stock: {str(e)}', 'error')
    
    # Get departments for location selection
    from app.models.departments import Department
    departments = Department.get_support_departments()
    
    return render_template('laboratory/add_stock.html', drug=drug, departments=departments)

@lab_bp.route('/inventory/<int:drug_id>/adjust', methods=['GET', 'POST'])
@login_required
@require_permission('inventory_manage')
def adjust_stock(drug_id):
    """Adjust stock levels"""
    drug = Drug.query.get_or_404(drug_id)
    
    if request.method == 'POST':
        try:
            qty = int(request.form.get('qty'))
            adjustment_type = request.form.get('adjustment_type')  # 'add' or 'subtract'
            location_id = int(request.form.get('location_id'))
            reason = request.form.get('reason')
            
            # Find inventory item
            inventory_item = Inventory.query.filter_by(
                drug_id=drug_id,
                location_id=location_id
            ).first()
            
            if not inventory_item:
                flash('Inventory item not found for this location.', 'error')
                return redirect(url_for('laboratory.drug_inventory', drug_id=drug_id))
            
            # Adjust stock
            if adjustment_type == 'add':
                inventory_item.add_stock(qty)
                move_type = 'adjust'
                move_qty = qty
            else:
                if inventory_item.remove_stock(qty):
                    move_type = 'adjust'
                    move_qty = -qty
                else:
                    flash('Insufficient stock for adjustment.', 'error')
                    return redirect(url_for('laboratory.drug_inventory', drug_id=drug_id))
            
            # Create stock move record
            stock_move = StockMove(
                drug_id=drug_id,
                qty=move_qty,
                move_type=move_type,
                ref='Stock Adjustment',
                notes=f'{reason} - {adjustment_type} {qty} units',
                created_by_id=current_user.id
            )
            db.session.add(stock_move)
            
            db.session.commit()
            
            audit_log('inventory_adjust', 'Inventory', inventory_item.id, 
                     after_data={'adjustment': f'{adjustment_type} {qty}'})
            
            flash(f'Stock adjusted successfully!', 'success')
            return redirect(url_for('laboratory.drug_inventory', drug_id=drug_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adjusting stock: {str(e)}', 'error')
    
    # Get departments for location selection
    from app.models.departments import Department
    departments = Department.get_support_departments()
    
    return render_template('laboratory/adjust_stock.html', drug=drug, departments=departments)

# API endpoints
@lab_bp.route('/api/orders/pending')
@login_required
@require_permission('orders_read')
def api_pending_orders():
    """Get pending orders for AJAX"""
    orders = Order.get_pending_orders(order_type='lab')
    return jsonify([{
        'id': o.id,
        'visit_no': o.visit.visit_no if o.visit else None,
        'patient_name': o.visit.patient.full_name if o.visit and o.visit.patient else None,
        'description': o.description,
        'priority': o.priority,
        'created_at': o.created_at.isoformat() if o.created_at else None
    } for o in orders])

@lab_bp.route('/api/results/critical')
@login_required
@require_permission('orders_read')
def api_critical_results():
    """Get critical results for AJAX"""
    results = LabResult.get_critical_results()
    return jsonify([{
        'id': r.id,
        'analyte': r.analyte,
        'value': r.value,
        'unit': r.unit,
        'patient_name': r.order.visit.patient.full_name if r.order and r.order.visit and r.order.visit.patient else None,
        'reported_at': r.reported_at.isoformat() if r.reported_at else None
    } for r in results])
