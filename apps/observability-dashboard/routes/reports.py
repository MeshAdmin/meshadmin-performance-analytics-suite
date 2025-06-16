from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, abort, send_file
from flask_login import login_required, current_user
import json
from datetime import datetime, timedelta
import os

from models import Report, ReportRun, User, Organization
from app import db, celery

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports')
@login_required
def index():
    """Show the reports dashboard"""
    # Get user's organizations
    org_ids = [org.id for org in current_user.organizations]
    
    # Get reports for the user and their organizations
    reports = Report.query.filter(
        (Report.user_id == current_user.id) | 
        (Report.organization_id.in_(org_ids))
    ).order_by(Report.updated_at.desc()).all()
    
    # Get scheduled reports
    scheduled_reports = Report.query.filter(
        ((Report.user_id == current_user.id) | 
        (Report.organization_id.in_(org_ids))) &
        (Report.schedule != None)
    ).all()
    
    # Get report runs for today
    today = datetime.utcnow().date()
    tomorrow = today + timedelta(days=1)
    report_runs = ReportRun.query.join(Report).filter(
        ((Report.user_id == current_user.id) | 
        (Report.organization_id.in_(org_ids))) &
        (ReportRun.started_at >= today) &
        (ReportRun.started_at < tomorrow)
    ).order_by(ReportRun.started_at.desc()).all()
    
    return render_template(
        'reports.html', 
        reports=reports,
        scheduled_reports=scheduled_reports,
        report_runs=report_runs,
        today=today.strftime('%Y-%m-%d')
    )

