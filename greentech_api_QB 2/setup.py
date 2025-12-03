#!/usr/bin/env python3
"""
GreenTech Painting - Easy Setup Script
Guides you through the complete setup process step by step.
"""
import os
import sys
import pathlib
from dotenv import load_dotenv

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")

def print_step(number, title):
    """Print a step header"""
    print(f"\n{'─' * 70}")
    print(f"STEP {number}: {title}")
    print(f"{'─' * 70}\n")

def check_python_version():
    """Check if Python version is adequate"""
    print_step(1, "Checking Python Version")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
    return True

def check_dependencies():
    """Check if dependencies are installed"""
    print_step(2, "Checking Dependencies")
    
    required = ['requests', 'flask', 'flask_cors', 'dotenv']
    missing = []
    
    for module in required:
        try:
            if module == 'dotenv':
                __import__('dotenv')
            elif module == 'flask_cors':
                __import__('flask_cors')
            else:
                __import__(module)
            print(f"✅ {module} - Installed")
        except ImportError:
            print(f"❌ {module} - Missing")
            missing.append(module)
    
    if missing:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing)}")
        print("\nTo install, run:")
        print("  pip install -r requirements_txt.txt")
        print("\nOr install manually:")
        print(f"  pip install {' '.join(missing)}")
        return False
    
    return True

def check_env_file():
    """Check if .env file exists and is configured"""
    print_step(3, "Checking Configuration")
    
    env_path = pathlib.Path(".env")
    
    if not env_path.exists():
        print("❌ .env file not found")
        print("\nCreating .env file template...")
        
        template = """# QuickBooks API Credentials
# Get these from: https://developer.intuit.com

QBO_CLIENT_ID=
QBO_CLIENT_SECRET=

# These will be filled after OAuth setup
QBO_REFRESH_TOKEN=
QBO_REALM_ID=

# Mode: 'sandbox' for testing, 'production' for live
QBO_MODE=sandbox
"""
        env_path.write_text(template)
        print("✅ Created .env file template")
        print("\n⚠️  Please edit .env and add your QBO_CLIENT_ID and QBO_CLIENT_SECRET")
        print("   Get them from: https://developer.intuit.com")
        return False
    
    load_dotenv()
    
    client_id = os.getenv("QBO_CLIENT_ID")
    client_secret = os.getenv("QBO_CLIENT_SECRET")
    refresh_token = os.getenv("QBO_REFRESH_TOKEN")
    realm_id = os.getenv("QBO_REALM_ID")
    
    if not client_id:
        print("❌ QBO_CLIENT_ID not set in .env")
        print("   Get it from: https://developer.intuit.com → Your App → Keys & OAuth")
        return False
    else:
        print(f"✅ QBO_CLIENT_ID: {client_id[:20]}...")
    
    if not client_secret:
        print("❌ QBO_CLIENT_SECRET not set in .env")
        return False
    else:
        print(f"✅ QBO_CLIENT_SECRET: {'*' * 20}...")
    
    if not refresh_token:
        print("⚠️  QBO_REFRESH_TOKEN not set")
        print("   You'll need to run OAuth setup next")
        return None
    
    if not realm_id:
        print("⚠️  QBO_REALM_ID not set")
        print("   You'll need to run OAuth setup next")
        return None
    
    print(f"✅ QBO_REFRESH_TOKEN: {refresh_token[:20]}...")
    print(f"✅ QBO_REALM_ID: {realm_id}")
    print("✅ Configuration complete!")
    
    return True

def check_oauth_setup():
    """Check if OAuth is configured"""
    print_step(4, "Checking OAuth Connection")
    
    load_dotenv()
    refresh_token = os.getenv("QBO_REFRESH_TOKEN")
    realm_id = os.getenv("QBO_REALM_ID")
    
    if not refresh_token or not realm_id:
        print("⚠️  OAuth not configured yet")
        print("\nTo set up OAuth:")
        print("  1. Make sure you've added redirect URI to Intuit app:")
        print("     http://localhost:8080/callback")
        print("  2. Run: python initial_oauth_setup.py")
        return False
    
    # Test connection
    try:
        from quickbooks_client import get_company_info
        print("🔄 Testing QuickBooks connection...")
        company = get_company_info()
        print(f"✅ Connected to: {company.get('CompanyName', 'Unknown')}")
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nYour refresh token may have expired.")
        print("Run: python initial_oauth_setup.py to get a new token")
        return False

def main():
    """Main setup flow"""
    print_header("GreenTech Painting - QuickBooks API Setup")
    
    print("This script will check your setup and guide you through configuration.")
    print("Press Ctrl+C at any time to exit.\n")
    
    # Step 1: Python version
    if not check_python_version():
        print("\n❌ Setup cannot continue. Please install Python 3.8 or higher.")
        return 1
    
    # Step 2: Dependencies - auto-install
    if not check_dependencies():
        print("\n📦 Installing missing dependencies automatically...")
        result = os.system("pip install -r requirements_txt.txt")
        if result != 0:
            print("\n⚠️  Installation had issues. Please check manually.")
        if not check_dependencies():
            print("\n❌ Failed to install dependencies. Please install manually:")
            print("   pip install -r requirements_txt.txt")
            return 1
    
    # Step 3: Configuration
    config_status = check_env_file()
    if config_status is False:
        print("\n⚠️  Please configure your .env file and run this script again.")
        return 1
    
    if config_status is None:
        print("\n⚠️  OAuth setup needed. Run: python initial_oauth_setup.py")
        return 0
    
    # Step 4: OAuth
    if not check_oauth_setup():
        print("\n⚠️  OAuth setup needed. Run: python initial_oauth_setup.py")
        return 0
    
    # Success!
    print_header("✅ Setup Complete!")
    
    print("Your system is ready to use!\n")
    print("Next steps:")
    print("  1. Test with mock: python cli_push_estimate.py --json samples/quote_sample.json --mock")
    print("  2. Create real estimate: python cli_push_estimate.py --json samples/quote_sample.json")
    print("  3. Start API server: python start_server.py")
    print("\nFor detailed documentation, see: COMPLETE_SETUP_GUIDE.md")
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)

