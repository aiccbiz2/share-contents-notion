import sys
import os

# Add current directory to sys.path so we can import app
sys.path.append(os.getcwd())

try:
    from app.config import settings
    print(f"Loaded NOTION_PARENT_PAGE_ID: {settings.NOTION_PARENT_PAGE_ID}")
    
    expected_id = "290b59220286805b9545f8d28ce92539"
    
    if settings.NOTION_PARENT_PAGE_ID == expected_id:
        print("SUCCESS: ID matches the one provided.")
    else:
        print(f"FAILURE: ID does not match. Expected {expected_id}, got {settings.NOTION_PARENT_PAGE_ID}")

    # Check other keys
    if not settings.OPENAI_API_KEY:
        print("WARNING: OPENAI_API_KEY is not set.")
    if not settings.NOTION_API_KEY:
        print("WARNING: NOTION_API_KEY is not set.")

except ImportError as e:
    print(f"ImportError: {e}")
    print("It seems 'pydantic-settings' or other dependencies are missing.")
    print("Please run: pip install -r requirements.txt")
except Exception as e:
    print(f"Error loading settings: {e}")
