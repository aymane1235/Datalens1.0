from flask import Flask
from config import Config
import os

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Import database and models
from models import db, user, dataset

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize database
    db.init_app(app)
    
    # Create upload directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Import and register blueprints
    from routes.auth import auth_bp
    from routes.main import main_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    
    # Make current_user available in templates
    @app.context_processor
    def inject_user():
        from services.auth_service import AuthService
        return dict(current_user=AuthService.get_current_user())
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
