# backend/apps/communications/whatsapp_service.py
from twilio.rest import Client
import json

class WhatsAppService:
    def __init__(self):
        self.client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )
        
    def send_update(self, user, message_type, data):
        """Send WhatsApp updates to users"""
        templates = {
            'application_sent': "🚀 CostByte Alert: Applied for {position} at {company}. Good luck!",
            'daily_summary': "📊 Daily Report: {applied} applications sent, {matches} new matches",
            'payment_success': "✅ Payment successful! AI job hunting activated.",
            'profile_update': "🔔 Profile updated. AI recalibrating job matches..."
        }
        
        message = templates[message_type].format(**data)
        
        self.client.messages.create(
            body=message,
            from_='whatsapp:+14155238886',
            to=f'whatsapp:{user.phone_number}'
        )
