from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

from . import db

class Dataset(db.Model):
    __tablename__ = 'datasets'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    rows_count = db.Column(db.Integer, nullable=False)
    columns_count = db.Column(db.Integer, nullable=False)
    columns_info = db.Column(db.JSON, nullable=False)
    missing_values = db.Column(db.JSON, nullable=False)
    statistics = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    def set_columns_info(self, columns_info):
        self.columns_info = json.dumps(columns_info) if isinstance(columns_info, dict) else columns_info
    
    def get_columns_info(self):
        return json.loads(self.columns_info) if isinstance(self.columns_info, str) else self.columns_info
    
    def set_missing_values(self, missing_values):
        self.missing_values = json.dumps(missing_values) if isinstance(missing_values, dict) else missing_values
    
    def get_missing_values(self):
        return json.loads(self.missing_values) if isinstance(self.missing_values, str) else self.missing_values
    
    def set_statistics(self, statistics):
        self.statistics = json.dumps(statistics) if isinstance(statistics, dict) else statistics
    
    def get_statistics(self):
        return json.loads(self.statistics) if isinstance(self.statistics, str) else self.statistics
    
    def __repr__(self):
        return f'<Dataset {self.name}>'
