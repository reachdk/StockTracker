"""
Email service for sending stock alerts
"""
import requests
from typing import Optional
import logging
from config import EmailConfig


class EmailService:
    """Email service using Elastic Email API"""
    
    def __init__(self, config: EmailConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
    
    def send_notification(self, subject: str, message: str) -> bool:
        """Send email notification"""
        try:
            # Prepare email data
            email_data = {
                'apikey': self.config.api_key,
                'subject': subject,
                'from': self.config.sender_email,
                'fromName': self.config.sender_name,
                'to': ','.join(self.config.recipient_emails),
                'bodyText': message,
                'bodyHtml': self._format_html_message(message),
                'isTransactional': True
            }
            
            # Send email
            response = requests.post(
                f"{self.config.api_uri}/email/send",
                data=email_data,
                timeout=30
            )
            
            # Check response
            if response.status_code == 200:
                result = response.json()
                if result.get('success', False):
                    self.logger.info(f"Email sent successfully to {len(self.config.recipient_emails)} recipients")
                    return True
                else:
                    error_msg = result.get('error', 'Unknown error')
                    self.logger.error(f"Email API error: {error_msg}")
                    return False
            else:
                self.logger.error(f"HTTP error {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            self.logger.error("Email request timed out")
            return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Email request failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending email: {e}")
            return False
    
    def _format_html_message(self, text_message: str) -> str:
        """Convert text message to HTML format"""
        html_message = text_message.replace('\n', '<br>')
        
        # Add some basic styling
        html_template = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #d32f2f;">Stock Portfolio Alert</h2>
            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px;">
                <pre style="white-space: pre-wrap; font-family: monospace;">{html_message}</pre>
            </div>
            <hr style="margin: 20px 0;">
            <p style="font-size: 12px; color: #666;">
                This is an automated message from your Stock Tracker system.
            </p>
        </body>
        </html>
        """
        
        return html_template