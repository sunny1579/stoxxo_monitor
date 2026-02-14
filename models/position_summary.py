"""
Options Position Summary Model
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class OptionsPositionSummary:
    """Aggregated options position data for a user"""
    
    # User identification (required - no defaults)
    user_id: str
    user_alias: str
    
    # P&L (required - no defaults)
    live_pnl: float
    
    # Call positions (required - no defaults)
    call_sell_qty: int  # Negative value
    call_buy_qty: int   # Positive value
    
    # Put positions (required - no defaults)
    put_sell_qty: int   # Negative value
    put_buy_qty: int    # Positive value
    
    # Net positions (required - no defaults)
    puts_net: int       # Sum of put_sell + put_buy
    calls_net: int      # Sum of call_sell + call_buy
    
    # Status (required - no defaults)
    imparity_status: str  # 'green' or 'red'
    
    # Optional fields with defaults (must come after required fields)
    available_margin: float = 0.0
    utilized_margin: float = 0.0
    last_updated: Optional[datetime] = None
    
    @property
    def is_balanced(self) -> bool:
        """Check if positions are balanced"""
        return self.puts_net == 0 and self.calls_net == 0
    
    @property
    def total_positions(self) -> int:
        """Total number of positions"""
        return abs(self.call_sell_qty) + abs(self.call_buy_qty) + \
               abs(self.put_sell_qty) + abs(self.put_buy_qty)
    
    @property
    def roi_percent(self) -> float:
        """Calculate ROI percentage"""
        total_margin = self.available_margin + self.utilized_margin
        if total_margin > 0:
            return (self.live_pnl * 100) / total_margin
        return 0.0
    
    def __str__(self):
        return f"{self.user_alias}: P&L={self.live_pnl}, " \
               f"ROI={self.roi_percent:.2f}%, " \
               f"Calls={self.calls_net}, Puts={self.puts_net}"