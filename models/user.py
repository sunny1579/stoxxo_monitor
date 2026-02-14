"""
User Data Model
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """User information"""
    user_id: str
    display_name: str
    is_active: bool = True
    logged_in: bool = False
    
    # Financial data
    live_pnl: float = 0.0
    available_margin: float = 0.0
    utilized_margin: float = 0.0
    
    # Metadata
    last_sync: Optional[datetime] = None
    broker: str = ""
    
    def __str__(self):
        return f"{self.display_name} ({self.user_id})"