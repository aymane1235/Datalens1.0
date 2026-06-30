from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app, send_file
from services.auth_service import AuthService
from services.data_service import DataService
from services.visualization_service import VisualizationService
from services.dashboard_service import DashboardService
from services.ai_service import AIService
from services.ai_assistant import DataLensAIAssistant
from services.auto_ai_analyzer import AutoAIAnalyzer
from services.pdf_report_service import PDFReportService
from services.dashboard_code_service import DashboardCodeService
from models.dataset import Dataset
import os
import markdown
from io import BytesIO

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if AuthService.is_authenticated():
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main_bp.route('/dashboard')
def dashboard():
    if not AuthService.is_authenticated():
        return redirect(url_for('auth.login'))
    
    user = AuthService.get_current_user()
    datasets = DataService.get_user_datasets(user.id)
    total_rows = sum((d.rows_count or 0) for d in datasets)
    total_size_bytes = sum((d.file_size or 0) for d in datasets)
    
    return render_template(
        'dashboard.html',
        user=user,
        datasets=datasets,
        total_rows=total_rows,
        total_size_bytes=total_size_bytes,
    )

@main_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    if not AuthService.is_authenticated():
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return render_template('upload.html')
        
        file = request.files['file']
        dataset_name = request.form.get('dataset_name')
        
        if file.filename == '':
            flash('No file selected', 'error')
            return render_template('upload.html')
        
        if not dataset_name:
            flash('Dataset name is required', 'error')
            return render_template('upload.html')
        
        user = AuthService.get_current_user()
        
        filename, file_path = DataService.save_file(file, current_app.config['UPLOAD_FOLDER'])
        
        if filename is None:
            flash('Invalid file format', 'error')
            return render_template('upload.html')
        
        df, error = DataService.read_file(file_path)
        
        if error:
            flash(f'Error reading file: {error}', 'error')
            os.remove(file_path)
            return render_template('upload.html')
        
        file_size = os.path.getsize(file_path)
        
        dataset = DataService.create_dataset(
            name=dataset_name,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            df=df,
            user_id=user.id
        )
        
        flash(f'Dataset "{dataset_name}" uploadé avec succès !', 'success')
        return redirect(url_for('main.view_dataset', dataset_id=dataset.id))
    
    return render_template('upload.html')

