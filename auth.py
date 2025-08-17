"""
Authentication routes for login, logout, and user management
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from werkzeug.security import check_password_hash
from app import db
from app.models.staff import Staff
from app.security import audit_log

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        if not email or not password:
            flash('Please provide both email and password.', 'error')
            return render_template('auth/login.html')
        
        user = Staff.find_by_email(email)
        
        if user and user.check_password(password) and user.active:
            login_user(user, remember=remember)
            
            # Log the successful login
            audit_log(
                action='login',
                entity='staff',
                entity_id=user.id,
                after_data={'success': True, 'ip': request.remote_addr}
            )
            
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('dashboard.index')
            
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(next_page)
        else:
            # Log failed login attempt
            if user:
                audit_log(
                    action='login',
                    entity='staff',
                    entity_id=user.id,
                    after_data={'success': False, 'ip': request.remote_addr, 'reason': 'invalid_password'}
                )
            
            flash('Invalid email or password.', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    user_id = current_user.id
    logout_user()
    
    # Log the logout
    audit_log(
        action='logout',
        entity='staff',
        entity_id=user_id,
        after_data={'ip': request.remote_addr}
    )
    
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    """API endpoint for user login"""
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400
    
    email = data['email']
    password = data['password']
    
    user = Staff.find_by_email(email)
    
    if user and user.check_password(password) and user.active:
        # Create JWT tokens
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        
        # Log the successful login
        audit_log(
            action='login',
            entity='staff',
            entity_id=user.id,
            after_data={'success': True, 'ip': request.remote_addr, 'method': 'api'}
        )
        
        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user.to_dict()
        }), 200
    else:
        # Log failed login attempt
        if user:
            audit_log(
                action='login',
                entity='staff',
                entity_id=user.id,
                after_data={'success': False, 'ip': request.remote_addr, 'reason': 'invalid_password', 'method': 'api'}
            )
        
        return jsonify({'error': 'Invalid credentials'}), 401

@auth_bp.route('/api/refresh', methods=['POST'])
@jwt_required(refresh=True)
def api_refresh():
    """API endpoint to refresh JWT token"""
    current_user_id = get_jwt_identity()
    new_token = create_access_token(identity=current_user_id)
    
    return jsonify({'access_token': new_token}), 200

@auth_bp.route('/api/me', methods=['GET'])
@jwt_required()
def api_me():
    """API endpoint to get current user information"""
    current_user_id = get_jwt_identity()
    user = Staff.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({'user': user.to_dict()}), 200

@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('auth/profile.html', user=current_user)

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password page"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_password or not new_password or not confirm_password:
            flash('All fields are required.', 'error')
            return render_template('auth/change_password.html')
        
        if not current_user.check_password(current_password):
            flash('Current password is incorrect.', 'error')
            return render_template('auth/change_password.html')
        
        if new_password != confirm_password:
            flash('New passwords do not match.', 'error')
            return render_template('auth/change_password.html')
        
        if len(new_password) < 8:
            flash('New password must be at least 8 characters long.', 'error')
            return render_template('auth/change_password.html')
        
        # Store old password hash for audit
        old_password_hash = current_user.hashed_pw
        
        # Update password
        current_user.set_password(new_password)
        db.session.commit()
        
        # Log password change
        audit_log(
            action='change_password',
            entity='staff',
            entity_id=current_user.id,
            before_data={'old_password_hash': old_password_hash},
            after_data={'new_password_hash': current_user.hashed_pw}
        )
        
        flash('Password changed successfully.', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/change_password.html')
