# DataLens - Data Analytics Platform

DataLens is a comprehensive web application for data analytics and visualization built with Flask. It allows users to upload datasets, perform statistical analysis, and visualize data patterns.

## Features

- **User Authentication**: Secure registration, login, and logout system with password hashing
- **File Upload**: Support for CSV, XLSX, and XLS file formats
- **Data Preview**: Quick preview of the first 10 rows of uploaded datasets
- **Statistical Analysis**: Automatic calculation of descriptive statistics (mean, median, min, max, standard deviation)
- **Missing Values Detection**: Identify and analyze missing data patterns
- **Dashboard**: Centralized view of all datasets with key metrics
- **Data Management**: View, analyze, and delete datasets

## Technology Stack

- **Backend**: Python 3.8+, Flask
- **Database**: MySQL with PyMySQL and Flask-SQLAlchemy
- **Data Processing**: Pandas, NumPy, OpenPyXL
- **Security**: Werkzeug for password hashing
- **Frontend**: HTML5, CSS3, JavaScript (vanilla), Jinja2 templating

## Installation

### Prerequisites

- Python 3.8 or higher
- MySQL server
- pip package manager

### Setup Instructions

1. **Clone or download the project**
   ```bash
   cd datalens
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up the database**
   - Create a MySQL database named `datalens`
   - Ensure MySQL is running on localhost:3306 with user `root` and no password
   
   ```sql
   CREATE DATABASE datalens;
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the application**
   Open your web browser and navigate to `http://localhost:5000`

## Configuration

### Database Configuration

The database configuration is set in `config.py`:

```python
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost:3306/datalens'
```

To modify database settings:
- **Host**: Change `localhost` to your MySQL server host
- **Port**: Change `3306` to your MySQL port
- **User**: Change `root` to your MySQL username
- **Password**: Add password after `:` if your MySQL user has a password
- **Database**: Change `datalens` to your preferred database name

### File Upload Configuration

- **Max file size**: 16MB (configurable in `config.py`)
- **Upload folder**: `uploads/` directory in the project root
- **Supported formats**: CSV, XLSX, XLS

## Project Structure

```
datalens/
├── app.py                 # Main application entry point
├── config.py              # Application configuration
├── requirements.txt       # Python dependencies
├── models/                # Database models
│   ├── __init__.py
│   ├── user.py           # User model
│   └── dataset.py        # Dataset model
├── routes/                # Application routes
│   ├── __init__.py
│   ├── auth.py           # Authentication routes
│   └── main.py           # Main application routes
├── services/              # Business logic services
│   ├── __init__.py
│   ├── auth_service.py   # Authentication service
│   └── data_service.py   # Data processing service
├── static/                # Static files
│   ├── css/
│   │   └── style.css     # Main stylesheet
│   └── js/
│       └── script.js     # JavaScript functionality
├── templates/             # Jinja2 templates
│   ├── base.html         # Base template
│   ├── index.html        # Home page
│   ├── dashboard.html    # User dashboard
│   ├── upload.html       # File upload page
│   ├── dataset.html      # Dataset view page
│   └── auth/             # Authentication templates
│       ├── login.html    # Login page
│       └── register.html # Registration page
└── uploads/               # Uploaded files storage
```

## Database Schema

### Users Table
- `id`: Primary key
- `username`: Unique username
- `email`: Unique email address
- `password_hash`: Hashed password
- `created_at`: Account creation timestamp

### Datasets Table
- `id`: Primary key
- `name`: Dataset name
- `filename`: Original filename
- `file_path`: Server file path
- `file_size`: File size in bytes
- `rows_count`: Number of rows
- `columns_count`: Number of columns
- `columns_info`: JSON with column information
- `missing_values`: JSON with missing values analysis
- `statistics`: JSON with statistical analysis
- `created_at`: Upload timestamp
- `user_id`: Foreign key to users table

## Usage

1. **Register an account**: Click "Register" on the home page
2. **Login**: Use your credentials to access the dashboard
3. **Upload data**: Click "Upload New Dataset" and select a CSV/XLSX/XLS file
4. **Analyze data**: View automatic statistics and missing values analysis
5. **Manage datasets**: View, analyze, or delete datasets from the dashboard

## Security Features

- Password hashing using Werkzeug
- Session-based authentication
- File upload validation
- SQL injection prevention through SQLAlchemy ORM
- XSS protection through Jinja2 templating

## Development

### Running in Development Mode

```bash
python app.py
```

The application will run in debug mode with auto-reloading enabled.

### Adding New Features

1. **New routes**: Add to appropriate files in `routes/` directory
2. **New models**: Add to `models/` directory
3. **New services**: Add business logic to `services/` directory
4. **New templates**: Add to `templates/` directory
5. **New static files**: Add CSS/JS to `static/` directory

## Troubleshooting

### Common Issues

1. **Database connection errors**
   - Ensure MySQL server is running
   - Check database credentials in `config.py`
   - Verify the database exists

2. **File upload errors**
   - Check file size (max 16MB)
   - Verify file format (CSV, XLSX, XLS)
   - Ensure uploads directory has write permissions

3. **Import errors**
   - Activate virtual environment
   - Install all dependencies: `pip install -r requirements.txt`

## License

This project is open source and available under the MIT License.
