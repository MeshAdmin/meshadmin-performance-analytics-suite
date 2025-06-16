from app import app, db
from models import Dashboard, Widget, DataSourceType
import json
from datetime import datetime, timedelta

with app.app_context():
    print("Creating default widgets for Dashboard ID 1")
    
    # First check if widgets already exist
    existing_widgets = Widget.query.filter_by(dashboard_id=1).all()
    if existing_widgets:
        print(f"Found {len(existing_widgets)} existing widgets, skipping creation")
    else:
        # Create default widgets for Dashboard 1
        widgets = [
            {
                'name': 'System Overview',
                'widget_type': 'stat',
                'data_source': DataSourceType.SYSLOG,
                'configuration': json.dumps({}),
                'position_x': 0,
                'position_y': 0,
                'width': 2,
                'height': 1,
                'dashboard_id': 1
            },
            {
                'name': 'Log Volume',
                'widget_type': 'line-chart',
                'data_source': DataSourceType.SYSLOG,
                'configuration': json.dumps({
                    'metric': 'count',
                    'group_by': 'hour'
                }),
                'position_x': 0,
                'position_y': 1,
                'width': 2,
                'height': 1,
                'dashboard_id': 1
            },
            {
                'name': 'Recent Alerts',
                'widget_type': 'alert-list',
                'data_source': DataSourceType.SYSLOG,
                'configuration': json.dumps({
                    'limit': 10,
                    'severity': ['ERROR', 'CRITICAL']
                }),
                'position_x': 2,
                'position_y': 0,
                'width': 1,
                'height': 2,
                'dashboard_id': 1
            }
        ]
        
        for widget_data in widgets:
            widget = Widget(**widget_data)
            db.session.add(widget)
        
        db.session.commit()
        print(f"Created {len(widgets)} widgets for Dashboard ID 1")