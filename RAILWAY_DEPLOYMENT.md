# Railway Deployment Guide

This guide will help you deploy your Primary Healthcare HIS to Railway.

## Files Created for Railway Deployment

1. **`wsgi.py`** - WSGI entry point for the Flask application
2. **`Procfile`** - Tells Railway how to start the application
3. **`runtime.txt`** - Specifies Python version
4. **`startup.py`** - Database initialization script

## Railway Configuration

### 1. Environment Variables

Set these environment variables in your Railway project:

```bash
# Flask Configuration
FLASK_APP=wsgi.py
FLASK_ENV=production
SECRET_KEY=your-secure-secret-key-here

# Database Configuration (Railway will provide this)
DATABASE_URL=postgresql://...

# Redis Configuration (if using Redis addon)
REDIS_URL=redis://...

# JWT Configuration
JWT_SECRET_KEY=your-jwt-secret-key

# Email Configuration (optional)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Security Configuration
WTF_CSRF_ENABLED=true
WTF_CSRF_TIME_LIMIT=3600

# Logging Configuration
LOG_LEVEL=INFO
```

### 2. Railway Services

You'll need to add these services to your Railway project:

1. **PostgreSQL Database** - For your main database
2. **Redis** (optional) - For caching and Celery tasks

### 3. Deployment Steps

1. **Connect your GitHub repository** to Railway
2. **Add PostgreSQL service** to your project
3. **Set environment variables** as listed above
4. **Deploy** - Railway will automatically detect the Procfile and start your application

### 4. Database Initialization

After deployment, you may need to initialize your database:

```bash
# Connect to your Railway app via CLI
railway login
railway link
railway run python startup.py
```

Or run the seed script to populate with sample data:

```bash
railway run python seed.py
```

### 5. Troubleshooting

#### Common Issues:

1. **"No start command found"** - Make sure `Procfile` exists and is named correctly (no extension)
2. **Database connection errors** - Check that `DATABASE_URL` is set correctly
3. **Import errors** - Ensure all dependencies are in `requirements.txt`
4. **"No module named 'app'"** - This has been fixed by adding proper `__init__.py` files and path configuration in `wsgi.py`

#### Logs:

Check your application logs in Railway dashboard or via CLI:

```bash
railway logs
```

### 6. Production Considerations

1. **Security**: Change all default secret keys
2. **Database**: Use Railway's managed PostgreSQL
3. **SSL**: Railway provides SSL certificates automatically
4. **Scaling**: Railway can auto-scale based on traffic

### 7. Custom Domains

Railway allows you to add custom domains to your application through the dashboard.

## File Structure

```
your-project/
├── app/                    # Flask application
├── wsgi.py                # WSGI entry point
├── Procfile               # Railway start command
├── runtime.txt            # Python version
├── startup.py             # Database initialization
├── requirements.txt       # Python dependencies
├── seed.py               # Sample data
└── RAILWAY_DEPLOYMENT.md # This guide
```

## Support

If you encounter issues:

1. Check Railway logs: `railway logs`
2. Verify environment variables are set correctly
3. Ensure all dependencies are in `requirements.txt`
4. Check that your database is properly connected
