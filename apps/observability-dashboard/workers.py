from app import celery, app
from datetime import datetime, timedelta
from models import Log, Metric, Alert, ReportRun, Report, AlertRule
from services.report_generator import generate_report
from services.alert_manager import check_alert_rule
import logging
import json
import os

logger = logging.getLogger(__name__)

# Task to clean old logs based on retention policy
@celery.task
def cleanup_old_data():
    with app.app_context():
        # Calculate retention date
        retention_days = app.config['DATA_RETENTION_DAYS']
        retention_date = datetime.utcnow() - timedelta(days=retention_days)
        
        logger.info(f"Cleaning up data older than {retention_date}")
        
        try:
            # Clean up old logs
            deleted_logs = Log.query.filter(Log.timestamp < retention_date).delete()
            
            # Clean up old metrics
            deleted_metrics = Metric.query.filter(Metric.timestamp < retention_date).delete()
            
            # Clean up old resolved alerts
            deleted_alerts = Alert.query.filter(
                Alert.resolved == True,
                Alert.resolved_at < retention_date
            ).delete()
            
            # Clean up old report runs
            old_report_runs = ReportRun.query.filter(
                ReportRun.completed_at < retention_date
            ).all()
            
            # Delete report files first
            for report_run in old_report_runs:
                if report_run.file_path and os.path.exists(report_run.file_path):
                    try:
                        os.remove(report_run.file_path)
                    except Exception as e:
                        logger.error(f"Error deleting report file {report_run.file_path}: {e}")
            
            # Delete report run records
            deleted_reports = ReportRun.query.filter(
                ReportRun.completed_at < retention_date
            ).delete()
            
            from app import db
            db.session.commit()
            
            logger.info(f"Cleanup completed: Deleted {deleted_logs} logs, {deleted_metrics} metrics, {deleted_alerts} alerts, and {deleted_reports} report runs")
            
        except Exception as e:
            logger.error(f"Error during data cleanup: {e}")
            from app import db
            db.session.rollback()

# Task to run scheduled reports
@celery.task
def run_scheduled_reports():
    with app.app_context():
        now = datetime.utcnow()
        logger.info(f"Checking for reports to run at {now}")
        
        # Get all scheduled reports
        reports = Report.query.filter(Report.schedule.isnot(None)).all()
        
        for report in reports:
            try:
                # Basic schedule check - in a real implementation, use a cron parser
                should_run = False
                
                if report.schedule == 'hourly':
                    should_run = now.minute == 0
                elif report.schedule == 'daily':
                    should_run = now.hour == 0 and now.minute == 0
                elif report.schedule == 'weekly':
                    should_run = now.weekday() == 0 and now.hour == 0 and now.minute == 0
                elif report.schedule == 'monthly':
                    should_run = now.day == 1 and now.hour == 0 and now.minute == 0
                
                if should_run:
                    logger.info(f"Scheduling report {report.id}: {report.name}")
                    run_report.delay(report.id)
                
            except Exception as e:
                logger.error(f"Error checking report {report.id}: {e}")

# Task to run a specific report
@celery.task
def run_report(report_id):
    with app.app_context():
        try:
            report = Report.query.get(report_id)
            if not report:
                logger.error(f"Report {report_id} not found")
                return
            
            logger.info(f"Running report {report_id}: {report.name}")
            
            # Create report run record
            from app import db
            report_run = ReportRun(
                status='running',
                report_id=report.id,
                parameters_used=report.parameters
            )
            db.session.add(report_run)
            db.session.commit()
            
            # Generate the report
            try:
                file_path = generate_report(report, report_run.id)
                report_run.file_path = file_path
                report_run.status = 'completed'
                report_run.completed_at = datetime.utcnow()
            except Exception as e:
                logger.error(f"Error generating report {report_id}: {e}")
                report_run.status = 'error'
                report_run.error_message = str(e)
                report_run.completed_at = datetime.utcnow()
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error in run_report task for report {report_id}: {e}")

# Task to check alert rules against collected data
@celery.task
def check_alert_rules():
    with app.app_context():
        logger.info("Checking alert rules")
        
        # Get all enabled alert rules
        rules = AlertRule.query.filter_by(enabled=True).all()
        
        for rule in rules:
            try:
                logger.debug(f"Checking rule {rule.id}: {rule.name}")
                check_alert_rule(rule)
            except Exception as e:
                logger.error(f"Error checking alert rule {rule.id}: {e}")

# Task to send an alert notification
@celery.task
def send_alert_notification(alert_id, channels):
    with app.app_context():
        from models import Alert
        from services.alert_manager import send_notification
        
        alert = Alert.query.get(alert_id)
        if not alert:
            logger.error(f"Alert {alert_id} not found")
            return
        
        logger.info(f"Sending alert {alert_id} notifications via {channels}")
        
        for channel in channels:
            try:
                send_notification(alert, channel)
            except Exception as e:
                logger.error(f"Error sending alert {alert_id} notification via {channel}: {e}")
