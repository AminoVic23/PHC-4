"""
Role and Permission models for RBAC system
"""
from datetime import datetime
from app import db

# Association table for many-to-many relationship between roles and permissions
role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id'), primary_key=True)
)

class Role(db.Model):
    """Role model for role-based access control"""
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Many-to-many relationship with permissions
    permissions = db.relationship('Permission', secondary=role_permissions, 
                                 backref=db.backref('roles', lazy='dynamic'))
    
    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)
    
    def add_permission(self, permission):
        """Add a permission to this role"""
        if permission not in self.permissions:
            self.permissions.append(permission)
    
    def remove_permission(self, permission):
        """Remove a permission from this role"""
        if permission in self.permissions:
            self.permissions.remove(permission)
    
    def has_permission(self, permission_code):
        """Check if role has a specific permission"""
        return any(p.code == permission_code for p in self.permissions)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'permissions': [p.to_dict() for p in self.permissions],
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Role {self.name}>'
    
    @classmethod
    def find_by_name(cls, name):
        """Find role by name"""
        return cls.query.filter_by(name=name).first()
    
    @classmethod
    def get_all_roles(cls):
        """Get all roles"""
        return cls.query.all()

class Permission(db.Model):
    """Permission model for fine-grained access control"""
    __tablename__ = 'permissions'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __init__(self, **kwargs):
        super(Permission, self).__init__(**kwargs)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Permission {self.code}: {self.name}>'
    
    @classmethod
    def find_by_code(cls, code):
        """Find permission by code"""
        return cls.query.filter_by(code=code).first()
    
    @classmethod
    def get_all_permissions(cls):
        """Get all permissions"""
        return cls.query.all()

class RolePermission(db.Model):
    """Association model for role-permission relationships (if needed for additional metadata)"""
    __tablename__ = 'role_permissions_meta'
    
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), primary_key=True)
    permission_id = db.Column(db.Integer, db.ForeignKey('permissions.id'), primary_key=True)
    granted_at = db.Column(db.DateTime, default=datetime.utcnow)
    granted_by = db.Column(db.Integer, db.ForeignKey('staff.id'))
    
    # Relationships
    role = db.relationship('Role', backref='role_permission_associations')
    permission = db.relationship('Permission', backref='role_permission_associations')
    granted_by_staff = db.relationship('Staff', backref='granted_permissions')
    
    def __repr__(self):
        return f'<RolePermission {self.role_id}:{self.permission_id}>'