@main_bp.route('/dataset/<int:dataset_id>')
def view_dataset(dataset_id):
    if not AuthService.is_authenticated():
        return redirect(url_for('auth.login'))
    
    user = AuthService.get_current_user()
    dataset = DataService.get_dataset_by_id(dataset_id, user.id)
    
    if not dataset:
        flash('Dataset not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    df, error = DataService.read_file(dataset.file_path)
    
    if error:
        flash(f'Error reading dataset: {error}', 'error')
        return redirect(url_for('main.dashboard'))
    
    preview = DataService.get_preview(df)
    statistics = dataset.get_statistics()
    missing_values = dataset.get_missing_values()
    columns_info = dataset.get_columns_info()
    
    return render_template('dataset.html', 
                         dataset=dataset, 
                         preview=preview, 
                         statistics=statistics,
                         missing_values=missing_values,
                         columns_info=columns_info)

@main_bp.route('/dataset/<int:dataset_id>/delete', methods=['POST'])
def delete_dataset(dataset_id):
    if not AuthService.is_authenticated():
        return redirect(url_for('auth.login'))
    
    user = AuthService.get_current_user()
    dataset = DataService.get_dataset_by_id(dataset_id, user.id)
    
    if not dataset:
        flash('Dataset not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    try:
        os.remove(dataset.file_path)
    except:
        pass
    
    from models import db
    db.session.delete(dataset)
    db.session.commit()
    
    flash(f'Dataset "{dataset.name}" deleted successfully', 'success')
    return redirect(url_for('main.dashboard'))

@main_bp.route('/dataset/<int:dataset_id>/visualize')
def visualize_dataset(dataset_id):
    if not AuthService.is_authenticated():
        return redirect(url_for('auth.login'))
    
    user = AuthService.get_current_user()
    dataset = DataService.get_dataset_by_id(dataset_id, user.id)
    
    if not dataset:
        flash('Dataset not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    df, error = DataService.read_file(dataset.file_path)
    
    if error:
        flash(f'Error reading dataset: {error}', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get column information
    numeric_columns = VisualizationService.get_numeric_columns(df)
    categorical_columns = VisualizationService.get_categorical_columns(df)
    datetime_columns = VisualizationService.get_datetime_columns(df)
    
    # Generate suggested charts
    suggested_charts = VisualizationService.generate_suggested_charts(df)
    
    return render_template('visualize.html', 
                         dataset=dataset,
                         numeric_columns=numeric_columns,
                         categorical_columns=categorical_columns,
                         datetime_columns=datetime_columns,
                         suggested_charts=suggested_charts)

@main_bp.route('/dataset/<int:dataset_id>/chart_data')
def get_chart_data(dataset_id):
    if not AuthService.is_authenticated():
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = AuthService.get_current_user()
    dataset = DataService.get_dataset_by_id(dataset_id, user.id)
    
    if not dataset:
        return jsonify({'error': 'Dataset not found'}), 404
    
    df, error = DataService.read_file(dataset.file_path)
    
    if error:
        return jsonify({'error': error}), 500
    
    # Get chart configuration from request
    chart_type = request.args.get('type')
    x_column = request.args.get('x_column')
    y_column = request.args.get('y_column')
    column = request.args.get('column')
    bar_column = request.args.get('bar_column')
    line_column = request.args.get('line_column')
    
    chart_config = {'type': chart_type}
    
    if x_column:
        chart_config['x_column'] = x_column
    if y_column:
        chart_config['y_column'] = y_column
    if column:
        chart_config['column'] = column
    if bar_column:
        chart_config['bar_column'] = bar_column
    if line_column:
        chart_config['line_column'] = line_column
    
    try:
        chart_data = VisualizationService.convert_to_chart_data(df, chart_config)
        return jsonify(chart_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/dataset/<int:dataset_id>/analysis')
def analysis_dataset(dataset_id):
    if not AuthService.is_authenticated():
        return redirect(url_for('auth.login'))
    
    user = AuthService.get_current_user()
    dataset = DataService.get_dataset_by_id(dataset_id, user.id)
    
    if not dataset:
        flash('Dataset not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    df, error = DataService.read_file(dataset.file_path)
    
    if error:
        flash(f'Error reading dataset: {error}', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Perform analysis
    correlations = VisualizationService.analyze_correlations(df)
    numeric_columns = VisualizationService.get_numeric_columns(df)
    categorical_columns = VisualizationService.get_categorical_columns(df)
    all_columns = numeric_columns + categorical_columns
    
    # Detect outliers for numeric columns
    outliers = {}
    for col in numeric_columns[:5]:  # Limit to first 5 numeric columns
        outliers[col] = VisualizationService.detect_outliers(df, col)
    
    return render_template('analysis.html', 
                         dataset=dataset,
                         correlations=correlations,
                         outliers=outliers,
                         numeric_columns=numeric_columns,
                         categorical_columns=categorical_columns,
                         all_columns=all_columns)

@main_bp.route('/dataset/<int:dataset_id>/filter', methods=['POST'])
def filter_dataset(dataset_id):
    if not AuthService.is_authenticated():
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = AuthService.get_current_user()
    dataset = DataService.get_dataset_by_id(dataset_id, user.id)
    
    if not dataset:
        return jsonify({'error': 'Dataset not found'}), 404
    
    df, error = DataService.read_file(dataset.file_path)
    
    if error:
        return jsonify({'error': error}), 500
    
    # Get filters from request
    filters = request.get_json() or {}
    
    try:
        # Apply filters
        filtered_df = VisualizationService.filter_data(df, filters)
        
        # Return filtered data preview
        preview = DataService.get_preview(filtered_df, rows=100)  # More rows for filtered data
        
        return jsonify({
            'preview': preview,
            'total_rows': len(filtered_df),
            'filtered_rows': len(df) - len(filtered_df)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/dataset/<int:dataset_id>/auto_dashboard')
def auto_dashboard(dataset_id):
    if not AuthService.is_authenticated():
        return redirect(url_for('auth.login'))
    
    user = AuthService.get_current_user()
    dataset = DataService.get_dataset_by_id(dataset_id, user.id)
    
    if not dataset:
        flash('Dataset not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    df, error = DataService.read_file(dataset.file_path)
    
    if error:
        flash(f'Error reading dataset: {error}', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Generate automatic dashboard
    dashboard_config = DashboardService.generate_auto_dashboard(df, dataset_id)
    insights = DashboardService.generate_insights(df)
    
    return render_template('auto_dashboard.html', 
                         dataset=dataset,
                         dashboard=dashboard_config,
                         insights=insights)

@main_bp.route('/dataset/<int:dataset_id>/auto_chart_data')
def get_auto_chart_data(dataset_id):
    if not AuthService.is_authenticated():
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = AuthService.get_current_user()
    dataset = DataService.get_dataset_by_id(dataset_id, user.id)
    
    if not dataset:
        return jsonify({'error': 'Dataset not found'}), 404
    
    df, error = DataService.read_file(dataset.file_path)
    
    if error:
        return jsonify({'error': error}), 500
    
    chart_id = request.args.get('chart_id')
    
    if not chart_id:
        return jsonify({'error': 'Chart ID is required'}), 400
    
    # Generate dashboard config to find the chart
    dashboard_config = DashboardService.generate_auto_dashboard(df, dataset_id)
    
    # Find the specific chart
    chart = None
    for c in dashboard_config['charts']:
        if c['id'] == chart_id:
            chart = c
            break
    
    if not chart:
        return jsonify({'error': 'Chart not found'}), 404
    
    try:
        chart_data = DashboardService.get_chart_data(df, chart)
        return jsonify(chart_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/dataset/<int:dataset_id>/ai_insights')
def ai_insights(dataset_id):
    if not AuthService.is_authenticated():
        return redirect(url_for('auth.login'))
    
    user = AuthService.get_current_user()
    dataset = DataService.get_dataset_by_id(dataset_id, user.id)
    
    if not dataset:
        flash('Dataset not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    df, error = DataService.read_file(dataset.file_path)
    
    if error:
        flash(f'Error reading dataset: {error}', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Initialize AI service
    ai_service = AIService()
    
    # Generate AI insights
    overview = ai_service.analyze_dataset_overview(df, dataset.name)
    visualizations = ai_service.suggest_visualizations(df)
    cleaning_suggestions = ai_service.data_cleaning_suggestions(df)
    
    return render_template('ai_insights.html', 
                         dataset=dataset,
                         overview=overview,
                         visualizations=visualizations,
                         cleaning_suggestions=cleaning_suggestions,
                         ai_configured=ai_service.is_configured())

@main_bp.route('/dataset/<int:dataset_id>/ai_query', methods=['POST'])
def ai_query(dataset_id):
    if not AuthService.is_authenticated():
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = AuthService.get_current_user()
    dataset = DataService.get_dataset_by_id(dataset_id, user.id)
    
    if not dataset:
        return jsonify({'error': 'Dataset not found'}), 404
    
    df, error = DataService.read_file(dataset.file_path)
    
    if error:
        return jsonify({'error': error}), 500
    
    # Get question from request
    data = request.get_json()
    question = data.get('question', '')
    
    if not question:
        return jsonify({'error': 'Question is required'}), 400
    
    try:
        # Initialize AI service
        ai_service = AIService()
        
        # Get AI response
        response = ai_service.natural_language_query(df, question)
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/dataset/<int:dataset_id>/ai_report')
def ai_report(dataset_id):
    if not AuthService.is_authenticated():
        return redirect(url_for('auth.login'))
    
    user = AuthService.get_current_user()
    dataset = DataService.get_dataset_by_id(dataset_id, user.id)
    
    if not dataset:
        flash('Dataset not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    df, error = DataService.read_file(dataset.file_path)
    
    if error:
        flash(f'Error reading dataset: {error}', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get report type
    report_type = request.args.get('type', 'summary')
    if report_type not in ('summary', 'executive', 'quality'):
        report_type = 'summary'
    
    try:
        ai_service = AIService()
        report_markdown = ai_service.generate_report(df, report_type)
        report_html = markdown.markdown(
            report_markdown or '',
            extensions=['extra', 'nl2br', 'sane_lists'],
        )
        
        return render_template(
            'ai_report.html',
            dataset=dataset,
            report=report_html,
            report_type=report_type,
            ai_configured=ai_service.is_configured(),
            report_error=ai_service.last_error,
        )
        
    except Exception as e:
        flash(f'Error generating report: {e}', 'error')
        ai_service = AIService()
        return render_template(
            'ai_report.html',
            dataset=dataset,
            report='',
            report_type=report_type,
            ai_configured=ai_service.is_configured(),
            report_error=str(e),
        )

@main_bp.route('/dataset/<int:dataset_id>/regression')
def regression_analysis(dataset_id):
    if not AuthService.is_authenticated():
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = AuthService.get_current_user()
    dataset = DataService.get_dataset_by_id(dataset_id, user.id)
    
    if not dataset:
        return jsonify({'error': 'Dataset not found'}), 404
    
    df, error = DataService.read_file(dataset.file_path)
    
    if error:
        return jsonify({'error': error}), 500
    
    x_column = request.args.get('x_column')
    y_column = request.args.get('y_column')
    
    if not x_column or not y_column:
        return jsonify({'error': 'Both x_column and y_column are required'}), 400
    
    try:
        regression_result = VisualizationService.linear_regression(df, x_column, y_column)
        return jsonify(regression_result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# AI Assistant Routes
@main_bp.route('/api/ai-assistant/welcome')
def ai_assistant_welcome():
    """Get AI assistant welcome message"""
    if not AuthService.is_authenticated():
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = AuthService.get_current_user()
    assistant = DataLensAIAssistant()
    
    response = assistant.get_welcome_message(user.username)
    
    return jsonify({
        'message': response.message,
        'action_suggestions': response.action_suggestions,
        'insights': response.insights,
        'confidence': response.confidence,
        'is_configured': assistant.is_configured
    })

@main_bp.route('/api/ai-assistant/analyze/<int:dataset_id>')
def ai_assistant_analyze(dataset_id):
    """Get contextual AI analysis for dataset"""
    if not AuthService.is_authenticated():
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = AuthService.get_current_user()
    dataset = DataService.get_dataset_by_id(dataset_id, user.id)
    
    if not dataset:
        return jsonify({'error': 'Dataset not found'}), 404
    
    df, error = DataService.read_file(dataset.file_path)
    if error:
        return jsonify({'error': error}), 500
    
    view = request.args.get('view', 'overview')
    assistant = DataLensAIAssistant()
    
    response = assistant.analyze_dataset_context(df, dataset.name, view)
    
    return jsonify({
        'message': response.message,
        'action_suggestions': response.action_suggestions,
        'insights': response.insights,
        'confidence': response.confidence
    })

@main_bp.route('/api/ai-assistant/suggest-actions/<int:dataset_id>')
def ai_assistant_suggest(dataset_id):
    """Get AI suggestions for next actions"""
    if not AuthService.is_authenticated():
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = AuthService.get_current_user()
    dataset = DataService.get_dataset_by_id(dataset_id, user.id)
    
    if not dataset:
        return jsonify({'error': 'Dataset not found'}), 404
    
    df, error = DataService.read_file(dataset.file_path)
    if error:
        return jsonify({'error': error}), 500
    
    current_action = request.args.get('current_action')
    assistant = DataLensAIAssistant()
    
    response = assistant.suggest_next_actions(df, current_action)
    
    return jsonify({
        'message': response.message,
        'action_suggestions': response.action_suggestions,
        'insights': response.insights,
        'confidence': response.confidence
    })

@main_bp.route('/api/ai-assistant/ask', methods=['POST'])
def ai_assistant_ask():
    """Ask AI assistant a question"""
    if not AuthService.is_authenticated():
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    question = data.get('question', '')
    dataset_id = data.get('dataset_id')
    
    if not question:
        return jsonify({'error': 'Question is required'}), 400
    
    assistant = DataLensAIAssistant()
    
    # If dataset_id provided, add context
    context = {}
    if dataset_id:
        user = AuthService.get_current_user()
        dataset = DataService.get_dataset_by_id(dataset_id, user.id)
        if dataset:
            df, error = DataService.read_file(dataset.file_path)
            if not error:
                context['dataset'] = {
                    'name': dataset.name,
                    'shape': df.shape,
                    'columns': df.columns.tolist()
                }
    
    response = assistant.answer_general_question(question, context)
    
    return jsonify({
        'message': response.message,
        'action_suggestions': response.action_suggestions,
        'insights': response.insights,
        'confidence': response.confidence
    })

@main_bp.route('/dataset/<int:dataset_id>/auto-ai-analysis')
def auto_ai_analysis(dataset_id):
    """Automatic AI analysis page - triggered after upload"""
    if not AuthService.is_authenticated():
        return redirect(url_for('auth.login'))
    
    user = AuthService.get_current_user()
    dataset = DataService.get_dataset_by_id(dataset_id, user.id)
    
    if not dataset:
        flash('Dataset not found', 'error')
        return redirect(url_for('main.dashboard'))
    
    df, error = DataService.read_file(dataset.file_path)
    
    if error:
        flash(f'Error reading dataset: {error}', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Perform automatic AI analysis
    analyzer = AutoAIAnalyzer()
    report = analyzer.analyze_and_generate_report(df, dataset.filename, dataset.id)
    
    return render_template('auto_ai_report.html', 
                         dataset=dataset,
                         report=report,
                         ai_configured=analyzer.ai_assistant.is_configured)


@main_bp.route('/dataset/<int:dataset_id>/ai_report/pdf')
def ai_report_pdf(dataset_id):
    """Download AI report as PDF"""
    if not AuthService.is_authenticated():
        return jsonify({'error': 'Unauthorized'}), 401

    user = AuthService.get_current_user()
    dataset = DataService.get_dataset_by_id(dataset_id, user.id)
    if not dataset:
        return jsonify({'error': 'Dataset not found'}), 404

    df, error = DataService.read_file(dataset.file_path)
    if error:
        return jsonify({'error': error}), 500

    report_type = request.args.get('type', 'summary')
    if report_type not in ('summary', 'executive', 'quality'):
        report_type = 'summary'

    ai_service = AIService()
    report_text = ai_service.generate_report(df, report_type)

    title = f"AI Report - {dataset.name}"
    subtitle = f"{dataset.filename} • {dataset.rows_count} rows × {dataset.columns_count} columns • type={report_type}"
    pdf_bytes = PDFReportService.generate_pdf_bytes(
        title=title,
        subtitle=subtitle,
        content=report_text or "",
        content_is_html=False,
    )

    filename = PDFReportService._safe_filename(f"{dataset.name}_{report_type}_ai_report") + ".pdf"
    return send_file(
        BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename,
    )


@main_bp.route('/dataset/<int:dataset_id>/auto-ai-analysis/pdf')
def auto_ai_report_pdf(dataset_id):
    """Download auto AI analysis report as PDF"""
    if not AuthService.is_authenticated():
        return jsonify({'error': 'Unauthorized'}), 401

    user = AuthService.get_current_user()
    dataset = DataService.get_dataset_by_id(dataset_id, user.id)
    if not dataset:
        return jsonify({'error': 'Dataset not found'}), 404

    df, error = DataService.read_file(dataset.file_path)
    if error:
        return jsonify({'error': error}), 500

    analyzer = AutoAIAnalyzer()
    report = analyzer.analyze_and_generate_report(df, dataset.filename, dataset.id)

    title = f"Auto AI Analysis - {dataset.name}"
    subtitle = f"{dataset.filename} • {dataset.rows_count} rows × {dataset.columns_count} columns • type={report.report_type}"

    # Use the formatted HTML report but render it as text in PDF.
    pdf_bytes = PDFReportService.generate_pdf_bytes(
        title=title,
        subtitle=subtitle,
        content=report.formatted_report or "",
        content_is_html=True,
    )

    filename = PDFReportService._safe_filename(f"{dataset.name}_{report.report_type}_auto_ai_report") + ".pdf"
    return send_file(
        BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename,
    )


@main_bp.route('/dataset/<int:dataset_id>/auto-dashboard/code')
def auto_dashboard_code(dataset_id):
    """Download generated dashboard code (standalone HTML)"""
    if not AuthService.is_authenticated():
        return jsonify({'error': 'Unauthorized'}), 401

    user = AuthService.get_current_user()
    dataset = DataService.get_dataset_by_id(dataset_id, user.id)
    if not dataset:
        return jsonify({'error': 'Dataset not found'}), 404

    df, error = DataService.read_file(dataset.file_path)
    if error:
        return jsonify({'error': error}), 500

    dashboard = DashboardService.generate_auto_dashboard(df, dataset_id)
    html = DashboardCodeService.generate_chartjs_dashboard_html(
        dataset_id=dataset_id,
        dataset_name=dataset.name,
        charts=dashboard.get('charts', []),
    )

    filename = PDFReportService._safe_filename(f"{dataset.name}_auto_dashboard") + ".html"
    return send_file(
        BytesIO(html.encode('utf-8')),
        mimetype='text/html; charset=utf-8',
        as_attachment=True,
        download_name=filename,
    )
