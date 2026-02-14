"""
User Manager Service
Manages user list from Stoxxo
"""
import logging
from datetime import datetime
from typing import List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.user import User


class UserManager:
    """
    Manages users directly from Stoxxo bridge
    No local configuration needed
    """
    
    def __init__(self, stoxxo_client):
        self.client = stoxxo_client
        self.logger = logging.getLogger(__name__)
        self._cached_users = []
        self._last_refresh = None
    
    def get_all_users(self):
        """
        Get all active users from Stoxxo
        
        Returns:
            List of User objects
        """
        try:
            users_data = self.client.system_info.get_users()
            
            users = []
            for data in users_data:
                # Only include enabled and logged-in users
                if data['enabled'] and data['logged_in']:
                    user = User(
                        user_id=data['user_id'],
                        display_name=data['user_alias'] or data['user_id'] or 'Default',
                        is_active=True,
                        logged_in=True,
                        live_pnl=data['mtm'],
                        available_margin=data['available_margin'],
                        utilized_margin=data['utilized_margin'],
                        last_sync=datetime.now(),
                        broker=data['broker']
                    )
                    users.append(user)
            
            # Cache users
            self._cached_users = users
            self._last_refresh = datetime.now()
            
            return users
            
        except Exception as e:
            self.logger.error("Error fetching users: %s", e)
            # Return cached users if available
            return self._cached_users
    
    def refresh_users(self):
        """
        Refresh user list from Stoxxo
        
        Returns:
            List of User objects
        """
        return self.get_all_users()
    
    def get_user_by_id(self, user_id):
        """
        Get specific user by ID
        
        Args:
            user_id: User ID to find
            
        Returns:
            User object or None
        """
        users = self.get_all_users()
        for user in users:
            if user.user_id == user_id:
                return user
        return None
    
    def get_user_count(self):
        """
        Get count of active users
        
        Returns:
            Number of active users
        """
        return len(self._cached_users)


if __name__ == "__main__":
    # Test the user manager
    from core.stoxxo_client import StoxxoClient
    
    print("Testing User Manager")
    print("=" * 50)
    
    try:
        client = StoxxoClient()
        
        if client.status.ping():
            print("Connected to Stoxxo Bridge\n")
            
            manager = UserManager(client)
            
            # Get all users
            users = manager.get_all_users()
            
            print("Found %d user(s):\n" % len(users))
            
            for user in users:
                print("  %s" % user.display_name)
                print("    User ID: %s" % user.user_id)
                print("    P&L: %.2f" % user.live_pnl)
                print("    Margin: %.2f" % user.available_margin)
                print("    Broker: %s" % user.broker)
                print()
        else:
            print("Cannot connect to Stoxxo Bridge")
            
    except Exception as e:
        print("Error: %s" % e)