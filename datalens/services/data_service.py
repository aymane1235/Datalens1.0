import pandas as pd
import numpy as np
import os
import json
from werkzeug.utils import secure_filename
from models.dataset import Dataset
from models import db

class DataService:
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
    
    @staticmethod
    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in DataService.ALLOWED_EXTENSIONS
    
    @staticmethod
    def save_file(file, upload_folder):
        if file and DataService.allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            return filename, file_path
        return None, None
    
    @staticmethod
    def read_file(file_path):
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path)
            else:
                return None, "Unsupported file format"
            
            return df, None
        except Exception as e:
            return None, str(e)
    
    @staticmethod
    def get_columns_info(df):
        columns_info = {}
        for column in df.columns:
            dtype = str(df[column].dtype)
            columns_info[column] = {
                'type': dtype,
                'non_null_count': int(df[column].count()),
                'null_count': int(df[column].isnull().sum())
            }
        return columns_info
    
    @staticmethod
    def get_missing_values(df):
        missing_values = {}
        for column in df.columns:
            missing_count = df[column].isnull().sum()
            if missing_count > 0:
                missing_values[column] = {
                    'count': int(missing_count),
                    'percentage': round((int(missing_count) / len(df)) * 100, 2)
                }
        return missing_values
    
    @staticmethod
    def get_statistics(df):
        statistics = {}
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        
        for column in df.columns:
            if column in numeric_columns:
                try:
                    statistics[column] = {
                        'mean': float(df[column].mean()),
                        'median': float(df[column].median()),
                        'min': float(df[column].min()),
                        'max': float(df[column].max()),
                        'std': float(df[column].std()) if not pd.isna(df[column].std()) else None,
                        'count': int(df[column].count())
                    }
                except:
                    statistics[column] = {
                        'error': 'Cannot calculate statistics for this column'
                    }
            else:
                statistics[column] = {
                    'type': 'categorical',
                    'unique_count': int(df[column].nunique()),
                    'most_frequent': str(df[column].mode().iloc[0]) if not df[column].mode().empty else None,
                    'count': int(df[column].count())
                }
        
        return statistics
    
    @staticmethod
    def convert_numpy_types(obj):
        """Convert numpy types to Python native types for JSON serialization"""
        if isinstance(obj, dict):
            return {key: DataService.convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [DataService.convert_numpy_types(item) for item in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            if np.isnan(obj):
                return None
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        else:
            return obj

    @staticmethod
    def create_dataset(name, filename, file_path, file_size, df, user_id):
        columns_info = DataService.get_columns_info(df)
        missing_values = DataService.get_missing_values(df)
        statistics = DataService.get_statistics(df)
        
        # Convert all numpy types to Python native types
        columns_info = DataService.convert_numpy_types(columns_info)
        missing_values = DataService.convert_numpy_types(missing_values)
        statistics = DataService.convert_numpy_types(statistics)
        
        dataset = Dataset(
            name=name,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            rows_count=int(len(df)),
            columns_count=int(len(df.columns)),
            columns_info=columns_info,
            missing_values=missing_values,
            statistics=statistics,
            user_id=user_id
        )
        
        db.session.add(dataset)
        db.session.commit()
        
        return dataset
    
    @staticmethod
    def get_preview(df, rows=10):
        preview_data = df.head(rows).to_dict('records')
        return DataService.convert_numpy_types(preview_data)
    
    @staticmethod
    def get_user_datasets(user_id):
        return Dataset.query.filter_by(user_id=user_id).order_by(Dataset.created_at.desc()).all()
    
    @staticmethod
    def get_dataset_by_id(dataset_id, user_id):
        return Dataset.query.filter_by(id=dataset_id, user_id=user_id).first()
