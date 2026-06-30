import pandas as pd
import numpy as np
import json
from collections import Counter
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import LabelEncoder

class VisualizationService:
    
    @staticmethod
    def prepare_bar_chart_data(df, x_column, y_column=None):
        """Prepare data for bar chart"""
        if y_column is None:
            # Count occurrences of x_column values
            value_counts = df[x_column].value_counts().head(10)
            return {
                'labels': value_counts.index.tolist(),
                'data': value_counts.values.tolist(),
                'type': 'bar'
            }
        else:
            # Group by x_column and aggregate y_column
            grouped = df.groupby(x_column)[y_column].sum().head(10)
            return {
                'labels': grouped.index.tolist(),
                'data': grouped.values.tolist(),
                'type': 'bar'
            }
    
    @staticmethod
    def prepare_line_chart_data(df, x_column, y_column):
        """Prepare data for line chart"""
        # Sort by x_column if it's numeric or datetime
        if pd.api.types.is_numeric_dtype(df[x_column]) or pd.api.types.is_datetime64_any_dtype(df[x_column]):
            df_sorted = df.sort_values(x_column)
        else:
            df_sorted = df
            
        return {
            'labels': df_sorted[x_column].tolist(),
            'data': df_sorted[y_column].tolist(),
            'type': 'line'
        }
    
    @staticmethod
    def prepare_pie_chart_data(df, column):
        """Prepare data for pie chart"""
        value_counts = df[column].value_counts().head(8)  # Limit to 8 categories for readability
        return {
            'labels': value_counts.index.tolist(),
            'data': value_counts.values.tolist(),
            'type': 'pie'
        }
    
    @staticmethod
    def prepare_scatter_chart_data(df, x_column, y_column):
        """Prepare data for scatter chart"""
        # Remove null values
        df_clean = df[[x_column, y_column]].dropna()
        
        return {
            'datasets': [{
                'label': f'{y_column} vs {x_column}',
                'data': [
                    {'x': float(row[x_column]), 'y': float(row[y_column])}
                    for _, row in df_clean.iterrows()
                ],
                'backgroundColor': 'rgba(54, 162, 235, 0.6)',
                'borderColor': 'rgba(54, 162, 235, 1)'
            }],
            'type': 'scatter'
        }
    
    @staticmethod
    def prepare_histogram_data(df, column, bins=10):
        """Prepare data for histogram"""
        # Remove null values
        data = df[column].dropna()
        
        # Create histogram
        hist, bin_edges = np.histogram(data, bins=bins)
        
        # Create labels for bins
        labels = [f'{bin_edges[i]:.1f}-{bin_edges[i+1]:.1f}' for i in range(len(hist))]
        
        return {
            'labels': labels,
            'data': hist.tolist(),
            'type': 'bar'
        }
    
    @staticmethod
    def get_numeric_columns(df):
        """Get list of numeric columns"""
        return df.select_dtypes(include=[np.number]).columns.tolist()
    
    @staticmethod
    def get_categorical_columns(df):
        """Get list of categorical columns"""
        return df.select_dtypes(include=['object', 'category']).columns.tolist()
    
    @staticmethod
    def get_datetime_columns(df):
        """Get list of datetime columns"""
        return df.select_dtypes(include=['datetime64']).columns.tolist()
    
    @staticmethod
    def generate_suggested_charts(df):
        """Generate suggested charts based on data types"""
        suggestions = []
        numeric_cols = VisualizationService.get_numeric_columns(df)
        categorical_cols = VisualizationService.get_categorical_columns(df)
        datetime_cols = VisualizationService.get_datetime_columns(df)
        
        # Bar charts for categorical data
        for col in categorical_cols[:3]:  # Limit to first 3 categorical columns
            if df[col].nunique() <= 20:  # Only if reasonable number of categories
                suggestions.append({
                    'type': 'bar',
                    'title': f'Distribution of {col}',
                    'x_column': col,
                    'description': f'Count of each category in {col}'
                })
        
        # Pie charts for categorical data with few categories
        for col in categorical_cols[:2]:  # Limit to first 2 categorical columns
            if df[col].nunique() <= 8:  # Only if few categories
                suggestions.append({
                    'type': 'pie',
                    'title': f'Proportion of {col}',
                    'column': col,
                    'description': f'Percentage distribution of {col}'
                })
        
        # Histograms for numeric data
        for col in numeric_cols[:3]:  # Limit to first 3 numeric columns
            suggestions.append({
                'type': 'histogram',
                'title': f'Distribution of {col}',
                'column': col,
                'description': f'Frequency distribution of {col}'
            })
        
        # Scatter plots for pairs of numeric columns
        if len(numeric_cols) >= 2:
            suggestions.append({
                'type': 'scatter',
                'title': f'{numeric_cols[0]} vs {numeric_cols[1]}',
                'x_column': numeric_cols[0],
                'y_column': numeric_cols[1],
                'description': f'Relationship between {numeric_cols[0]} and {numeric_cols[1]}'
            })
        
        # Line charts for datetime data
        if datetime_cols and numeric_cols:
            suggestions.append({
                'type': 'line',
                'title': f'{numeric_cols[0]} over {datetime_cols[0]}',
                'x_column': datetime_cols[0],
                'y_column': numeric_cols[0],
                'description': f'Trend of {numeric_cols[0]} over time'
            })
        
        return suggestions
    
    @staticmethod
    def prepare_combined_chart_data(df, x_column, bar_column, line_column):
        """Prepare data for combined bar + line chart"""
        # Group by x_column and aggregate both columns
        grouped = df.groupby(x_column).agg({
            bar_column: 'sum',
            line_column: 'mean'
        }).head(15)
        
        return {
            'labels': grouped.index.tolist(),
            'datasets': [
                {
                    'label': bar_column,
                    'data': grouped[bar_column].tolist(),
                    'type': 'bar',
                    'backgroundColor': 'rgba(54, 162, 235, 0.6)',
                    'borderColor': 'rgba(54, 162, 235, 1)',
                    'yAxisID': 'y'
                },
                {
                    'label': line_column,
                    'data': grouped[line_column].tolist(),
                    'type': 'line',
                    'backgroundColor': 'rgba(255, 99, 132, 0.2)',
                    'borderColor': 'rgba(255, 99, 132, 1)',
                    'yAxisID': 'y1'
                }
            ],
            'type': 'combined'
        }
    
    @staticmethod
    def prepare_heatmap_data(df, columns=None):
        """Prepare data for correlation heatmap"""
        if columns is None:
            # Select only numeric columns
            numeric_df = df.select_dtypes(include=[np.number])
        else:
            numeric_df = df[columns].select_dtypes(include=[np.number])
        
        if numeric_df.empty:
            return None
        
        # Calculate correlation matrix
        corr_matrix = numeric_df.corr()
        
        # Convert to format suitable for Chart.js
        labels = corr_matrix.columns.tolist()
        data = []
        
        for i, row_name in enumerate(labels):
            for j, col_name in enumerate(labels):
                correlation = corr_matrix.iloc[i, j]
                if not np.isnan(correlation):
                    data.append({
                        'x': j,
                        'y': i,
                        'v': round(correlation, 3)
                    })
        
        return {
            'labels': labels,
            'data': data,
            'type': 'heatmap'
        }
    
    @staticmethod
    def prepare_box_plot_data(df, column):
        """Prepare data for box plot"""
        # Remove null values
        data = df[column].dropna()
        
        if data.empty:
            return None
        
        # Calculate box plot statistics
        q1 = data.quantile(0.25)
        q3 = data.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        # Find outliers
        outliers = data[(data < lower_bound) | (data > upper_bound)].tolist()
        
        return {
            'min': float(data.min()),
            'q1': float(q1),
            'median': float(data.median()),
            'q3': float(q3),
            'max': float(data.max()),
            'outliers': outliers,
            'type': 'boxplot'
        }
    
    @staticmethod
    def filter_data(df, filters):
        """Apply filters to dataframe"""
        filtered_df = df.copy()
        
        for column, filter_config in filters.items():
            if column not in filtered_df.columns:
                continue
                
            filter_type = filter_config.get('type')
            
            if filter_type == 'range':
                min_val = filter_config.get('min')
                max_val = filter_config.get('max')
                if min_val is not None:
                    filtered_df = filtered_df[filtered_df[column] >= min_val]
                if max_val is not None:
                    filtered_df = filtered_df[filtered_df[column] <= max_val]
            
            elif filter_type == 'values':
                values = filter_config.get('values', [])
                if values:
                    filtered_df = filtered_df[filtered_df[column].isin(values)]
            
            elif filter_type == 'text':
                search_text = filter_config.get('text', '').lower()
                if search_text:
                    filtered_df = filtered_df[filtered_df[column].astype(str).str.lower().str.contains(search_text)]
        
        return filtered_df
    
    @staticmethod
    def analyze_correlations(df, threshold=0.7):
        """Analyze correlations and return significant ones"""
        numeric_df = df.select_dtypes(include=[np.number])
        
        if numeric_df.empty:
            return []
        
        corr_matrix = numeric_df.corr()
        significant_correlations = []
        
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                correlation = corr_matrix.iloc[i, j]
                if abs(correlation) >= threshold and not np.isnan(correlation):
                    significant_correlations.append({
                        'column1': corr_matrix.columns[i],
                        'column2': corr_matrix.columns[j],
                        'correlation': round(correlation, 3),
                        'strength': 'strong' if abs(correlation) >= 0.8 else 'moderate'
                    })
        
        # Sort by absolute correlation
        significant_correlations.sort(key=lambda x: abs(x['correlation']), reverse=True)
        
        return significant_correlations
    
    @staticmethod
    def detect_outliers(df, column, method='iqr'):
        """Detect outliers in a column"""
        if column not in df.columns:
            return []
        
        data = df[column].dropna()
        
        if method == 'iqr':
            q1 = data.quantile(0.25)
            q3 = data.quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            outlier_mask = (data < lower_bound) | (data > upper_bound)
            
        elif method == 'zscore':
            z_scores = np.abs(stats.zscore(data))
            outlier_mask = z_scores > 3
        
        outliers = data[outlier_mask]
        
        return [
            {
                'index': int(idx),
                'value': float(val),
                'column': column
            }
            for idx, val in outliers.items()
        ]
    
    @staticmethod
    def linear_regression(df, x_column, y_column):
        """Perform simple linear regression"""
        if x_column not in df.columns or y_column not in df.columns:
            return None
        
        # Remove null values
        regression_df = df[[x_column, y_column]].dropna()
        
        if len(regression_df) < 2:
            return None
        
        X = regression_df[[x_column]].values
        y = regression_df[y_column].values
        
        # Perform regression
        model = LinearRegression()
        model.fit(X, y)
        
        # Calculate predictions
        y_pred = model.predict(X)
        
        # Calculate R-squared
        r_squared = model.score(X, y)
        
        # Prepare data for plotting
        plot_data = {
            'actual': [
                {'x': float(X[i][0]), 'y': float(y[i])}
                for i in range(len(X))
            ],
            'predicted': [
                {'x': float(X[i][0]), 'y': float(y_pred[i])}
                for i in range(len(X))
            ]
        }
        
        return {
            'slope': float(model.coef_[0]),
            'intercept': float(model.intercept_),
            'r_squared': float(r_squared),
            'equation': f'y = {model.coef_[0]:.3f}x + {model.intercept_:.3f}',
            'plot_data': plot_data,
            'type': 'regression'
        }
    
    @staticmethod
    def convert_to_chart_data(df, chart_config):
        """Convert chart configuration to Chart.js data format"""
        chart_type = chart_config['type']
        
        if chart_type == 'bar':
            if 'y_column' in chart_config:
                return VisualizationService.prepare_bar_chart_data(
                    df, chart_config['x_column'], chart_config['y_column']
                )
            else:
                return VisualizationService.prepare_bar_chart_data(df, chart_config['x_column'])
        
        elif chart_type == 'line':
            return VisualizationService.prepare_line_chart_data(
                df, chart_config['x_column'], chart_config['y_column']
            )
        
        elif chart_type == 'pie':
            return VisualizationService.prepare_pie_chart_data(df, chart_config['column'])
        
        elif chart_type == 'scatter':
            return VisualizationService.prepare_scatter_chart_data(
                df, chart_config['x_column'], chart_config['y_column']
            )
        
        elif chart_type == 'histogram':
            return VisualizationService.prepare_histogram_data(df, chart_config['column'])
        
        elif chart_type == 'combined':
            return VisualizationService.prepare_combined_chart_data(
                df, chart_config['x_column'], chart_config['bar_column'], chart_config['line_column']
            )
        
        elif chart_type == 'heatmap':
            return VisualizationService.prepare_heatmap_data(df, chart_config.get('columns'))
        
        elif chart_type == 'boxplot':
            return VisualizationService.prepare_box_plot_data(df, chart_config['column'])
        
        return None
