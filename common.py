"""
Common models for documents and audit trails
"""
from datetime import datetime, timedelta
from app import db

class Document(db.Model):
    """Document model for file management"""
    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)
    document_no = db.Column(db.String(20), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)  # Size in bytes
    mime_type = db.Column(db.String(100))
    document_type = db.Column(db.String(50), nullable=False, index=True)  # patient_record, invoice, prescription, report, etc.
    category = db.Column(db.String(50), index=True)  # clinical, administrative, financial, etc.
    entity_type = db.Column(db.String(50), index=True)  # Patient, Visit, Invoice, etc.
    entity_id = db.Column(db.Integer, index=True)  # ID of the related entity
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False, index=True)
    status = db.Column(db.String(20), default='active', nullable=False, index=True)  # active, archived, deleted
    is_public = db.Column(db.Boolean, default=False, index=True)  # Whether document is publicly accessible
    tags = db.Column(db.JSON)  # Store tags as JSON array
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    uploaded_by = db.relationship('Staff', backref='uploaded_documents')

    def __init__(self, **kwargs):
        super(Document, self).__init__(**kwargs)
        if not self.document_no:
            self.document_no = self.generate_document_no()

    @property
    def is_active(self):
        """Check if document is active"""
        return self.status == 'active'

    @property
    def is_archived(self):
        """Check if document is archived"""
        return self.status == 'archived'

    @property
    def is_deleted(self):
        """Check if document is deleted"""
        return self.status == 'deleted'

    @property
    def file_size_mb(self):
        """Get file size in MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return None

    @property
    def file_extension(self):
        """Get file extension"""
        if self.file_name:
            return self.file_name.split('.')[-1].lower()
        return None

    @property
    def is_image(self):
        """Check if document is an image"""
        image_types = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff']
        return self.file_extension in image_types

    @property
    def is_pdf(self):
        """Check if document is a PDF"""
        return self.file_extension == 'pdf'

    def archive_document(self):
        """Archive the document"""
        self.status = 'archived'

    def delete_document(self):
        """Mark document as deleted"""
        self.status = 'deleted'

    def restore_document(self):
        """Restore document to active status"""
        self.status = 'active'

    def add_tag(self, tag):
        """Add a tag to the document"""
        if not self.tags:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag):
        """Remove a tag from the document"""
        if self.tags and tag in self.tags:
            self.tags.remove(tag)

    def has_tag(self, tag):
        """Check if document has a specific tag"""
        return self.tags and tag in self.tags

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'document_no': self.document_no,
            'title': self.title,
            'description': self.description,
            'file_name': self.file_name,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'file_size_mb': self.file_size_mb,
            'mime_type': self.mime_type,
            'document_type': self.document_type,
            'category': self.category,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'uploaded_by_id': self.uploaded_by_id,
            'uploaded_by_name': self.uploaded_by.name if self.uploaded_by else None,
            'status': self.status,
            'is_public': self.is_public,
            'tags': self.tags,
            'is_active': self.is_active,
            'is_archived': self.is_archived,
            'is_deleted': self.is_deleted,
            'file_extension': self.file_extension,
            'is_image': self.is_image,
            'is_pdf': self.is_pdf,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<Document {self.document_no}: {self.title} ({self.document_type})>'

    @classmethod
    def generate_document_no(cls):
        """Generate a unique document number"""
        import random
        import string

        while True:
            # Generate document number in format: DOC-YYYYMMDD-XXXXX
            date_str = datetime.now().strftime('%Y%m%d')
            digits = ''.join(random.choices(string.digits, k=5))
            document_no = f"DOC-{date_str}-{digits}"

            # Check if document number already exists
            if not cls.query.filter_by(document_no=document_no).first():
                return document_no

    @classmethod
    def get_active_documents(cls, limit=50):
        """Get all active documents"""
        return cls.query.filter_by(status='active')\
                       .order_by(cls.created_at.desc())\
                       .limit(limit).all()

    @classmethod
    def get_documents_by_type(cls, document_type, limit=50):
        """Get documents by type"""
        return cls.query.filter_by(document_type=document_type, status='active')\
                       .order_by(cls.created_at.desc())\
                       .limit(limit).all()

    @classmethod
    def get_documents_by_category(cls, category, limit=50):
        """Get documents by category"""
        return cls.query.filter_by(category=category, status='active')\
                       .order_by(cls.created_at.desc())\
                       .limit(limit).all()

    @classmethod
    def get_entity_documents(cls, entity_type, entity_id, limit=20):
        """Get documents for a specific entity"""
        return cls.query.filter_by(
            entity_type=entity_type,
            entity_id=entity_id,
            status='active'
        ).order_by(cls.created_at.desc())\
         .limit(limit).all()

    @classmethod
    def get_user_documents(cls, user_id, limit=50):
        """Get documents uploaded by a user"""
        return cls.query.filter_by(uploaded_by_id=user_id)\
                       .order_by(cls.created_at.desc())\
                       .limit(limit).all()

    @classmethod
    def get_public_documents(cls, limit=50):
        """Get public documents"""
        return cls.query.filter_by(is_public=True, status='active')\
                       .order_by(cls.created_at.desc())\
                       .limit(limit).all()

    @classmethod
    def get_documents_by_tag(cls, tag, limit=50):
        """Get documents with a specific tag"""
        return cls.query.filter(
            cls.tags.contains([tag]),
            cls.status == 'active'
        ).order_by(cls.created_at.desc())\
         .limit(limit).all()

    @classmethod
    def get_recent_documents(cls, days=30):
        """Get recently uploaded documents"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return cls.query.filter(
            cls.created_at >= cutoff_date,
            cls.status == 'active'
        ).order_by(cls.created_at.desc()).all()

    @classmethod
    def get_document_statistics(cls):
        """Get document statistics"""
        total_documents = cls.query.count()
        active_documents = cls.query.filter_by(status='active').count()
        archived_documents = cls.query.filter_by(status='archived').count()
        deleted_documents = cls.query.filter_by(status='deleted').count()
        public_documents = cls.query.filter_by(is_public=True, status='active').count()
        
        # Calculate total size
        total_size = cls.query.with_entities(db.func.sum(cls.file_size)).scalar() or 0
        
        return {
            'total_documents': total_documents,
            'active_documents': active_documents,
            'archived_documents': archived_documents,
            'deleted_documents': deleted_documents,
            'public_documents': public_documents,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2) if total_size > 0 else 0
        }

