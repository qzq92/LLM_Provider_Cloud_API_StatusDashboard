#!/usr/bin/env python3
"""
Setup script to initialize uv environment and generate lock file.
"""
import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False

def main():
    """Setup uv environment and generate lock file."""
    print("🚀 Setting up uv environment for LLM & Cloud API Status Dashboard")
    
    # Check if uv is installed
    if not run_command("uv --version", "Checking uv installation"):
        print("❌ uv is not installed. Please install it first:")
        print("   curl -LsSf https://astral.sh/uv/install.sh | sh")
        print("   # or")
        print("   pip install uv")
        sys.exit(1)
    
    # Initialize uv project
    if not run_command("uv init --no-readme", "Initializing uv project"):
        print("⚠️  Project may already be initialized")
    
    # Sync dependencies and generate lock file
    if not run_command("uv sync", "Syncing dependencies and generating lock file"):
        print("❌ Failed to sync dependencies")
        sys.exit(1)
    
    # Show installed packages
    run_command("uv pip list", "Listing installed packages")
    
    print("\n🎉 Setup complete!")
    print("\n📋 Next steps:")
    print("1. Run the dashboard: uv run streamlit run app_main.py")
    print("2. Or activate the environment: uv shell")
    print("3. Then run: streamlit run app_main.py")

if __name__ == "__main__":
    main()

