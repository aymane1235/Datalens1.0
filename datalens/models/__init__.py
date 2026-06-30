from flask_sqlalchemy import SQLAlchemy

# Create shared database instance
db = SQLAlchemy()

from .user import User
from .dataset import Dataset

__all__ = ['db', 'User', 'Dataset']
