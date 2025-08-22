import os
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, abort
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
import functools
import threading
from database import db, migrate

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Create the Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_key_replace_in_production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///flow_collector.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Configure upload settings for MIB files
app.config["UPLOAD_FOLDER"] = "uploads/mibs"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload
app.config["ALLOWED_EXTENSIONS"] = {"mib", "txt", "xml"}

# Initialize the database
db.init_app(app)
migrate.init_app(app, db)

# Initialize Flask-Login after app is created
login_manager.init_app(app)

# Import health check and API blueprints first
from health import health_bp
from api_endpoints import api_bp

# Register blueprints
app.register_blueprint(health_bp)
app.register_blueprint(api_bp)

# Global variables for models and components that will be initialized later
FlowData = Device = FlowTemplate = MibFile = SimulationConfig = ForwardTarget = None
User = Role = Permission = UserDevice = AnalysisResult = None  
flow_receiver = flow_simulator = flow_forwarder = ai_insights_manager = None
enhanced_processor = analytics_integration = None

def initialize_app():
    """Initialize app components after database is set up"""
    global FlowData, Device, FlowTemplate, MibFile, SimulationConfig, ForwardTarget
    global User, Role, Permission, UserDevice, AnalysisResult
    global flow_receiver, flow_simulator, flow_forwarder, ai_insights_manager
    global enhanced_processor, analytics_integration
    
    # Import models inside app context to avoid circular imports
    from models import FlowData, Device, FlowTemplate, MibFile, SimulationConfig, ForwardTarget
    from models import User, Role, Permission, UserDevice, AnalysisResult
    from flow_receiver import FlowReceiver
    from flow_simulator import FlowSimulator
    from flow_forwarder import FlowForwarder
    from ai_insights import get_ai_insights_manager
    import config
    
    # Note: Database tables are created via Flask-Migrate migrations
    # Run 'flask db init', 'flask db migrate', 'flask db upgrade' to set up the database
    
    # Create default roles
    Role.insert_roles()
    
    # Create default admin user if it doesn't exist
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        admin_role = Role.query.filter_by(name='Administrator').first()
        if admin_role:
            admin_user = User(
                username='admin',
                email='admin@flowvision.local',
                role=admin_role
            )
            # Generate a random password for production security
            import secrets
            import string
            password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
            admin_user.set_password(password)
            db.session.add(admin_user)
            db.session.commit()
            print(f"Created default admin user: username='admin', password='{password}'")
    
    # Initialize the flow receiver, simulator, and forwarder
    flow_receiver = FlowReceiver()
    flow_simulator = FlowSimulator()
    flow_forwarder = FlowForwarder()
    
    # Initialize AI insights manager
    ai_insights_manager = get_ai_insights_manager()
    
    # Initialize Enhanced Flow Processor
    try:
        from enhanced_flow_processor import create_enhanced_flow_processor
        enhanced_processor = create_enhanced_flow_processor()
        logger.info("✅ Enhanced Flow Processor initialized")
    except ImportError as e:
        logger.warning(f"Enhanced Flow Processor not available: {e}")
        enhanced_processor = None
    
    # Initialize Analytics Integration
    try:
        from analytics_integration import setup_analytics_integration
        if enhanced_processor:
            analytics_integration = setup_analytics_integration(
                app, 
                enhanced_processor,
                config={
                    'analytics_interval': 10.0,  # 10 seconds
                    'collection_interval': 30.0,  # 30 seconds
                    'max_history': 500
                }
            )
            analytics_integration.start()
            logger.info("✅ Analytics Integration initialized")
        else:
            logger.warning("Analytics integration skipped - enhanced processor not available")
    except ImportError as e:
        logger.warning(f"Analytics integration not available: {e}")
        analytics_integration = None
    
    # Set up user loader after User model is imported
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

def start_flow_services():
    """Start flow processing services"""
    try:
        # Start the flow receivers in background mode
        # Note: In production, these would be started as separate processes
        # or services. For development, they can be started programmatically.
        print("Flow processing services initialized")
        print("Note: Flow receivers should be started separately in production")
    except Exception as e:
        print(f"Warning: Could not start flow services: {e}")

# Initialize app components but defer database initialization
# This allows Flask-Migrate to work without circular import issues
def create_app():
    """Create and configure the Flask application"""
    with app.app_context():
        initialize_app()
        start_flow_services()
    return app

# Only initialize if running directly, not during import
if __name__ == '__main__':
    create_app()

