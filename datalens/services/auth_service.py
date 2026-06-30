from flask import session
from models.user import User
from models import db

class AuthService:
    @staticmethod
    def register_user(username, email, password):
        if User.query.filter_by(username=username).first():
            return False, "Username already exists"
        
        if User.query.filter_by(email=email).first():
            return False, "Email already exists"
        
        user = User(username=username, email=email)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        return True, user
    
    @staticmethod
    def login_user(username, password):
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            return True, user
        
        return False, "Invalid username or password"
    
    @staticmethod
    def logout_user():
        session.clear()
    
    @staticmethod
    def get_current_user():
        if 'user_id' in session:
            return User.query.get(session['user_id'])
        return None
    
    @staticmethod
    def is_authenticated():
        return 'user_id' in session