@reports_bp.route('/reports/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new report"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        query = request.form.get('query', '')
        format = request.form.get('format', 'pdf')
        organization_id = request.form.get('organization_id')
        
        # Create report
        report = Report(
            name=name,
            description=description,
            query=query,
            format=format,
            user_id=current_user.id,
            organization_id=organization_id if organization_id and organization_id != 'none' else None
        )
        
        # Process schedule if provided
        schedule_enabled = request.form.get('schedule_enabled') == 'on'
        if schedule_enabled:
            schedule_type = request.form.get('schedule_type')
            if schedule_type == 'custom':
                cron = request.form.get('schedule_cron')
                report.schedule = 'custom'
                report.cron = cron
            else:
                report.schedule = schedule_type  # hourly, daily, weekly, or monthly
                
            # Process recipients
            recipients = request.form.get('schedule_recipients', '')
            if recipients:
                report.recipients = [r.strip() for r in recipients.split(',')]
        
        # Process parameters
        parameters = []
        param_names = request.form.getlist('param_name[]')
        param_types = request.form.getlist('param_type[]')
        param_defaults = request.form.getlist('param_default[]')
        param_required = request.form.getlist('param_required[]')
        
        for i in range(len(param_names)):
            if param_names[i]:
                parameters.append({
                    'name': param_names[i],
                    'type': param_types[i],
                    'default': param_defaults[i],
                    'required': i in param_required
                })
        
        report.parameters = json.dumps(parameters)
        
        db.session.add(report)
        db.session.commit()
        
        flash('Report created successfully', 'success')
        return redirect(url_for('reports.edit', report_id=report.id))
    
    # GET request - show the report builder
    organizations = current_user.organizations
    return render_template('report_builder.html', report=None, organizations=organizations)

@reports_bp.route('/reports/builder/<int:report_id>')
@login_required
def edit(report_id):
    """Edit an existing report"""
    report = Report.query.get_or_404(report_id)
    
    # Check if user has access to this report
    org_ids = [org.id for org in current_user.organizations]
    if report.user_id != current_user.id and report.organization_id not in org_ids:
        abort(403)
    
    organizations = current_user.organizations
    return render_template('report_builder.html', report=report, organizations=organizations)

@reports_bp.route('/reports/run/<int:report_id>', methods=['GET', 'POST'])
@login_required
def run(report_id):
    """Run a report with parameters"""
    report = Report.query.get_or_404(report_id)
    
    # Check if user has access to this report
    org_ids = [org.id for org in current_user.organizations]
    if report.user_id != current_user.id and report.organization_id not in org_ids:
        abort(403)
    
    if request.method == 'POST':
        # Create a report run
        report_run = ReportRun(
            status='pending',
            report_id=report.id
        )
        db.session.add(report_run)
        db.session.commit()
        
        # Collect parameters
        parameters = {}
        for param in report.get_parameters():
            param_name = param['name']
            param_value = request.form.get(f'param_{param_name}', param['default'])
            parameters[param_name] = param_value
        
        # Store parameters used
        report_run.parameters_used = json.dumps(parameters)
        db.session.commit()
        
        # Queue report generation task
        celery.send_task('workers.run_report', args=[report_id, report_run.id, parameters])
        
        flash('Report generation started', 'info')
        return redirect(url_for('reports.view_run', run_id=report_run.id))
    
    # GET request - show parameter input form
    return render_template('report_run.html', report=report)

@reports_bp.route('/reports/run/<int:run_id>/view')
@login_required
def view_run(run_id):
    """View the results of a report run"""
    report_run = ReportRun.query.get_or_404(run_id)
    report = report_run.report
    
    # Check if user has access to this report
    org_ids = [org.id for org in current_user.organizations]
    if report.user_id != current_user.id and report.organization_id not in org_ids:
        abort(403)
    
    # If report is still running, show progress page
    if report_run.status in ['pending', 'running']:
        return render_template('report_progress.html', report=report, run=report_run)
    
    # If report is complete, show the result
    if report_run.status == 'completed' and report_run.file_path:
        # For PDF or HTML, we can display in the browser
        if report.format in ['pdf', 'html']:
            return render_template('report_view.html', report=report, run=report_run)
        else:
            # For other formats, redirect to download
            return redirect(url_for('reports.download', run_id=run_id))
    
    # If report failed, show error page
    return render_template('report_error.html', report=report, run=report_run)

@reports_bp.route('/reports/run/<int:run_id>/download')
@login_required
def download(run_id):
    """Download the report file"""
    report_run = ReportRun.query.get_or_404(run_id)
    report = report_run.report
    
    # Check if user has access to this report
    org_ids = [org.id for org in current_user.organizations]
    if report.user_id != current_user.id and report.organization_id not in org_ids:
        abort(403)
    
    if report_run.status != 'completed' or not report_run.file_path:
        flash('Report is not ready for download', 'error')
        return redirect(url_for('reports.view_run', run_id=run_id))
    
    if not os.path.exists(report_run.file_path):
        flash('Report file not found', 'error')
        return redirect(url_for('reports.view_run', run_id=run_id))
    
    # Determine mimetype based on format
    mimetypes = {
        'pdf': 'application/pdf',
        'csv': 'text/csv',
        'excel': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'html': 'text/html',
        'json': 'application/json'
    }
    
    filename = f"report_{report.name.replace(' ', '_')}_{report_run.started_at.strftime('%Y%m%d')}.{report.format}"
    
    return send_file(
        report_run.file_path, 
        mimetype=mimetypes.get(report.format, 'application/octet-stream'),
        as_attachment=True,
        download_name=filename
    )

@reports_bp.route('/api/reports/<int:report_id>/run', methods=['POST'])
@login_required
def api_run_report(report_id):
    """API endpoint to run a report"""
    report = Report.query.get_or_404(report_id)
    
    # Check if user has access to this report
    org_ids = [org.id for org in current_user.organizations]
    if report.user_id != current_user.id and report.organization_id not in org_ids:
        return jsonify({'error': 'Permission denied'}), 403
    
    # Create a report run
    report_run = ReportRun(
        status='pending',
        report_id=report.id
    )
    db.session.add(report_run)
    db.session.commit()
    
    # Get parameters from request (if any)
    parameters = request.json.get('parameters', {})
    
    # Store parameters used
    report_run.parameters_used = json.dumps(parameters)
    db.session.commit()
    
    # Queue report generation task
    celery.send_task('workers.run_report', args=[report_id, report_run.id, parameters])
    
    return jsonify({
        'status': 'success',
        'runId': report_run.id,
        'message': 'Report generation started'
    })

@reports_bp.route('/api/reports/save', methods=['POST'])
@login_required
def api_save_report():
    """API endpoint to save a report configuration"""
    data = request.json
    report_id = data.get('id')
    
    # Check if we're updating an existing report
    if report_id:
        report = Report.query.get(report_id)
        if not report:
            return jsonify({'error': 'Report not found'}), 404
        
        # Check if user has access to this report
        org_ids = [org.id for org in current_user.organizations]
        if report.user_id != current_user.id and report.organization_id not in org_ids:
            return jsonify({'error': 'Permission denied'}), 403
    else:
        # Create a new report
        report = Report(
            user_id=current_user.id
        )
        db.session.add(report)
    
    # Update report data
    report.name = data.get('name', 'Untitled Report')
    report.description = data.get('description', '')
    report.format = data.get('format', 'pdf')
    
    # Update organization if provided
    if 'organization_id' in data:
        report.organization_id = data['organization_id']
    
    # Update sections
    if 'sections' in data:
        report.sections = json.dumps(data['sections'])
    
    # Update parameters
    if 'parameters' in data:
        report.parameters = json.dumps(data['parameters'])
    
    # Update scheduling
    if 'schedule' in data:
        schedule = data['schedule']
        if schedule:
            report.schedule = schedule.get('type')
            report.recipients = schedule.get('recipients', [])
            
            if schedule.get('type') == 'custom':
                report.cron = schedule.get('cron')
        else:
            report.schedule = None
            report.cron = None
            report.recipients = []
    
    # Update format-specific options
    if 'options' in data:
        report.options = json.dumps(data['options'])
    
    report.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'id': report.id,
        'name': report.name,
        'status': 'saved'
    })

