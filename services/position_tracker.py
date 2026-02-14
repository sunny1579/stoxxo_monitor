"""
Position Tracker Service
Aggregates options positions for users
"""
import logging
from datetime import datetime
from typing import List
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.position_summary import OptionsPositionSummary


class OptionsPositionTracker:
    """
    Tracks and aggregates options positions for all users
    Uses Stoxxo's /Positions endpoint
    """
    
    def __init__(self, stoxxo_client):
        self.client = stoxxo_client
        self.logger = logging.getLogger(__name__)
    
    def get_user_summary(self, user_id=""):
        """
        Get aggregated options positions for a user
        
        Args:
            user_id: User ID (empty string for default user)
            
        Returns:
            OptionsPositionSummary object
        """
        try:
            # Get all positions for user
            positions = self.client.system_info.get_positions(user_id)
            
            # Get user details
            user_data = self.client.system_info.get_users(user_id)
            user_info = user_data[0] if user_data else {}
            
            # Aggregate positions
            call_sell_qty = 0
            call_buy_qty = 0
            put_sell_qty = 0
            put_buy_qty = 0
            
            for pos in positions:
                symbol = pos['symbol'].upper()
                net_qty = pos['net_qty']
                
                # Skip closed positions (net_qty = 0)
                if net_qty == 0:
                    continue
                
                # Check if option (has CE or PE)
                is_call = 'CE' in symbol
                is_put = 'PE' in symbol
                
                if not (is_call or is_put):
                    continue  # Skip non-options (equity)
                
                # Determine if position is long or short based on net_qty
                if is_call:
                    if net_qty > 0:
                        # Long call (bought)
                        call_buy_qty += net_qty
                    else:
                        # Short call (sold)
                        call_sell_qty += net_qty  # net_qty is already negative
                elif is_put:
                    if net_qty > 0:
                        # Long put (bought)
                        put_buy_qty += net_qty
                    else:
                        # Short put (sold)
                        put_sell_qty += net_qty  # net_qty is already negative
            
            # Calculate net positions
            puts_net = put_sell_qty + put_buy_qty
            calls_net = call_sell_qty + call_buy_qty
            
            # Determine imparity status
            imparity = 'green' if (puts_net == 0 and calls_net == 0) else 'red'
            
            # Create summary
            return OptionsPositionSummary(
                user_id=user_id,
                user_alias=user_info.get('user_alias', user_id or 'Default'),
                live_pnl=user_info.get('mtm', 0.0),
                available_margin=user_info.get('available_margin', 0.0),
                utilized_margin=user_info.get('utilized_margin', 0.0),
                call_sell_qty=call_sell_qty,
                call_buy_qty=call_buy_qty,
                put_sell_qty=put_sell_qty,
                put_buy_qty=put_buy_qty,
                puts_net=puts_net,
                calls_net=calls_net,
                imparity_status=imparity,
                last_updated=datetime.now()
            )
            
        except Exception as e:
            self.logger.error("Error getting user summary for %s: %s", user_id, e)
            # Return empty summary on error
            return OptionsPositionSummary(
                user_id=user_id,
                user_alias=user_id or 'Default',
                live_pnl=0.0,
                available_margin=0.0,
                utilized_margin=0.0,
                call_sell_qty=0,
                call_buy_qty=0,
                put_sell_qty=0,
                put_buy_qty=0,
                puts_net=0,
                calls_net=0,
                imparity_status='green',
                last_updated=datetime.now()
            )
    
    def get_all_users_summary(self):
        """
        Get summary for all active users
        
        Returns:
            List of OptionsPositionSummary objects
        """
        try:
            # Get all users from Stoxxo
            users = self.client.system_info.get_users()
            
            summaries = []
            for user in users:
                # Only process enabled and logged-in users
                if user['enabled'] and user['logged_in']:
                    user_id = user['user_id']
                    summary = self.get_user_summary(user_id)
                    summaries.append(summary)
            
            return summaries
            
        except Exception as e:
            self.logger.error("Error getting all users summary: %s", e)
            return []
    
    def is_option_symbol(self, symbol):
        """
        Check if symbol is an option
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Tuple (is_option, is_call, is_put)
        """
        symbol_upper = symbol.upper()
        is_call = 'CE' in symbol_upper
        is_put = 'PE' in symbol_upper
        is_option = is_call or is_put
        
        return (is_option, is_call, is_put)


if __name__ == "__main__":
    # Test the tracker
    from core.stoxxo_client import StoxxoClient
    
    print("Testing Options Position Tracker")
    print("=" * 50)
    
    try:
        client = StoxxoClient()
        
        if client.status.ping():
            print("Connected to Stoxxo Bridge")
            
            tracker = OptionsPositionTracker(client)
            
            # Get all users summary
            print("\nFetching all users...")
            summaries = tracker.get_all_users_summary()
            
            print("Found %d user(s)\n" % len(summaries))
            
            for summary in summaries:
                print("User: %s" % summary.user_alias)
                print("  P&L: %.2f" % summary.live_pnl)
                print("  Call Sell: %d | Call Buy: %d | Net: %d" % (
                    summary.call_sell_qty, summary.call_buy_qty, summary.calls_net))
                print("  Put Sell: %d | Put Buy: %d | Net: %d" % (
                    summary.put_sell_qty, summary.put_buy_qty, summary.puts_net))
                print("  Status: %s" % summary.imparity_status)
                print()
        else:
            print("Cannot connect to Stoxxo Bridge")
            
    except Exception as e:
        print("Error: %s" % e)