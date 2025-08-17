# Primary Healthcare Hospital Information System (HIS)

A comprehensive, production-ready Hospital Information System designed for primary healthcare facilities. Built with Flask, featuring modular architecture, robust Role-Based Access Control (RBAC), and comprehensive clinical and administrative workflows.

## 🏥 Features

### Core Modules
- **Patient Registration & Management** - Complete patient lifecycle management
- **Clinical Operations** - Physician clinics, dental clinic with SOAP notes
- **Laboratory Management** - Lab orders, results, and inventory
- **Radiology** - Imaging orders and reports
- **Pharmacy & Inventory** - Drug management, prescriptions, stock control
- **Billing & Cashier** - Invoicing, payments, insurance claims
- **Referrals** - Patient referral management
- **Human Resources** - Staff management, shifts, leave requests
- **IT Helpdesk** - Ticket management with SLA tracking
- **Quality Management** - Incident reporting and audits
- **Patient Satisfaction** - Survey management and NPS tracking
- **Maintenance** - Asset management and work orders
- **Medical Administration** - Clinical oversight and reporting
- **Facility Head** - Executive dashboard and approvals

### Technical Features
- **Role-Based Access Control (RBAC)** - Granular permissions system
- **Audit Trail** - Comprehensive logging of all user actions
- **REST API** - JWT-based API for external integrations
- **Real-time Dashboards** - Chart.js powered analytics
- **Background Jobs** - Celery for asynchronous tasks
- **Caching** - Redis for performance optimization
- **Document Management** - File upload and storage
- **Email Notifications** - Automated alerts and reminders

## 🛠 Technology Stack

- **Backend**: Python 3.11, Flask 2.3+
- **Database**: PostgreSQL 13+
- **ORM**: SQLAlchemy 2.0+, Alembic
- **Authentication**: Flask-Login (web), Flask-JWT-Extended (API)
- **Security**: bcrypt, CSRF protection, rate limiting
- **Frontend**: Jinja2, Bootstrap 5, HTMX, Chart.js
- **Background Jobs**: Celery, Redis
- **Testing**: pytest, factory-boy
- **Deployment**: Docker, Docker Compose, Gunicorn

## 📋 Prerequisites

- Python 3.11 or higher
- PostgreSQL 13 or higher
- Redis 6 or higher
- Docker and Docker Compose (for containerized deployment)

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone <repository-url>
cd PHC
```

### 2. Set Up Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your configuration
# See Configuration section below
```

### 3. Install Dependencies
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Database Setup
```bash
# Set up database
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Seed the database with initial data
python seed.py
```

### 5. Run the Application
```bash
# Development mode
flask run

# Production mode with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "app:app"
```

### 6. Access the Application
- **Web Interface**: http://localhost:5000
- **Default Admin**: admin@healthcare.com / password123

## 🐳 Docker Deployment

### Using Docker Compose
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Docker Services
- **web**: Flask application (Gunicorn)
- **db**: PostgreSQL database
- **redis**: Redis cache and message broker
- **worker**: Celery worker for background jobs
- **scheduler**: Celery beat for scheduled tasks

## ⚙️ Configuration

### Environment Variables (.env)
```bash
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
FLASK_APP=app

# Database
DATABASE_URL=postgresql://username:password@localhost:5432/phc_db

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1

# JWT
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ACCESS_TOKEN_EXPIRES=3600

# Email
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# File Upload
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216

# Security
SESSION_COOKIE_SECURE=False
SESSION_COOKIE_HTTPONLY=True
PERMANENT_SESSION_LIFETIME=3600
```

## 👥 User Roles and Permissions

### Role Hierarchy
1. **superadmin** - Full system access
2. **facility_head** - Read-all access, approval capabilities
3. **medical_admin** - Medical oversight and administration
4. **physician** - Clinical operations
5. **registration** - Patient registration
6. **laboratory** - Lab operations
7. **pharmacy** - Pharmacy operations
8. **cashier** - Billing and payments
9. **hr** - Human resources
10. **helpdesk** - IT support
11. **quality** - Quality management
12. **satisfaction** - Patient satisfaction
13. **maintenance** - Facility maintenance

### Permission System
- **view** - Read access to module data
- **create** - Create new records
- **edit** - Modify existing records
- **delete** - Delete records
- **approve** - Approval capabilities
- **export** - Export data
- **admin** - Administrative functions

## 📊 Key Workflows

### Patient Journey
1. **Registration** → Patient registration and MRN assignment
2. **Appointment** → Schedule clinic visit
3. **Check-in** → Patient arrival and triage
4. **Clinical** → Physician consultation and SOAP notes
5. **Orders** → Lab/radiology orders if needed
6. **Pharmacy** → Prescription and dispensing
7. **Billing** → Invoice generation and payment
8. **Follow-up** → Referrals or discharge

