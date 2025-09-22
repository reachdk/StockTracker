"""
Configuration management for Stock Tracker
"""
import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class EmailConfig:
    """Email configuration settings"""
    api_key: str
    sender_email: str
    sender_name: str
    recipient_emails: List[str]
    api_uri: str = "https://api.elasticemail.com/v2"


@dataclass
class TrackerConfig:
    """Stock tracker configuration settings"""
    data_dir: str = "data"
    input_dir: str = "data/input"
    investments_file: str = "data/yfin_investments.csv"
    data_file: str = "data/yfin_data.csv"
    lookback_days: int = 5
    stagnation_threshold_days: int = 45
    default_tolerance: float = 15.0


class Config:
    """Main configuration class"""
    
    def __init__(self):
        self.email = EmailConfig(
            api_key=os.getenv("ELASTIC_EMAIL_API_KEY", ""),
            sender_email=os.getenv("SENDER_EMAIL", ""),
            sender_name=os.getenv("SENDER_NAME", "Stock Tracker"),
            recipient_emails=os.getenv("RECIPIENT_EMAILS", "").split(",")
        )
        
        self.tracker = TrackerConfig(
            data_dir=os.getenv("DATA_DIR", "data"),
            input_dir=os.getenv("INPUT_DIR", "data/input"),
            investments_file=os.getenv("INVESTMENTS_FILE", "data/yfin_investments.csv"),
            data_file=os.getenv("DATA_FILE", "data/yfin_data.csv"),
            lookback_days=int(os.getenv("LOOKBACK_DAYS", "5")),
            stagnation_threshold_days=int(os.getenv("STAGNATION_THRESHOLD", "45")),
            default_tolerance=float(os.getenv("DEFAULT_TOLERANCE", "15.0"))
        )
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        if not self.email.api_key:
            errors.append("ELASTIC_EMAIL_API_KEY environment variable is required")
        
        if not self.email.sender_email:
            errors.append("SENDER_EMAIL environment variable is required")
        
        if not self.email.recipient_emails or not self.email.recipient_emails[0]:
            errors.append("RECIPIENT_EMAILS environment variable is required")
        
        return errors