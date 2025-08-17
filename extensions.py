"""
Flask extensions initialization
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from flask_caching import Cache
from flask_mail import Mail
from celery import Celery

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
jwt = JWTManager()
cache = Cache()
mail = Mail()
celery = Celery()

def init_extensions(app):
    """Initialize all extensions with the app"""
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    jwt.init_app(app)
    cache.init_app(app)
    mail.init_app(app)
    
    # Configure Celery
    celery.conf.update(app.config)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.staff import Staff
        return Staff.query.get(int(user_id))
