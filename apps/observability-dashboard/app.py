import os
import logging
from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from celery import Celery
from apscheduler.schedulers.background import BackgroundScheduler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create SQLAlchemy base class
class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
csrf = CSRFProtect()
login_manager = LoginManager()
scheduler = BackgroundScheduler()

# Create and configure Celery
def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Load configuration
app.config.from_object('config.Config')

# Initialize extensions with app
db.init_app(app)
csrf.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

# Initialize Celery
celery = make_celery(app)

# Import and register blueprints
with app.app_context():
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.reports import reports_bp
    from routes.alerts import alerts_bp
    from routes.settings import settings_bp
    from routes.customers import customers_bp
    from routes.api import api_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(alerts_bp, url_prefix='/alerts')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(customers_bp, url_prefix='/customers')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Import models and create database tables
    import models
    db.create_all()
    
    # Start scheduler
    scheduler.start()
    
    # Initialize Analytics Integration
    observability_analytics_integration = None
    try:
        from analytics_integration import setup_analytics_integration
        observability_analytics_integration = setup_analytics_integration(
            app,
            config={
                'analytics_interval': 30.0,  # 30 seconds
                'collection_interval': 45.0,  # 45 seconds
                'max_history': 1000
            }
        )
        if observability_analytics_integration:
            observability_analytics_integration.start()
            logger.info("✅ Observability Dashboard Analytics Integration initialized")
    except ImportError as e:
        logger.warning(f"Analytics integration not available: {e}")
        observability_analytics_integration = None
    except Exception as e:
        logger.error(f"Error initializing analytics integration: {e}")
        observability_analytics_integration = None
    
    # Add template context processor for active alerts count
    @app.context_processor
    def inject_alert_counts():
        if current_user.is_authenticated:
            from models import Alert
            active_alerts_count = Alert.query.filter_by(resolved=False).count()
            return {'active_alerts_count': active_alerts_count}
        return {'active_alerts_count': 0}
    
    logger.info("Application initialized")

# Define route for the root URL
@app.route('/')
@login_required
def home():
    """Redirect to the dashboard as the home page"""
    return redirect(url_for('dashboard.index'))

# Load user for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))
