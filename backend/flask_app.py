"""
Multi-Screen Display Server

A Flask-based server for managing multi-screen video streaming.
"""

import os
import time
import threading
import logging
from flask import Flask, jsonify  # type: ignore
from flask_cors import CORS  # type: ignore
from flask_session import Session  # type: ignore
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

# Handle imports for both direct execution and module import
try:
    from .app_config import AppConfig  # type: ignore
    from .blueprints.group_management import group_bp  # type: ignore
    from .blueprints.video_management import video_bp  # type: ignore
    from .blueprints.client_management import client_bp  # type: ignore
    from .blueprints.streaming import multi_stream_bp, split_stream_bp  # type: ignore
    from .blueprints.docker_management import docker_bp  # type: ignore
    from .blueprints.auth_management import auth_bp  # type: ignore
except ImportError:
    # Fallback for direct execution
    from app_config import AppConfig  # type: ignore
    from blueprints.group_management import group_bp  # type: ignore
    from blueprints.video_management import video_bp  # type: ignore
    from blueprints.client_management import client_bp  # type: ignore
    from blueprints.streaming import multi_stream_bp, split_stream_bp  # type: ignore
    from blueprints.docker_management import docker_bp  # type: ignore
    from blueprints.auth_management import auth_bp  # type: ignore


