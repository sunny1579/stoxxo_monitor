"""
Clear all Python cache files.....hare krishna
"""
import os
import shutil

# Find and delete all __pycache__ directories
def clear_cache(root_dir='.'):
    deleted = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if '__pycache__' in dirnames:
            cache_path = os.path.join(dirpath, '__pycache__')
            try:
                shutil.rmtree(cache_path)
                deleted.append(cache_path)
                print(f"Deleted: {cache_path}")
            except Exception as e:
                print(f"Error deleting {cache_path}: {e}")
        
        # Also delete .pyc files
        for filename in filenames:
            if filename.endswith('.pyc'):
                pyc_path = os.path.join(dirpath, filename)
                try:
                    os.remove(pyc_path)
                    deleted.append(pyc_path)
                    print(f"Deleted: {pyc_path}")
                except Exception as e:
                    print(f"Error deleting {pyc_path}: {e}")
    
    if deleted:
        print(f"\nDeleted {len(deleted)} cache files/folders")
        print("\nNow run: python main.py")
    else:
        print("No cache files found")

if __name__ == "__main__":
    print("Clearing Python cache...")
    print("=" * 60)
    clear_cache()
    