# Helper function to check if file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    from forms import LoginForm
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return render_template('auth/login.html', form=form)
        login_user(user, form.remember_me.data)
        next_page = request.args.get('next')
        if next_page is None or not next_page.startswith('/'):
            next_page = url_for('dashboard')
        flash(f'Welcome, {user.username}!', 'success')
        return redirect(next_page)
    return render_template('auth/login.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    from forms import RegistrationForm
    from models import User, Role
    form = RegistrationForm()
    if form.validate_on_submit():
        # Get default role (User)
        default_role = Role.query.filter_by(name='User').first()
        if not default_role:
            flash("Registration error: Default role not found. Please contact an administrator.", "error")
            return redirect(url_for('login'))
            
        # Create new user
        user = User(
            username=form.username.data,
            email=form.email.data,
            role=default_role
        )
        user.set_password(form.password.data)
        
        try:
            db.session.add(user)
            db.session.commit()
            flash("Registration successful! You can now log in.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash("Registration failed. Please try again.", "error")
            logger.error(f"Registration error: {str(e)}")
    return render_template('auth/register.html', form=form)

@app.route('/user/profile', methods=['GET', 'POST'])
@login_required
def user_profile():
    from forms import ChangePasswordForm
    form = ChangePasswordForm()
    if form.validate_on_submit():
        # Verify current password
        if not current_user.check_password(form.old_password.data):
            flash("Invalid current password.", "error")
            return render_template('auth/profile.html', form=form)
            
        # Update password
        try:
            current_user.set_password(form.password.data)
            db.session.commit()
            flash("Password updated successfully.", "success")
            return redirect(url_for('user_profile'))
        except Exception as e:
            db.session.rollback()
            flash("Password change failed. Please try again.", "error")
            logger.error(f"Password change error: {str(e)}")
    return render_template('auth/profile.html', form=form)

@app.route('/user/manage', methods=['GET'])
@login_required
def manage_users():
    # Check if user has admin permission
    if not current_user.is_administrator():
        flash('Access denied: You must be an administrator.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Add pagination for better performance
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    users = User.query.options(db.joinedload(User.role)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return render_template('auth/manage_users.html', users=users)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Get flow statistics for the dashboard
    flow_stats = {
        'total_flows': db.session.query(FlowData).count(),
        'netflow_count': db.session.query(FlowData).filter(FlowData.flow_type.like('netflow%')).count(),
        'sflow_count': db.session.query(FlowData).filter(FlowData.flow_type.like('sflow%')).count(),
        'devices': db.session.query(Device).count(),
        'recent_flows': db.session.query(FlowData).order_by(FlowData.timestamp.desc()).limit(10).all()
    }
    return render_template('dashboard.html', stats=flow_stats)

@app.route('/analyzer')
@login_required
def analyzer():
    if not current_user.has_permission(Permission.VIEW_FLOW_DATA):
        flash('You do not have permission to access the analyzer.', 'danger')
        return redirect(url_for('dashboard'))
    # Only load essential device fields for dropdown/selection
    devices = Device.query.with_entities(Device.id, Device.name, Device.ip_address).all()
    return render_template('analyzer.html', devices=devices)

@app.route('/ai_insights/<int:device_id>')
@login_required
def ai_insights(device_id):
    """
    Render the AI insights page for a specific device
    """
    if not current_user.has_permission(Permission.VIEW_FLOW_DATA):
        flash('You do not have permission to access AI insights.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get device
    device = Device.query.get_or_404(device_id)
    
    # Check if user has access to this device
    if not current_user.can_access_device(device.id):
        flash('You do not have permission to access this device.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Add now function for template
    from datetime import datetime
    def now():
        return datetime.utcnow()
    
    return render_template('ai_insights.html', device=device, now=now)

@app.route('/simulator')
@login_required
def simulator():
    if not current_user.has_permission(Permission.MANAGE_SIMULATIONS):
        flash('You do not have permission to access the simulator.', 'danger')
        return redirect(url_for('dashboard'))
    # Only load essential template fields for selection
    templates = FlowTemplate.query.with_entities(
        FlowTemplate.id, FlowTemplate.name, FlowTemplate.description
    ).order_by(FlowTemplate.name).all()
    return render_template('simulator.html', templates=templates)

@app.route('/simulations')
@login_required
def get_simulations():
    """Get all active simulations"""
    try:
        # Check if user has permission
        if not current_user.has_permission(Permission.MANAGE_SIMULATIONS):
            return jsonify({"error": "Access denied"}), 403
            
        # Get active simulations from the database
        simulations = SimulationConfig.query.filter(
            (SimulationConfig.status == 'running') | 
            (SimulationConfig.status == 'pending')
        ).all()
        
        # Convert to dict for JSON response
        sim_list = []
        for sim in simulations:
            sim_list.append({
                'id': sim.id,
                'flow_type': sim.flow_type,
                'flow_version': sim.flow_version,
                'packets_per_second': sim.packets_per_second,
                'start_time': sim.start_time.isoformat() if sim.start_time else None,
                'status': sim.status
            })
            
        return jsonify({'simulations': sim_list})
    except Exception as e:
        logger.error(f"Error getting simulations: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/stop_simulation/<int:simulation_id>', methods=['POST'])
@login_required
def stop_simulation(simulation_id):
    """Stop a running simulation"""
    try:
        # Check if user has permission
        if not current_user.has_permission(Permission.MANAGE_SIMULATIONS):
            return jsonify({"error": "Access denied"}), 403
            
        # Get the simulation
        sim = SimulationConfig.query.get(simulation_id)
        if not sim:
            return jsonify({"error": "Simulation not found"}), 404
            
        # Update status in database
        sim.status = 'stopped'
        sim.end_time = datetime.now()
        db.session.commit()
        
        # Stop the simulation in the flow_simulator if it's running
        if hasattr(flow_simulator, 'stop_simulation'):
            flow_simulator.stop_simulation(simulation_id)
            
        return jsonify({'success': True, 'message': 'Simulation stopped successfully'})
    except Exception as e:
        logger.error(f"Error stopping simulation: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/start_simulation', methods=['POST'])
@login_required
def start_simulation():
    if request.method == 'POST':
        template_id = request.form.get('template_id')
        flow_type = request.form.get('flow_type')
        flow_version = request.form.get('flow_version')
        packets_per_second = int(request.form.get('packets_per_second', 100))
        duration = int(request.form.get('duration', 60))
        
        # Create a simulation config
        sim_config = SimulationConfig(
            template_id=template_id if template_id else None,
            flow_type=flow_type,
            flow_version=flow_version,
            packets_per_second=packets_per_second,
            duration=duration,
            status='running',
            start_time=datetime.now()
        )
        db.session.add(sim_config)
        db.session.commit()
        
        # Start simulation in a background thread
        threading.Thread(
            target=flow_simulator.start_simulation,
            args=(sim_config.id,),
            daemon=True
        ).start()
        
        flash('Simulation started successfully!', 'success')
        return redirect(url_for('simulator'))

@app.route('/forwarder')
@login_required
def forwarder():
    if not current_user.has_permission(Permission.MANAGE_FORWARD_TARGETS):
        flash('You do not have permission to access the forwarder.', 'danger')
        return redirect(url_for('dashboard'))
    # Load targets with pagination for better performance
    page = request.args.get('page', 1, type=int)
    targets = ForwardTarget.query.order_by(ForwardTarget.name).paginate(
        page=page, per_page=50, error_out=False
    )
    return render_template('forwarder.html', targets=targets)

@app.route('/add_forward_target', methods=['POST'])
@login_required
def add_forward_target():
    if request.method == 'POST':
        name = request.form.get('name')
        ip_address = request.form.get('ip_address')
        port = int(request.form.get('port'))
        protocol = request.form.get('protocol')
        flow_type = request.form.get('flow_type')
        flow_version = request.form.get('flow_version')
        
        target = ForwardTarget(
            name=name,
            ip_address=ip_address,
            port=port,
            protocol=protocol,
            flow_type=flow_type,
            flow_version=flow_version,
            active=True
        )
        db.session.add(target)
        db.session.commit()
        
        flash('Forward target added successfully!', 'success')
        return redirect(url_for('forwarder'))

@app.route('/toggle_forward_target/<int:target_id>', methods=['POST'])
@login_required
def toggle_forward_target(target_id):
    if not current_user.has_permission(Permission.MANAGE_FORWARD_TARGETS):
        return jsonify({"success": False, "error": "Permission denied"}), 403
    
    target = ForwardTarget.query.get_or_404(target_id)
    target.active = not target.active
    db.session.commit()
    return jsonify({"success": True, "active": target.active})

@app.route('/mib_manager')
@login_required
def mib_manager():
    if not current_user.has_permission(Permission.MANAGE_MIBS):
        flash('You do not have permission to access the MIB manager.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Add pagination and only load essential fields
    page = request.args.get('page', 1, type=int)
    mibs = MibFile.query.with_entities(
        MibFile.id, MibFile.filename, MibFile.device_type, MibFile.description, MibFile.parsed
    ).order_by(MibFile.filename).paginate(
        page=page, per_page=25, error_out=False
    )
    return render_template('mib_manager.html', mibs=mibs)

@app.route('/upload_mib', methods=['POST'])
@login_required
def upload_mib():
    if 'mib_file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('mib_manager'))
    
    file = request.files['mib_file']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('mib_manager'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        
        # Create upload directory if it doesn't exist
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Save MIB file record in database
        mib_file = MibFile(
            filename=filename,
            path=file_path,
            device_type=request.form.get('device_type', 'unknown'),
            description=request.form.get('description', '')
        )
        db.session.add(mib_file)
        db.session.commit()
        
        flash('MIB file uploaded successfully!', 'success')
        return redirect(url_for('mib_manager'))
    
    flash('Invalid file type', 'error')
    return redirect(url_for('mib_manager'))

@app.route('/parse_mib/<int:mib_id>')
@login_required
def parse_mib(mib_id):
    if not current_user.has_permission(Permission.MANAGE_MIBS):
        flash('You do not have permission to parse MIB files.', 'danger')
        return redirect(url_for('mib_manager'))
    
    # Get the MIB file record
    mib_file = MibFile.query.get_or_404(mib_id)
    
    # Create MIB parser instance
    from mib_parser import MibParser
    mib_parser = MibParser()
    
    # Parse the MIB file
    result = mib_parser.parse_mib_file(mib_id)
    
    if 'error' in result:
        flash(f'Error parsing MIB file: {result["error"]}', 'danger')
    else:
        flash(f'MIB file parsed successfully. Found {result["oids"]} OIDs.', 'success')
    
    return redirect(url_for('mib_manager'))

@app.route('/mib_info/<int:mib_id>')
@login_required
def mib_info(mib_id):
    if not current_user.has_permission(Permission.MANAGE_MIBS):
        flash('You do not have permission to view MIB information.', 'danger')
        return redirect(url_for('mib_manager'))
    
    # Get the MIB file record
    mib_file = MibFile.query.get_or_404(mib_id)
    
    # Create MIB parser instance if the MIB is parsed
    mib_info = {}
    if mib_file.parsed:
        from mib_parser import MibParser
        mib_parser = MibParser()
        
        # Get basic information about the MIB file
        mib_module = os.path.splitext(os.path.basename(mib_file.path))[0]
        mib_info = {
            'module_name': mib_module,
            'oids': {},
            'tables': {}
        }
        
        # Try to get OIDs and tables from the MIB
        try:
            if mib_module in mib_parser.mib_builder.mibSymbols:
                mib_symbols = mib_parser.mib_builder.mibSymbols[mib_module]
                
                for symbol_name, symbol_obj in mib_symbols.items():
                    # Skip internal symbols
                    if symbol_name.startswith('_'):
                        continue
                    
                    try:
                        # Get OID for this symbol
                        oid = mib_parser.mib_view_controller.getNodeLocation((mib_module, symbol_name))
                        
                        # Add to appropriate section
                        if hasattr(symbol_obj, 'syntax') and hasattr(symbol_obj.syntax, 'clone'):
                            mib_info['oids'][symbol_name] = {
                                'oid': '.'.join([str(x) for x in oid[0]]),
                                'type': str(symbol_obj.syntax.__class__.__name__),
                                'description': getattr(symbol_obj, 'description', '')
                            }
                        elif hasattr(symbol_obj, 'createRow'):
                            mib_info['tables'][symbol_name] = {
                                'oid': '.'.join([str(x) for x in oid[0]]),
                                'description': getattr(symbol_obj, 'description', '')
                            }
                    except:
                        pass
        except Exception as e:
            flash(f'Error getting MIB information: {str(e)}', 'warning')
    
    return render_template('mib_info.html', mib_file=mib_file, mib_info=mib_info)

@app.route('/device_info/<int:mib_id>')
@login_required
def device_info(mib_id):
    if not current_user.has_permission(Permission.MANAGE_MIBS):
        flash('You do not have permission to view device information.', 'danger')
        return redirect(url_for('mib_manager'))
    
    # Get the MIB file record
    mib_file = MibFile.query.get_or_404(mib_id)
    
    # Create MIB parser instance
    from mib_parser import MibParser
    mib_parser = MibParser()
    
    # Extract device information from the MIB
    device_info = mib_parser.extract_device_info_from_mib(mib_id, mib_file.device_type)
    
    # Check for errors
    if 'error' in device_info:
        flash(f'Error extracting device information: {device_info["error"]}', 'danger')
        return redirect(url_for('mib_manager'))
    
    return render_template('device_info.html', mib_file=mib_file, device_info=device_info)

@app.route('/api_docs')
@login_required
def api_docs():
    # Only users with API access can view documentation
    if not current_user.has_permission(Permission.VIEW_FLOW_DATA):
        flash('You do not have permission to access API documentation.', 'danger')
        return redirect(url_for('dashboard'))
    
    return render_template('api_docs.html')

@app.route('/settings')
@login_required
def settings():
    # Only administrators can access settings
    if not current_user.is_administrator():
        flash('You do not have permission to access settings.', 'danger')
        return redirect(url_for('dashboard'))
    
    return render_template('settings.html', config=config)

@app.route('/update_settings', methods=['POST'])
@login_required
def update_settings():
    if request.method == 'POST':
        # Update receiver settings
        config.NETFLOW_PORT = int(request.form.get('netflow_port', 2055))
        config.SFLOW_PORT = int(request.form.get('sflow_port', 6343))
        config.MAX_PACKET_SIZE = int(request.form.get('max_packet_size', 8192))
        config.BUFFER_SIZE = int(request.form.get('buffer_size', 10000))
        
        # Update storage settings
        config.MAX_FLOWS_STORED = int(request.form.get('max_flows_stored', 1000000))
        config.FLOW_RETENTION_DAYS = int(request.form.get('flow_retention_days', 7))
        
        # Update external storage settings
        config.USE_EXTERNAL_STORAGE = 'use_external_storage' in request.form
        config.MINIO_ENDPOINT = request.form.get('minio_endpoint', 'minio:9000')
        config.MINIO_BUCKET = request.form.get('minio_bucket', 'r369-bucket')
        config.MINIO_SECURE = 'minio_secure' in request.form
        
        # Update access and secret keys only if provided (not empty)
        if request.form.get('minio_access_key'):
            config.MINIO_ACCESS_KEY = request.form.get('minio_access_key')
        if request.form.get('minio_secret_key'):
            config.MINIO_SECRET_KEY = request.form.get('minio_secret_key')
        
        # Update analysis settings
        config.ANOMALY_DETECTION_THRESHOLD = float(request.form.get('anomaly_detection_threshold', 0.05))
        config.MIN_FLOWS_FOR_ANALYSIS = int(request.form.get('min_flows_for_analysis', 10))
        
        # If external storage was enabled, initialize the storage manager
        if config.USE_EXTERNAL_STORAGE:
            from storage_manager import get_storage_manager
            storage_mgr = get_storage_manager()
            storage_success = storage_mgr._init_minio_client()
            
            if storage_success:
                flash('External storage connected successfully!', 'success')
            else:
                flash('Failed to connect to external storage. Please check your settings.', 'error')
        
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('settings'))

# Import caching utilities
try:
    import sys
    sys.path.append('../../../tools')
    from cache_manager import cache_response, QueryCache
    CACHING_ENABLED = True
except ImportError:
    # Fallback if caching not available
    def cache_response(ttl=300, key_func=None):
        def decorator(func):
            return func
        return decorator
    CACHING_ENABLED = False

# API endpoints for dashboard data
@app.route('/api/flow_stats')
@login_required
@cache_response(ttl=120)  # Cache for 2 minutes
def api_flow_stats():
    """
    Get time-based flow statistics for charts
    
    Returns JSON with the following structure:
    {
        'statistics': {
            'total_flows': int,
            'netflow_count': int,
            'sflow_count': int,
            'device_count': int,
            'top_source_ips': {ip: count, ...},
            'top_destination_ips': {ip: count, ...},
            'protocol_distribution': {protocol: count, ...}
        },
        'time_series': {
            'labels': [timestamp1, timestamp2, ...],
            'netflow': [count1, count2, ...],
            'sflow': [count1, count2, ...]
        },
        'recent_flows': [{flow data}, ...],
        'devices': [{device data}, ...]
    }
    """
    # Get time-based flow statistics for charts
    time_period = request.args.get('period', 'hour')
    
    # Get time range based on the selected period
    now = datetime.utcnow()
    if time_period == 'hour':
        start_time = now - timedelta(hours=1)
        interval = 5  # 5-minute intervals
        format_string = '%H:%M'
    elif time_period == 'day':
        start_time = now - timedelta(days=1)
        interval = 60  # 1-hour intervals
        format_string = '%H:%M'
    elif time_period == 'week':
        start_time = now - timedelta(weeks=1)
        interval = 1440  # 1-day intervals
        format_string = '%m-%d'
    else:
        start_time = now - timedelta(hours=1)
        interval = 5  # Default to 5-minute intervals
        format_string = '%H:%M'
    
    # Get basic statistics
    total_flows = db.session.query(FlowData).count()
    netflow_count = db.session.query(FlowData).filter(FlowData.flow_type.like('netflow%')).count()
    sflow_count = db.session.query(FlowData).filter(FlowData.flow_type.like('sflow%')).count()
    device_count = db.session.query(Device).count()
    
    # Get top source IPs (subquery method to improve performance)
    top_sources_query = db.session.query(
        FlowData.src_ip,
        db.func.count(FlowData.id).label('count')
    ).group_by(FlowData.src_ip).order_by(db.func.count(FlowData.id).desc()).limit(5).all()
    
    top_sources = {row[0]: row[1] for row in top_sources_query}
    
    # Get top destination IPs
    top_destinations_query = db.session.query(
        FlowData.dst_ip,
        db.func.count(FlowData.id).label('count')
    ).group_by(FlowData.dst_ip).order_by(db.func.count(FlowData.id).desc()).limit(5).all()
    
    top_destinations = {row[0]: row[1] for row in top_destinations_query}
    
    # Get protocol distribution
    protocol_query = db.session.query(
        FlowData.protocol,
        db.func.count(FlowData.id).label('count')
    ).group_by(FlowData.protocol).order_by(db.func.count(FlowData.id).desc()).limit(6).all()
    
    protocol_distribution = {str(row[0]): row[1] for row in protocol_query}
    
    # Generate time series data
    # This part would ideally use more efficient SQL queries with time bucketing
    time_labels = []
    netflow_counts = []
    sflow_counts = []
    
    # Sample time points for the chart
    for i in range(12):  # 12 time points
        if time_period == 'hour':
            point_time = now - timedelta(minutes=60-i*5)
            time_labels.append(point_time.strftime(format_string))
            
            # Count flows for this time period
            start_interval = point_time - timedelta(minutes=5)
            netflow_counts.append(
                db.session.query(FlowData)
                .filter(FlowData.timestamp >= start_interval, 
                        FlowData.timestamp < point_time,
                        FlowData.flow_type.like('netflow%'))
                .count()
            )
            sflow_counts.append(
                db.session.query(FlowData)
                .filter(FlowData.timestamp >= start_interval, 
                        FlowData.timestamp < point_time,
                        FlowData.flow_type.like('sflow%'))
                .count()
            )
        elif time_period == 'day':
            point_time = now - timedelta(hours=24-i*2)
            time_labels.append(point_time.strftime(format_string))
            
            # Count flows for this time period
            start_interval = point_time - timedelta(hours=2)
            netflow_counts.append(
                db.session.query(FlowData)
                .filter(FlowData.timestamp >= start_interval, 
                        FlowData.timestamp < point_time,
                        FlowData.flow_type.like('netflow%'))
                .count()
            )
            sflow_counts.append(
                db.session.query(FlowData)
                .filter(FlowData.timestamp >= start_interval, 
                        FlowData.timestamp < point_time,
                        FlowData.flow_type.like('sflow%'))
                .count()
            )
        elif time_period == 'week':
            point_time = now - timedelta(days=7-i*0.5)
            time_labels.append(point_time.strftime(format_string))
            
            # Count flows for this time period
            start_interval = point_time - timedelta(days=0.5)
            netflow_counts.append(
                db.session.query(FlowData)
                .filter(FlowData.timestamp >= start_interval, 
                        FlowData.timestamp < point_time,
                        FlowData.flow_type.like('netflow%'))
                .count()
            )
            sflow_counts.append(
                db.session.query(FlowData)
                .filter(FlowData.timestamp >= start_interval, 
                        FlowData.timestamp < point_time,
                        FlowData.flow_type.like('sflow%'))
                .count()
            )
    
    # Get recent flows
    recent_flows = db.session.query(FlowData).order_by(FlowData.timestamp.desc()).limit(20).all()
    
    # Process recent flows for the frontend
    flow_data = []
    for flow in recent_flows:
        flow_data.append({
            'id': flow.id,
            'timestamp': flow.timestamp,
            'flow_type': flow.flow_type,
            'src_ip': flow.src_ip,
            'src_port': flow.src_port,
            'dst_ip': flow.dst_ip,
            'dst_port': flow.dst_port,
            'protocol': flow.protocol,
            'bytes': flow.bytes,
            'packets': flow.packets
        })
    
    # Get device data
    devices_query = db.session.query(Device).all()
    devices_data = []
    
    for device in devices_query:
        # Count flows for this device
        flow_count = db.session.query(FlowData).filter_by(device_id=device.id).count()
        
        devices_data.append({
            'id': device.id,
            'name': device.name,
            'ip_address': device.ip_address,
            'flow_type': device.flow_type,
            'flow_version': device.flow_version,
            'last_seen': device.last_seen,
            'statistics': {
                'flow_count': flow_count
            }
        })
    
    # Build the response object
    response_data = {
        'statistics': {
            'total_flows': total_flows,
            'netflow_count': netflow_count,
            'sflow_count': sflow_count,
            'device_count': device_count,
            'top_source_ips': top_sources,
            'top_destination_ips': top_destinations,
            'protocol_distribution': protocol_distribution
        },
        'time_series': {
            'labels': time_labels,
            'netflow': netflow_counts,
            'sflow': sflow_counts
        },
        'recent_flows': flow_data,
        'devices': devices_data
    }
    
    return jsonify(response_data)

@app.route('/api/devices')
@login_required
@cache_response(ttl=180)  # Cache for 3 minutes
def api_devices():
    """Get information about all devices"""
    devices_query = db.session.query(Device).all()
    devices_data = []
    
    for device in devices_query:
        # Count flows for this device
        flow_count = db.session.query(FlowData).filter_by(device_id=device.id).count()
        
        devices_data.append({
            'id': device.id,
            'name': device.name,
            'ip_address': device.ip_address,
            'flow_type': device.flow_type,
            'flow_version': device.flow_version,
            'last_seen': device.last_seen,
            'statistics': {
                'flow_count': flow_count
            }
        })
    
    return jsonify({'devices': devices_data})

@app.route('/api/device_data/<int:device_id>')
@login_required  
@cache_response(ttl=90)  # Cache for 90 seconds
def api_device_data(device_id):
    """Get detailed data for a specific device"""
    # Get device info
    device = Device.query.get_or_404(device_id)
    
    # Get flow data for this device
    flows = FlowData.query.filter_by(device_id=device_id).order_by(FlowData.timestamp.desc()).limit(100).all()
    
    # Process the data for the frontend
    flow_data = []
    for flow in flows:
        flow_data.append({
            'id': flow.id,
            'timestamp': flow.timestamp,
            'flow_type': flow.flow_type,
            'src_ip': flow.src_ip,
            'src_port': flow.src_port,
            'dst_ip': flow.dst_ip,
            'dst_port': flow.dst_port,
            'protocol': flow.protocol,
            'bytes': flow.bytes,
            'packets': flow.packets,
            'tos': flow.tos
        })
    
    # Get protocol distribution for this device
    protocol_query = db.session.query(
        FlowData.protocol,
        db.func.count(FlowData.id).label('count')
    ).filter_by(device_id=device_id).group_by(FlowData.protocol).order_by(db.func.count(FlowData.id).desc()).all()
    
    protocol_distribution = {str(row[0]): row[1] for row in protocol_query}
    
    # Get top talkers for this device
    top_sources_query = db.session.query(
        FlowData.src_ip,
        db.func.count(FlowData.id).label('count')
    ).filter_by(device_id=device_id).group_by(FlowData.src_ip).order_by(db.func.count(FlowData.id).desc()).limit(5).all()
    
    top_sources = {row[0]: row[1] for row in top_sources_query}
    
    # Get top destinations for this device
    top_destinations_query = db.session.query(
        FlowData.dst_ip,
        db.func.count(FlowData.id).label('count')
    ).filter_by(device_id=device_id).group_by(FlowData.dst_ip).order_by(db.func.count(FlowData.id).desc()).limit(5).all()
    
    top_destinations = {row[0]: row[1] for row in top_destinations_query}
    
    return jsonify({
        'device': {
            'id': device.id,
            'name': device.name,
            'ip_address': device.ip_address,
            'flow_type': device.flow_type,
            'flow_version': device.flow_version,
            'last_seen': device.last_seen,
            'created_at': device.created_at
        },
        'flows': flow_data,
        'statistics': {
            'flow_count': len(flows),
            'protocol_distribution': protocol_distribution,
            'top_sources': top_sources,
            'top_destinations': top_destinations
        }
    })


# AI Insights API routes
@app.route('/api/ai_insights/<int:device_id>')
@login_required
def api_ai_insights(device_id):
    """
    Get AI-powered insights for a specific device
    
    Returns JSON with AI analysis results including:
    - Anomaly detection
    - Traffic pattern analysis
    - Network behavior classification
    - Predictive analytics
    """
    try:
        device = Device.query.get_or_404(device_id)
        
        # Check if user has access to this device
        if not current_user.can_access_device(device.id):
            return jsonify({"error": "Access denied"}), 403
        
        # Get time window parameters
        time_period = request.args.get('period', 'day')
        start_time = None
        end_time = None
        
        # Parse time window parameters
        now = datetime.utcnow()
        if time_period == 'hour':
            start_time = now - timedelta(hours=1)
        elif time_period == 'day':
            start_time = now - timedelta(days=1)
        elif time_period == 'week':
            start_time = now - timedelta(weeks=1)
        elif time_period == 'month':
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(days=1)  # Default to 1 day
        
        # Create time window for AI analysis
        time_window = {
            'start': start_time,
            'end': now
        }
        
        # Run AI analysis (will be cached in the database)
        analysis_results = ai_insights_manager.analyze_device_data(device_id, time_window)
        
        # Check for error
        if 'error' in analysis_results:
            return jsonify({
                "error": analysis_results['error'],
                "device_id": device_id,
                "time_window": {
                    "start": start_time.isoformat(),
                    "end": now.isoformat()
                }
            }), 400
        
        # Return the results
        return jsonify(analysis_results)
        
    except Exception as e:
        logger.error(f"Error getting AI insights: {str(e)}")
        return jsonify({"error": str(e)}), 500




@app.route('/api/anomalies')
@login_required
def api_anomalies():
    """
    Get recent anomalies detected across all devices
    
    Returns JSON with a list of recent anomaly detections
    """
    try:
        # Check if user has permission to view flow data
        if not current_user.has_permission(Permission.VIEW_FLOW_DATA):
            return jsonify({"error": "Access denied"}), 403
        
        # Get limit parameter (default to 10)
        limit = request.args.get('limit', 10, type=int)
        
        # Get recent anomalies
        anomalies = ai_insights_manager.get_recent_anomalies(limit)
        
        # Filter to only show anomalies for devices the user can access
        if not current_user.is_administrator():
            accessible_devices = [d.id for d in current_user.get_accessible_devices()]
            anomalies = [a for a in anomalies if a['device_id'] in accessible_devices]
        
        return jsonify({
            "anomalies": anomalies,
            "count": len(anomalies)
        })
        
    except Exception as e:
        logger.error(f"Error getting anomalies: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/forwarder_stats')
@login_required
def api_forwarder_stats():
    """
    Get statistics about the flow forwarder
    
    Returns JSON with statistics about the flow forwarder:
    - running: whether the forwarder is running
    - queue_size: current number of flows in the queue
    - queue_capacity: maximum queue capacity
    - active_targets: number of active forward targets
    - total_targets: total number of configured targets
    """
    try:
        # Check if user has permission
        if not current_user.has_permission(Permission.VIEW_FLOW_DATA):
            return jsonify({"error": "Access denied"}), 403
            
        # Get stats from the flow forwarder
        stats = flow_forwarder.get_stats()
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Error getting forwarder stats: {str(e)}")
        return jsonify({
            'error': f"Failed to get forwarder statistics: {str(e)}",
            'running': False,
            'queue_size': 0,
            'queue_capacity': 0,
            'active_targets': 0,
            'total_targets': 0,
            'forwarded_flows': 0,
            'dropped_flows': 0
        }), 500

# Maintenance routes
@app.route('/cleanup_old_flows')
def cleanup_old_flows():
    """Clean up old flow data based on retention policy"""
    from storage_manager import get_storage_manager
    
    try:
        storage_mgr = get_storage_manager()
        local_cleaned, external_cleaned = storage_mgr.clean_old_data()
        
        message = f"Successfully removed {local_cleaned} old flow records from database"
        if external_cleaned > 0:
            message += f" and {external_cleaned} objects from external storage"
        
        flash(message, 'success')
    except Exception as e:
        flash(f"Error cleaning up old flow data: {str(e)}", 'error')
    
    return redirect(url_for('settings'))

@app.route('/clear_unused_devices')
def clear_unused_devices():
    """Remove unused device records (no flow data)"""
    try:
        # Get all devices
        devices = Device.query.all()
        removed_count = 0
        
        # Check each device for flow data
        for device in devices:
            flow_count = FlowData.query.filter_by(device_id=device.id).count()
            if flow_count == 0:
                db.session.delete(device)
                removed_count += 1
        
        db.session.commit()
        flash(f"Successfully removed {removed_count} unused device records", 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Error removing unused devices: {str(e)}", 'error')
    
    return redirect(url_for('settings'))

@app.route('/restart_services')
def restart_services():
    """Restart flow collection services"""
    try:
        # Stop current services if running
        flow_receiver.stop()
        flow_forwarder.stop()
        
        # Start services again
        start_flow_services()
        
        flash("Flow services restarted successfully", 'success')
    except Exception as e:
        flash(f"Error restarting services: {str(e)}", 'error')
    
    return redirect(url_for('settings'))

# Flow services will be started by create_app() when the app is properly initialized

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))  # Use PORT env var or default to 5001
    app.run(host="0.0.0.0", port=port, debug=False)