def clear_all_logs():
    """Rotate all log files to keep only the newest 1000 lines when server starts"""
    try:
        logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
        if os.path.exists(logs_dir):
            try:
                from logging_config import rotate_existing_logs, MAX_LOG_LINES
                rotate_existing_logs(logs_dir, max_lines=MAX_LOG_LINES)
                print(f"All log files rotated to keep newest {MAX_LOG_LINES} lines")
            except ImportError:
                # Fallback to clearing logs if logging_config not available
                log_files = [
                    'all.log',
                    'errors.log', 
                    'ffmpeg.log',
                    'clients.log',
                    'streaming.log',
                    'system.log'
                ]
                
                for log_file in log_files:
                    log_path = os.path.join(logs_dir, log_file)
                    if os.path.exists(log_path):
                        # Clear the file content
                        with open(log_path, 'w') as f:
                            f.write(f"# Log file cleared at server startup: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                            f.write(f"# Server session started\n")
                            f.write("=" * 80 + "\n\n")
                        print(f"Cleared log file: {log_file}")
    except Exception as e:
        print(f"Warning: Could not rotate log files: {e}")

# Configure comprehensive logging
try:
    from logging_config import setup_comprehensive_logging, MAX_LOG_LINES
    logger = setup_comprehensive_logging()
    
    # Clear all logs at startup
    clear_all_logs()
    
    logger.info("Enhanced logging system initialized")
    logger.info(f"All log files rotated to keep newest {MAX_LOG_LINES} lines for new server session")
except ImportError:
    # Fallback to basic logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.warning("Enhanced logging not available, using basic logging")

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Configure session
    app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SESSION_TYPE'] = 'mongodb'
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_USE_SIGNER'] = True
    app.config['SESSION_KEY_PREFIX'] = 'openvideowall:'
    app.config['SESSION_COOKIE_NAME'] = 'openvideowall_session'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # Get MongoDB client for session storage
    try:
        from db.mongo import get_mongo_client
    except ImportError:
        try:
            from .db.mongo import get_mongo_client
        except ImportError:
            pass
    
    # Configure MongoDB session storage
    mongo_client = get_mongo_client()
    if mongo_client is not None:
        app.config['SESSION_MONGODB'] = mongo_client
        app.config['SESSION_MONGODB_DB'] = os.environ.get('OPENVIDEOWALL_MONGO_DB', 'openvideowall')
        app.config['SESSION_MONGODB_COLLECT'] = 'flask_sessions'
        logger.info("Session storage configured to use MongoDB")
    else:
        logger.warning("MongoDB not available, sessions will not persist")
    
    # Initialize session
    Session(app)
    
    # Enable CORS for all routes
    CORS(app, resources={
        r"/*": {
            "origins": [
                "http://localhost:3000",           # React dev server
                "http://127.0.0.1:3000",          # React dev server alternative
                "http://localhost:5173",           # Vite dev server
                "http://127.0.0.1:5173",          # Vite dev server alternative
                "http://128.205.39.64:3000",      # Your server's frontend
                "http://128.205.39.64:5173",      # Your server's frontend alternative
                "*"                               # Allow all origins (for development)
            ],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
            "supports_credentials": True
        }
    })
    
    # Load configuration
    config = AppConfig()
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
    app.config['UNIFIED_CONFIG'] = config
    
    # Initialize persistent client state
    from blueprints.client_management.client_state import get_persistent_state
    app.config['APP_STATE'] = get_persistent_state()

    # SQL database disabled for Mongo-only mode
    logger.info("SQL database is disabled (Mongo-only mode)")

    # Initialize MongoDB if configured
    try:
        try:
            from .db.mongo import is_mongo_enabled, ensure_indexes  # type: ignore
        except ImportError:
            from db.mongo import is_mongo_enabled, ensure_indexes  # type: ignore
        if is_mongo_enabled():
            ensure_indexes()
            logger.info("MongoDB enabled and indexes ensured")
            # Preload clients from Mongo into in-memory state
            try:
                try:
                    from .db.mongo import find_all  # type: ignore
                except ImportError:
                    from db.mongo import find_all  # type: ignore
                state = app.config['APP_STATE']
                docs = find_all("clients")
                if docs:
                    for doc in docs:
                        cid = doc.get('client_id')
                        if cid:
                            try:
                                state.add_client(cid, doc)
                            except Exception as e:
                                logger.warning(f"Failed to load client {cid} from Mongo into state: {e}")
                    logger.info(f"Loaded {len(docs)} clients from MongoDB into state")
            except Exception as mongo_preload_e:
                logger.warning(f"Could not preload clients from MongoDB: {mongo_preload_e}")
        else:
            logger.info("MongoDB not enabled (set OPENVIDEOWALL_MONGO_URL to enable)")
    except Exception as mongo_e:
        logger.warning(f"MongoDB initialization skipped or failed: {mongo_e}")
    
    # Create uploads directory
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize default admin user
    try:
        try:
            from .blueprints.auth_management.auth_service import AuthService  # type: ignore
        except ImportError:
            from blueprints.auth_management.auth_service import AuthService  # type: ignore
        
        auth_service = AuthService()
        auth_service.initialize_default_admin()
        logger.info("Authentication system initialized")
    except Exception as auth_e:
        logger.warning(f"Authentication initialization failed: {auth_e}")
    
    # Register blueprints
    app.register_blueprint(group_bp)
    app.register_blueprint(video_bp)
    app.register_blueprint(client_bp, url_prefix='/api/clients')
    app.register_blueprint(multi_stream_bp, url_prefix='/api/streaming')
    app.register_blueprint(split_stream_bp, url_prefix='/api/streaming')
    app.register_blueprint(auth_bp)
    
    # Add backward compatibility routes (without prefix) with unique names
    app.register_blueprint(multi_stream_bp, url_prefix='', name='multi_stream_legacy')
    app.register_blueprint(split_stream_bp, url_prefix='', name='split_stream_legacy')
    app.register_blueprint(docker_bp)

    
    # Root endpoint
    @app.route('/')
    def index():
        return jsonify({
            "api_endpoints": {
                "clients": "/api/clients",
                "docker": "/api/docker",
                "groups": "/api/groups",
                "multi_stream": "/api/streaming/start_multi_video_srt",
                "split_stream": "/api/streaming/start_split_screen_srt",
                "streaming_status": "/api/streaming/all_streaming_statuses",
                "stop_stream": "/api/streaming/stop_group_stream",
                "videos": "/api/videos",

            },
            "status": "running",
            "version": "2.0.0"
        })
    
    # Health check endpoint
    @app.route('/health')
    def health():
        return jsonify({
            "status": "healthy",
            "timestamp": time.time(),
            "service": "multi_screen_server"
        })
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Endpoint not found"}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "Internal server error"}), 500
    
    return app

# Create app instance
app = create_app()

if __name__ == '__main__':
    logger.info("Starting Multi-Screen Display Server...")
    logger.info(f"Server config: 0.0.0.0:5000, debug=True")
    
    # Run the app
    app.run(host='0.0.0.0', port=5000, debug=True)