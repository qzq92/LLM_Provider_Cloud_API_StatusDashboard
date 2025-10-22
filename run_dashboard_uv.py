#!/usr/bin/env python3
"""
Run the Streamlit dashboard using uv.
"""
import subprocess
import sys
import os

def main():
    """Run the Streamlit dashboard using uv."""
    try:
        print("🚀 Starting LLM & Cloud API Status Dashboard with uv...")
        
        # Check if uv is available
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ uv is not installed. Please install it first:")
            print("   curl -LsSf https://astral.sh/uv/install.sh | sh")
            print("   # or")
            print("   pip install uv")
            sys.exit(1)
        
        # Run the dashboard with uv
        subprocess.run([
            "uv", "run", "streamlit", "run", "app_main.py",
            "--server.port", "8501",
            "--server.address", "localhost"
        ])
        
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error running dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

