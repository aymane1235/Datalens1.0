import pandas as pd
import numpy as np
from services.visualization_service import VisualizationService

class DashboardService:
    
    @staticmethod
    def convert_numpy_types(obj):
        """Convert numpy types to Python native types for JSON serialization"""
        if isinstance(obj, dict):
            return {key: DashboardService.convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [DashboardService.convert_numpy_types(item) for item in obj]
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
    def generate_auto_dashboard(df, dataset_id):
        """Generate automatic dashboard with smart chart suggestions"""
        dashboard_config = {
            'dataset_id': dataset_id,
            'charts': [],
            'summary_stats': DashboardService.get_summary_stats(df),
            'data_quality': DashboardService.assess_data_quality(df)
        }
        
        numeric_columns = VisualizationService.get_numeric_columns(df)
        categorical_columns = VisualizationService.get_categorical_columns(df)
        datetime_columns = VisualizationService.get_datetime_columns(df)
        
        # Generate charts based on data characteristics
        charts = []
        
        # 1. Data overview chart (always include)
        charts.append({
            'id': 'overview',
            'title': '📊 Dataset Overview',
            'type': 'summary',
            'position': {'row': 1, 'col': 1, 'width': 2, 'height': 1},
            'data': {
                'total_rows': len(df),
                'total_columns': len(df.columns),
                'numeric_columns': len(numeric_columns),
                'categorical_columns': len(categorical_columns),
                'missing_values': df.isnull().sum().sum(),
                'memory_usage': f"{df.memory_usage(deep=True).sum() / 1024:.1f} KB"
            }
        })
        
        # 2. Missing values chart if any
        missing_data = df.isnull().sum()
        if missing_data.sum() > 0:
            missing_cols = missing_data[missing_data > 0].head(8)
            charts.append({
                'id': 'missing_values',
                'title': '🔍 Missing Values Analysis',
                'type': 'bar',
                'position': {'row': 2, 'col': 1, 'width': 1, 'height': 1},
                'config': {
                    'x_column': missing_cols.index.tolist(),
                    'data': DashboardService.convert_numpy_types(missing_cols.values.tolist())
                }
            })
        
        # 3. Categorical data charts
        for i, col in enumerate(categorical_columns[:4]):  # Max 4 categorical charts
            if df[col].nunique() <= 10:  # Only if reasonable number of categories
                charts.append({
                    'id': f'categorical_{i}',
                    'title': f'📈 {col} Distribution',
                    'type': 'pie' if df[col].nunique() <= 6 else 'bar',
                    'position': {'row': 2 + (i // 2), 'col': 1 + (i % 2), 'width': 1, 'height': 1},
                    'config': {
                        'column': col
                    }
                })
        
        # 4. Numeric data distributions
        for i, col in enumerate(numeric_columns[:4]):  # Max 4 numeric charts
            charts.append({
                'id': f'numeric_dist_{i}',
                'title': f'📉 {col} Distribution',
                'type': 'histogram',
                'position': {'row': 3 + (i // 2), 'col': 1 + (i % 2), 'width': 1, 'height': 1},
                'config': {
                    'column': col
                }
            })
        
        # 5. Correlation heatmap if enough numeric columns
        if len(numeric_columns) >= 2:
            charts.append({
                'id': 'correlation',
                'title': '🔗 Correlation Matrix',
                'type': 'heatmap',
                'position': {'row': 1, 'col': 2, 'width': 2, 'height': 2},
                'config': {
                    'columns': numeric_columns[:8]  # Limit to 8 columns for readability
                }
            })
        
        # 6. Time series if datetime columns exist
        if datetime_columns and numeric_columns:
            charts.append({
                'id': 'timeseries',
                'title': f'📅 {numeric_columns[0]} over Time',
                'type': 'line',
                'position': {'row': 3, 'col': 2, 'width': 2, 'height': 1},
                'config': {
                    'x_column': datetime_columns[0],
                    'y_column': numeric_columns[0]
                }
            })
        
        # 7. Scatter plots for correlated variables
        correlations = VisualizationService.analyze_correlations(df, threshold=0.5)
        for i, corr in enumerate(correlations[:2]):  # Max 2 scatter plots
            charts.append({
                'id': f'scatter_{i}',
                'title': f'⚡ {corr["column1"]} vs {corr["column2"]}',
                'type': 'scatter',
                'position': {'row': 4 + i, 'col': 2, 'width': 2, 'height': 1},
                'config': {
                    'x_column': corr['column1'],
                    'y_column': corr['column2']
                }
            })
        
        # 8. Box plots for key numeric columns
        for i, col in enumerate(numeric_columns[:2]):  # Max 2 box plots
            charts.append({
                'id': f'boxplot_{i}',
                'title': f'📊 {col} Statistics',
                'type': 'boxplot',
                'position': {'row': 4 + i, 'col': 1, 'width': 1, 'height': 1},
                'config': {
                    'column': col
                }
            })
        
        dashboard_config['charts'] = DashboardService.convert_numpy_types(charts)
        return dashboard_config
    
    @staticmethod
    def get_summary_stats(df):
        """Get comprehensive summary statistics"""
        stats = {
            'dimensions': f"{df.shape[0]} rows × {df.shape[1]} columns",
            'memory_usage': f"{df.memory_usage(deep=True).sum() / 1024:.1f} KB",
            'missing_values': int(df.isnull().sum().sum()),
            'duplicate_rows': int(df.duplicated().sum()),
            'numeric_columns': len(df.select_dtypes(include=[np.number]).columns),
            'categorical_columns': len(df.select_dtypes(include=['object', 'category']).columns),
            'datetime_columns': len(df.select_dtypes(include=['datetime64']).columns)
        }
        
        # Data quality score
        total_cells = df.shape[0] * df.shape[1]
        missing_cells = df.isnull().sum().sum()
        quality_score = max(0, 100 - (missing_cells / total_cells * 100))
        stats['quality_score'] = round(float(quality_score), 1)
        
        return DashboardService.convert_numpy_types(stats)
    
    @staticmethod
    def assess_data_quality(df):
        """Assess data quality and provide recommendations"""
        issues = []
        recommendations = []
        
        # Check missing values
        missing_pct = (df.isnull().sum().sum() / (df.shape[0] * df.shape[1])) * 100
        if missing_pct > 10:
            issues.append(f"High missing data: {float(missing_pct):.1f}%")
            recommendations.append("Consider imputation or removal of missing values")
        
        # Check duplicates
        duplicate_pct = (df.duplicated().sum() / len(df)) * 100
        if duplicate_pct > 5:
            issues.append(f"High duplicate rate: {float(duplicate_pct):.1f}%")
            recommendations.append("Remove duplicate rows for cleaner analysis")
        
        # Check data types
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if df[col].nunique() < 10:
                recommendations.append(f"Column '{col}' might be categorical despite being numeric")
        
        # Check for potential outliers
        for col in numeric_cols[:5]:  # Check first 5 numeric columns
            outliers = VisualizationService.detect_outliers(df, col)
            if len(outliers) > len(df) * 0.05:  # More than 5% outliers
                recommendations.append(f"Consider investigating outliers in column '{col}'")
        
        return DashboardService.convert_numpy_types({
            'issues': issues,
            'recommendations': recommendations,
            'overall_quality': 'Good' if len(issues) == 0 else 'Needs Attention' if len(issues) <= 2 else 'Poor'
        })
    
    @staticmethod
    def get_chart_data(df, chart_config):
        """Get data for a specific chart configuration"""
        chart_type = chart_config['type']
        config = chart_config.get('config', {})
        
        if chart_type == 'summary':
            return chart_config.get('data') or config
        
        # Build chart configuration for VisualizationService
        viz_config = {'type': chart_type}
        
        if chart_type == 'bar' and 'x_column' in config and 'data' in config:
            return {
                'labels': config['x_column'],
                'data': config['data'],
                'type': 'bar'
            }
        
        if 'column' in config:
            viz_config['column'] = config['column']
        
        if 'x_column' in config:
            viz_config['x_column'] = config['x_column']
        
        if 'y_column' in config:
            viz_config['y_column'] = config['y_column']
        
        if 'columns' in config:
            viz_config['columns'] = config['columns']
        
        return VisualizationService.convert_to_chart_data(df, viz_config)
    
    @staticmethod
    def generate_insights(df):
        """Generate automatic insights from the data"""
        insights = []
        
        numeric_cols = VisualizationService.get_numeric_columns(df)
        categorical_cols = VisualizationService.get_categorical_columns(df)
        
        # Insight 1: Most correlated variables
        correlations = VisualizationService.analyze_correlations(df, threshold=0.7)
        if correlations:
            top_corr = correlations[0]
            insights.append({
                'type': 'correlation',
                'title': 'Strong Correlation Found',
                'description': f"{top_corr['column1']} and {top_corr['column2']} are strongly correlated (r={float(top_corr['correlation']):.3f})",
                'icon': '🔗'
            })
        
        # Insight 2: Data distribution
        if numeric_cols:
            most_variable = max(numeric_cols, key=lambda col: df[col].std())
            insights.append({
                'type': 'variability',
                'title': 'Highest Variability',
                'description': f"{most_variable} shows the highest variability (std={float(df[most_variable].std()):.2f})",
                'icon': '📊'
            })
        
        # Insight 3: Categorical insights
        if categorical_cols:
            most_diverse = max(categorical_cols, key=lambda col: df[col].nunique())
            insights.append({
                'type': 'diversity',
                'title': 'Most Diverse Category',
                'description': f"{most_diverse} has the most unique values ({df[most_diverse].nunique()} categories)",
                'icon': '🎯'
            })
        
        # Insight 4: Missing data pattern
        missing_cols = df.isnull().sum()
        if missing_cols.sum() > 0:
            most_missing = missing_cols.idxmax()
            insights.append({
                'type': 'missing_data',
                'title': 'Missing Data Pattern',
                'description': f"{most_missing} has the most missing values ({int(missing_cols[most_missing])} rows)",
                'icon': '🔍'
            })
        
        return DashboardService.convert_numpy_types(insights)