### Clinical Workflows
- **SOAP Notes** - Structured clinical documentation
- **Lab Orders** - Order management and result tracking
- **Radiology** - Imaging workflow
- **Prescriptions** - Drug prescribing and dispensing
- **Referrals** - Patient referral management

### Administrative Workflows
- **Staff Management** - HR operations
- **Quality Assurance** - Incident reporting and audits
- **Maintenance** - Asset and work order management
- **Financial** - Revenue tracking and reporting

## 🔧 Development

### Project Structure
```
PHC/
├── app/
│   ├── __init__.py          # Application factory
│   ├── config.py            # Configuration classes
│   ├── extensions.py        # Flask extensions
│   ├── security.py          # RBAC and security
│   ├── models/              # Database models
│   ├── routes/              # Flask blueprints
│   ├── services/            # Business logic
│   ├── tasks/               # Celery tasks
│   ├── utils/               # Utility functions
│   ├── templates/           # Jinja2 templates
│   └── static/              # Static files
├── migrations/              # Alembic migrations
├── tests/                   # Test suite
├── docker/                  # Docker configuration
├── requirements.txt         # Python dependencies
├── docker-compose.yml       # Docker services
├── seed.py                  # Database seeding
└── README.md               # This file
```

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_models.py

# Run E2E tests
pytest tests/e2e/
```

### Database Migrations
```bash
# Create new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Rollback migration
flask db downgrade
```

### Code Quality
```bash
# Format code
black app/ tests/

# Lint code
flake8 app/ tests/

# Type checking
mypy app/
```

## 📈 Monitoring and Logging

### Logging Configuration
- **Application Logs**: `logs/app.log`
- **Error Logs**: `logs/error.log`
- **Audit Logs**: Database table `audit_logs`
- **Access Logs**: `logs/access.log`

### Health Checks
- **Application**: `/health`
- **Database**: `/health/db`
- **Redis**: `/health/redis`
- **Celery**: `/health/celery`

### Metrics and KPIs
- **Clinical**: Visit volume, documentation rate, referral acceptance
- **Financial**: Revenue, outstanding receivables, payment methods
- **Quality**: Incident rates, satisfaction scores, SLA compliance
- **Operational**: Staff productivity, asset utilization, maintenance metrics

## 🔒 Security Features

### Authentication & Authorization
- **Multi-factor Authentication** (planned)
- **Session Management** with secure cookies
- **JWT Tokens** for API access
- **Role-Based Access Control** (RBAC)
- **Permission-based Authorization**

### Data Protection
- **Password Hashing** with bcrypt
- **CSRF Protection** on all forms
- **Input Validation** with Marshmallow
- **SQL Injection Prevention** with SQLAlchemy
- **XSS Protection** with Jinja2 auto-escaping

### Audit & Compliance
- **Comprehensive Audit Trail** for all actions
- **Data Change Tracking** with before/after snapshots
- **User Activity Logging** with IP addresses
- **Sensitive Data Encryption** (planned)

## 🚀 Production Deployment

### Recommended Setup
1. **Load Balancer** (nginx/haproxy)
2. **Application Servers** (multiple Gunicorn instances)
3. **Database** (PostgreSQL with replication)
4. **Cache** (Redis cluster)
5. **File Storage** (S3-compatible or local)
6. **Monitoring** (Prometheus + Grafana)

### Environment Variables for Production
```bash
FLASK_ENV=production
SECRET_KEY=<strong-random-key>
DATABASE_URL=<production-db-url>
REDIS_URL=<production-redis-url>
MAIL_SERVER=<smtp-server>
SESSION_COOKIE_SECURE=True
```

### Performance Optimization
- **Database Indexing** on frequently queried fields
- **Redis Caching** for session data and queries
- **CDN** for static assets
- **Database Connection Pooling**
- **Background Job Processing** with Celery

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Code Standards
- Follow PEP 8 style guidelines
- Write docstrings for all functions
- Include type hints where appropriate
- Maintain test coverage above 80%
- Update documentation for new features

## 📞 Support

### Getting Help
- **Documentation**: Check this README and inline code comments
- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Use GitHub Discussions for questions
- **Email**: Contact the development team

### Common Issues
- **Database Connection**: Check DATABASE_URL in .env
- **Redis Connection**: Verify REDIS_URL configuration
- **Permission Errors**: Ensure proper file permissions
- **Import Errors**: Check virtual environment activation

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Flask community for the excellent web framework
- SQLAlchemy team for the powerful ORM
- Bootstrap team for the responsive UI framework
- All contributors and testers

---

**Note**: This is a production-ready system designed for healthcare environments. Ensure compliance with local healthcare regulations and data protection laws before deployment.
