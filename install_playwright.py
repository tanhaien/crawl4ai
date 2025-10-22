#!/usr/bin/env python3
"""
Script to install Playwright browsers for Streamlit Cloud deployment
"""
import subprocess
import sys
import os

def install_playwright_browsers():
    """Install Playwright browsers"""
    try:
        print("Installing Playwright browsers...")
        result = subprocess.run([
            sys.executable, "-m", "playwright", "install", "chromium"
        ], capture_output=True, text=True, check=True)
        print("✅ Playwright browsers installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing Playwright browsers: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False

if __name__ == "__main__":
    install_playwright_browsers()