@reports_bp.route('/api/reports/<int:report_id>', methods=['DELETE'])
@login_required
def api_delete_report(report_id):
    """API endpoint to delete a report"""
    report = Report.query.get_or_404(report_id)
    
    # Check if user has access to delete this report
    if report.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'Permission denied'}), 403
    
    # Delete report runs first (and associated files)
    for run in report.report_runs:
        if run.file_path and os.path.exists(run.file_path):
            try:
                os.remove(run.file_path)
            except Exception as e:
                # Log but continue
                print(f"Error deleting report file {run.file_path}: {e}")
    
    # Delete report runs from database
    ReportRun.query.filter_by(report_id=report.id).delete()
    
    # Delete the report
    db.session.delete(report)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Report deleted successfully'
    })

@reports_bp.route('/api/reports/<int:report_id>/schedule', methods=['PUT'])
@login_required
def api_update_schedule(report_id):
    """API endpoint to update report schedule"""
    report = Report.query.get_or_404(report_id)
    
    # Check if user has access to update this report
    org_ids = [org.id for org in current_user.organizations]
    if report.user_id != current_user.id and report.organization_id not in org_ids:
        return jsonify({'error': 'Permission denied'}), 403
    
    data = request.json
    enabled = data.get('enabled', False)
    
    if enabled and not report.schedule:
        # Can't enable a schedule that doesn't exist
        return jsonify({'error': 'No schedule defined for this report'}), 400
    
    # Set enabled status by either setting or clearing the schedule
    if not enabled:
        # Store schedule temporarily
        temp_schedule = {
            'type': report.schedule,
            'cron': report.cron,
            'recipients': report.recipients
        }
        
        # Clear schedule
        report.schedule = None
        report.cron = None
        report.recipients = []
        
        # Store disabled schedule in options for later re-enabling
        report.options = json.dumps({
            'disabled_schedule': temp_schedule
        })
    else:
        # Re-enable previously disabled schedule
        options = json.loads(report.options) if report.options else {}
        disabled_schedule = options.get('disabled_schedule', {})
        
        report.schedule = disabled_schedule.get('type')
        report.cron = disabled_schedule.get('cron')
        report.recipients = disabled_schedule.get('recipients', [])
        
        # Remove disabled schedule from options
        options.pop('disabled_schedule', None)
        report.options = json.dumps(options) if options else None
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'enabled': enabled
    })

@reports_bp.route('/api/reports/runs/<int:run_id>', methods=['DELETE'])
@login_required
def api_delete_run(run_id):
    """API endpoint to delete a report run"""
    report_run = ReportRun.query.get_or_404(run_id)
    report = report_run.report
    
    # Check if user has access to delete this run
    org_ids = [org.id for org in current_user.organizations]
    if report.user_id != current_user.id and report.organization_id not in org_ids:
        return jsonify({'error': 'Permission denied'}), 403
    
    # Delete the file if it exists
    if report_run.file_path and os.path.exists(report_run.file_path):
        try:
            os.remove(report_run.file_path)
        except Exception as e:
            # Log but continue
            print(f"Error deleting report file {report_run.file_path}: {e}")
    
    # Delete the run
    db.session.delete(report_run)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Report run deleted successfully'
    })

@reports_bp.route('/api/reports/runs/<int:run_id>/error')
@login_required
def api_get_run_error(run_id):
    """API endpoint to get error details for a failed report run"""
    report_run = ReportRun.query.get_or_404(run_id)
    report = report_run.report
    
    # Check if user has access to view this run
    org_ids = [org.id for org in current_user.organizations]
    if report.user_id != current_user.id and report.organization_id not in org_ids:
        return jsonify({'error': 'Permission denied'}), 403
    
    if report_run.status != 'error' or not report_run.error_message:
        return jsonify({'error': 'This run did not fail or has no error message'}), 400
    
    return jsonify({
        'run_id': report_run.id,
        'report_id': report.id,
        'report_name': report.name,
        'date': report_run.started_at.strftime('%Y-%m-%d %H:%M:%S'),
        'error_message': report_run.error_message
    })

@reports_bp.route('/api/reports/<int:report_id>/export')
@login_required
def api_export_report(report_id):
    """API endpoint to export a report definition"""
    report = Report.query.get_or_404(report_id)
    
    # Check if user has access to this report
    org_ids = [org.id for org in current_user.organizations]
    if report.user_id != current_user.id and report.organization_id not in org_ids:
        return jsonify({'error': 'Permission denied'}), 403
    
    format = request.args.get('format', 'json')
    
    # Create report definition
    definition = {
        'name': report.name,
        'description': report.description,
        'format': report.format,
        'sections': json.loads(report.sections) if report.sections else [],
        'parameters': json.loads(report.parameters) if report.parameters else [],
        'schedule': {
            'type': report.schedule,
            'cron': report.cron,
            'recipients': report.recipients
        } if report.schedule else None,
        'options': json.loads(report.options) if report.options else {}
    }
    
    if format == 'json':
        return jsonify(definition)
    else:
        # Handle other formats if needed
        return jsonify({'error': 'Unsupported export format'}), 400
