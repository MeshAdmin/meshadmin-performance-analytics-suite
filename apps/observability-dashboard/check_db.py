from app import app, db
from models import Dashboard, Widget, User, Organization

with app.app_context():
    print("Dashboards:")
    dashboards = Dashboard.query.all()
    for d in dashboards:
        print(f"  - ID: {d.id}, Name: {d.name}, User ID: {d.user_id}")
    
    print("\nWidgets:")
    widgets = Widget.query.all()
    for w in widgets:
        print(f"  - ID: {w.id}, Name: {w.name}, Dashboard ID: {w.dashboard_id}, Type: {w.widget_type}")
    
    print("\nUsers:")
    users = User.query.all()
    for u in users:
        print(f"  - ID: {u.id}, Username: {u.username}, Email: {u.email}")
    
    print("\nOrganizations:")
    orgs = Organization.query.all()
    for o in orgs:
        print(f"  - ID: {o.id}, Name: {o.name}")