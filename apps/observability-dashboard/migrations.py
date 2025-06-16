import json
from app import db, app
from sqlalchemy import text
from models import Organization

def add_settings_column():
    """Add settings column to Organization table if it doesn't exist"""
    with app.app_context():
        # Check if the column already exists
        try:
            # Try to query the column
            Organization.query.with_entities(Organization.settings).limit(1).all()
            print("Settings column already exists")
            return
        except Exception as e:
            # Column doesn't exist, add it
            print("Adding settings column to Organization table...")
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE organization ADD COLUMN IF NOT EXISTS settings TEXT DEFAULT '{}'"))
                conn.commit()
            print("Settings column added successfully")
            return

if __name__ == "__main__":
    add_settings_column()