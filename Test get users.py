"""
Quick test — run this while Stoxxo Bridge is running.
Prints the raw API response AND the parsed dict for every user.

Usage: python test_get_users.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.stoxxo_client import StoxxoClient

client = StoxxoClient()

if not client.status.ping():
    print("ERROR: Stoxxo Bridge not reachable. Make sure it's running.")
    sys.exit(1)

print("Connected to Stoxxo Bridge\n")

# Raw response
raw = client.request("Users", {})
print("=" * 60)
print("RAW RESPONSE:")
print("=" * 60)
print(raw)
print()

# Parsed dicts
users = client.system_info.get_users()
print("=" * 60)
print(f"PARSED — {len(users)} user(s):")
print("=" * 60)
for u in users:
    print(f"\n--- {u['user_alias']} ({u['user_id']}) ---")
    for key, val in u.items():
        print(f"  {key:<25} {val}")