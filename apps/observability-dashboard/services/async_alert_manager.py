import logging
import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import threading

logger = logging.getLogger(__name__)

class AsyncAlertManager:
    """Async version of AlertManager for improved performance"""
    
    def __init__(self):
        self.running = False
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def start(self):
        """Start the async alert manager service"""
        logger.info("Starting async alert manager service...")
        self.running = True
        
        # Create aiohttp session for HTTP requests
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        
        # Start the alert checking loop
        asyncio.create_task(self._check_alert_rules_loop())
        logger.info("Async alert manager service started")
    
    async def _check_alert_rules_loop(self):
        """Main loop for checking alert rules"""
        while self.running:
            try:
                await self.check_alert_rules()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in async alert manager: {e}")
                await asyncio.sleep(60)
    
    async def check_alert_rules(self):
        """Check all active alert rules concurrently"""
        try:
            from app import db
            from models import AlertRule, Alert
            
            # Get all enabled alert rules
            rules = AlertRule.query.filter_by(enabled=True).all()
            
            # Process rules concurrently
            tasks = []
            for rule in rules:
                # Skip rules that are in cooldown
                last_alert = Alert.query.filter_by(
                    alert_rule_id=rule.id, resolved=False
                ).order_by(Alert.timestamp.desc()).first()
                
                if last_alert and (datetime.utcnow() - last_alert.timestamp).total_seconds() < (rule.cooldown_minutes * 60):
                    continue
                
                tasks.append(self._process_rule(rule))
            
            # Execute all rule checks concurrently
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                
        except Exception as e:
            logger.error(f"Error checking alert rules: {e}")
    
    async def send_slack_notification(self, webhook_url: str, payload: dict, alert_id: int):
        """Send a Slack notification asynchronously"""
        try:
            async with self.session.post(webhook_url, json=payload) as response:
                if response.status != 200:
                    response_text = await response.text()
                    logger.warning(f"Slack API returned error: {response.status}, {response_text}")
                else:
                    logger.info(f"Slack notification sent for alert {alert_id}")
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
    
    async def send_pagerduty_notification(self, payload: dict, alert_id: int):
        """Send a PagerDuty notification asynchronously"""
        try:
            headers = {"Content-Type": "application/json"}
            async with self.session.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=payload,
                headers=headers
            ) as response:
                if response.status != 202:
                    response_text = await response.text()
                    logger.warning(f"PagerDuty API returned error: {response.status}, {response_text}")
                else:
                    logger.info(f"PagerDuty notification sent for alert {alert_id}")
        except Exception as e:
            logger.error(f"Error sending PagerDuty notification: {e}")

# Global instance for use in the application
async_alert_manager = AsyncAlertManager()
