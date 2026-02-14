"""
Test Settings Manager
Quick test to verify settings are saving and loading correctly
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.settings_manager import SettingsManager

print("Testing Settings Manager")
print("=" * 60)

# Create settings manager
manager = SettingsManager()

print("\n1. Testing Font Size:")
print("   Current font size: %d" % manager.get_font_size())

print("\n2. Saving font size = 17...")
manager.save_font_size(17)

print("\n3. Reading back font size...")
saved = manager.get_font_size()
print("   Saved font size: %d" % saved)

if saved == 17:
    print("   [OK] Font size save/load WORKS!")
else:
    print("   [FAIL] Font size save/load FAILED! Expected 17, got %d" % saved)

print("\n4. Testing Polling Interval:")
print("   Current interval: %.1f" % manager.get_polling_interval())

print("\n5. Saving interval = 2.0...")
manager.save_polling_interval(2.0)

print("\n6. Reading back interval...")
saved_interval = manager.get_polling_interval()
print("   Saved interval: %.1f" % saved_interval)

if saved_interval == 2.0:
    print("   [OK] Interval save/load WORKS!")
else:
    print("   [FAIL] Interval save/load FAILED! Expected 2.0, got %.1f" % saved_interval)

print("\n7. Testing P&L Hidden:")
print("   Current P&L hidden: %s" % manager.get_pnl_hidden())

print("\n8. Saving P&L hidden = True...")
manager.save_pnl_hidden(True)

print("\n9. Reading back P&L hidden...")
saved_pnl = manager.get_pnl_hidden()
print("   Saved P&L hidden: %s" % saved_pnl)

if saved_pnl == True:
    print("   [OK] P&L hidden save/load WORKS!")
else:
    print("   [FAIL] P&L hidden save/load FAILED! Expected True, got %s" % saved_pnl)

print("\n10. Checking all saved keys:")
all_keys = manager.settings.allKeys()
print("    Found %d saved settings:" % len(all_keys))
for key in all_keys:
    value = manager.settings.value(key)
    print("    - %s = %s" % (key, value))

print("\n" + "=" * 60)
print("Test Complete!")
print("\nIf all tests passed, settings are working correctly.")
print("If any failed, there may be an issue with QSettings on your system.")