class AuditLog(db.Model):
    """Audit log model for tracking system changes"""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False, index=True)
    action = db.Column(db.String(100), nullable=False, index=True)  # create, update, delete, login, logout, etc.
    entity = db.Column(db.String(100), nullable=False, index=True)  # Patient, Visit, Invoice, etc.
    entity_id = db.Column(db.Integer, index=True)  # ID of the affected entity
    before_json = db.Column(db.JSON)  # Data before change
    after_json = db.Column(db.JSON)  # Data after change
    ip_address = db.Column(db.String(45))  # IPv4 or IPv6
    user_agent = db.Column(db.String(500))
    session_id = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    notes = db.Column(db.Text)

    # Relationships
    actor = db.relationship('Staff', backref='audit_logs')

    def __init__(self, **kwargs):
        super(AuditLog, self).__init__(**kwargs)

    @property
    def is_create_action(self):
        """Check if action is create"""
        return self.action == 'create'

    @property
    def is_update_action(self):
        """Check if action is update"""
        return self.action == 'update'

    @property
    def is_delete_action(self):
        """Check if action is delete"""
        return self.action == 'delete'

    @property
    def is_login_action(self):
        """Check if action is login"""
        return self.action == 'login'

    @property
    def is_logout_action(self):
        """Check if action is logout"""
        return self.action == 'logout'

    @property
    def has_changes(self):
        """Check if there are data changes"""
        return self.before_json is not None or self.after_json is not None

    @property
    def change_summary(self):
        """Get a summary of changes"""
        if not self.has_changes:
            return None
        
        if self.is_create_action:
            return f"Created {self.entity} with ID {self.entity_id}"
        elif self.is_delete_action:
            return f"Deleted {self.entity} with ID {self.entity_id}"
        elif self.is_update_action and self.before_json and self.after_json:
            # Compare before and after data
            changed_fields = []
            for key in self.after_json:
                if key in self.before_json and self.before_json[key] != self.after_json[key]:
                    changed_fields.append(key)
            return f"Updated {self.entity} {self.entity_id}: {', '.join(changed_fields)}"
        
        return f"{self.action.title()} {self.entity} {self.entity_id}"

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'actor_id': self.actor_id,
            'actor_name': self.actor.name if self.actor else None,
            'action': self.action,
            'entity': self.entity,
            'entity_id': self.entity_id,
            'before_json': self.before_json,
            'after_json': self.after_json,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'session_id': self.session_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'notes': self.notes,
            'is_create_action': self.is_create_action,
            'is_update_action': self.is_update_action,
            'is_delete_action': self.is_delete_action,
            'is_login_action': self.is_login_action,
            'is_logout_action': self.is_logout_action,
            'has_changes': self.has_changes,
            'change_summary': self.change_summary
        }

    def __repr__(self):
        return f'<AuditLog {self.actor.name if self.actor else "Unknown"}: {self.action} {self.entity} {self.entity_id}>'

    @classmethod
    def get_user_audit_logs(cls, user_id, limit=50):
        """Get audit logs for a specific user"""
        return cls.query.filter_by(actor_id=user_id)\
                       .order_by(cls.timestamp.desc())\
                       .limit(limit).all()

    @classmethod
    def get_entity_audit_logs(cls, entity, entity_id, limit=50):
        """Get audit logs for a specific entity"""
        return cls.query.filter_by(entity=entity, entity_id=entity_id)\
                       .order_by(cls.timestamp.desc())\
                       .limit(limit).all()

    @classmethod
    def get_action_audit_logs(cls, action, limit=50):
        """Get audit logs for a specific action"""
        return cls.query.filter_by(action=action)\
                       .order_by(cls.timestamp.desc())\
                       .limit(limit).all()

    @classmethod
    def get_recent_audit_logs(cls, hours=24):
        """Get recent audit logs"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return cls.query.filter(cls.timestamp >= cutoff_time)\
                       .order_by(cls.timestamp.desc()).all()

    @classmethod
    def get_login_audit_logs(cls, limit=50):
        """Get login audit logs"""
        return cls.query.filter_by(action='login')\
                       .order_by(cls.timestamp.desc())\
                       .limit(limit).all()

    @classmethod
    def get_failed_login_audit_logs(cls, limit=50):
        """Get failed login audit logs"""
        return cls.query.filter_by(action='login_failed')\
                       .order_by(cls.timestamp.desc())\
                       .limit(limit).all()

    @classmethod
    def get_data_change_audit_logs(cls, limit=50):
        """Get audit logs with data changes"""
        return cls.query.filter(
            cls.action.in_(['create', 'update', 'delete']),
            cls.has_changes == True
        ).order_by(cls.timestamp.desc())\
         .limit(limit).all()

    @classmethod
    def get_audit_log_statistics(cls, days=30):
        """Get audit log statistics"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        total_logs = cls.query.filter(cls.timestamp >= cutoff_date).count()
        create_logs = cls.query.filter_by(action='create').filter(cls.timestamp >= cutoff_date).count()
        update_logs = cls.query.filter_by(action='update').filter(cls.timestamp >= cutoff_date).count()
        delete_logs = cls.query.filter_by(action='delete').filter(cls.timestamp >= cutoff_date).count()
        login_logs = cls.query.filter_by(action='login').filter(cls.timestamp >= cutoff_date).count()
        
        # Get unique users
        unique_users = cls.query.filter(cls.timestamp >= cutoff_date)\
                               .with_entities(cls.actor_id)\
                               .distinct().count()
        
        return {
            'total_logs': total_logs,
            'create_logs': create_logs,
            'update_logs': update_logs,
            'delete_logs': delete_logs,
            'login_logs': login_logs,
            'unique_users': unique_users
        }
