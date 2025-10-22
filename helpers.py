"""
Helper functions for fetching API and cloud service statuses.
"""
from typing import Union, Dict, Any
import subprocess
import re
import logging
import requests
import feedparser
from datetime import datetime
from bs4 import BeautifulSoup
def get_chrome_version()-> Union[int, None]:
    """
    Detect the installed Chrome browser version.
    
    Returns:
        int: Major version number of Chrome, or None if unable to detect
    """
    try:
        # Try common Chrome binary locations for different OS
        chrome_commands = [
            ['google-chrome', '--version'],
            ['google-chrome-stable', '--version'],
            ['chromium', '--version'],
            ['chromium-browser', '--version'],
            ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--version'],  # macOS
            ['chrome', '--version'],
        ]
        
        for cmd in chrome_commands:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    # Parse version from output like "Google Chrome 140.0.7339.207"
                    version_text = result.stdout.strip()
                    version_match = re.search(r'(\d+)\.', version_text)
                    if version_match:
                        major_version = int(version_match.group(1))
                        logging.info(f"Detected Chrome version: {major_version} from output: {version_text}")
                        return major_version
            except (subprocess.SubprocessError, FileNotFoundError):
                continue
        
        logging.warning("Could not detect Chrome version, will let undetected_chromedriver auto-detect")
        return None
    except Exception as e:
        logging.error(f"Error detecting Chrome version: {e}")
        return None

def get_openai_status() -> Dict[str, Any]:
    """
    Get OpenAI API status from their RSS feed.
    
    Returns:
        Dict containing status information
    """
    try:
        rss_url = 'https://status.openai.com/feed.rss'
        feed = feedparser.parse(rss_url)
        
        if feed.entries:
            latest_entry = feed.entries[0]
            title = latest_entry.title
            description = latest_entry.description
            
            # Check for operational issues
            description_lower = description.lower()
            conditions = ["partial outage", "degraded performance"]
            
            matched_conditions = [condition for condition in conditions if condition in description_lower]
            is_operational = len(matched_conditions) == 0 or "all impacted services have now fully recovered" in description_lower
            
            return {
                "name": "OpenAI",
                "status": "Operational" if is_operational else "Issues Detected",
                "operational": is_operational,
                "last_update": latest_entry.published,
                "title": title,
                "description": description[:200] + "..." if len(description) > 200 else description
            }
    except Exception as e:
        logging.error(f"Error fetching OpenAI status: {e}")
    
    return {
        "name": "OpenAI",
        "status": "Unknown",
        "operational": False,
        "last_update": "N/A",
        "title": "Error",
        "description": "Unable to fetch status"
    }

def get_deepseek_status() -> Dict[str, Any]:
    """
    Get DeepSeek API status from their RSS feed.
    
    Returns:
        Dict containing status information
    """
    try:
        rss_url = 'https://status.deepseek.com/history.atom'
        feed = feedparser.parse(rss_url)
        
        if feed.entries:
            latest_entry = feed.entries[0]
            title = latest_entry.title
            content = latest_entry.get('content', [{}])[0].get('value', '') if latest_entry.get('content') else ''
            
            # Check for operational issues
            content_lower = content.lower()
            is_operational = "api service not available" not in content_lower
            
            return {
                "name": "DeepSeek",
                "status": "Operational" if is_operational else "Issues Detected",
                "operational": is_operational,
                "last_update": latest_entry.updated,
                "title": title,
                "description": content[:200] + "..." if len(content) > 200 else content
            }
    except Exception as e:
        logging.error(f"Error fetching DeepSeek status: {e}")
    
    return {
        "name": "DeepSeek",
        "status": "Unknown",
        "operational": False,
        "last_update": "N/A",
        "title": "Error",
        "description": "Unable to fetch status"
    }

def get_gemini_status() -> Dict[str, Any]:
    """
    Get Google Gemini API status from their status page.
    
    Returns:
        Dict containing status information
    """
    try:
        # This is a simplified version - in production you might want to use Selenium like in the original code
        response = requests.get("https://aistudio.google.com/status", timeout=10)
        if response.status_code == 200:
            # Simple check - if the page loads, assume operational
            # In a real implementation, you'd parse the actual status
            return {
                "name": "Gemini",
                "status": "Operational",
                "operational": True,
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "title": "Google AI Studio",
                "description": "Service appears to be operational"
            }
    except Exception as e:
        logging.error(f"Error fetching Gemini status: {e}")
    
    return {
        "name": "Gemini",
        "status": "Unknown",
        "operational": False,
        "last_update": "N/A",
        "title": "Error",
        "description": "Unable to fetch status"
    }

def get_anthropic_status() -> Dict[str, Any]:
    """
    Get Anthropic API status from their RSS feed.
    
    Returns:
        Dict containing status information
    """
    try:
        rss_url = 'https://status.anthropic.com/history.rss'
        feed = feedparser.parse(rss_url)
        
        if feed.entries:
            latest_entry = feed.entries[0]
            title = latest_entry.title
            description = latest_entry.description
            
            # Check for operational issues
            description_lower = description.lower()
            is_operational = "resolved" in description_lower or "monitoring - a fix has been implemented" in description_lower
            
            return {
                "name": "Anthropic",
                "status": "Operational" if is_operational else "Issues Detected",
                "operational": is_operational,
                "last_update": latest_entry.published,
                "title": title,
                "description": description[:200] + "..." if len(description) > 200 else description
            }
    except Exception as e:
        logging.error(f"Error fetching Anthropic status: {e}")
    
    return {
        "name": "Anthropic",
        "status": "Unknown",
        "operational": False,
        "last_update": "N/A",
        "title": "Error",
        "description": "Unable to fetch status"
    }


# Cloud related status using single RSS source
def get_gcp_status() -> Dict[str, Any]:
    """
    Get Google Cloud Platform status.
    
    Returns:
        Dict containing status information
    """
    try:
        # GCP Status API endpoint
        rss_url = 'https://status.cloud.google.com/en/feed.atom'
        feed = feedparser.parse(rss_url)
        
        if feed.entries:
            latest_entry = feed.entries[0]
            title = latest_entry.title
            content = latest_entry.get('content', [{}])[0].get('value', '') if latest_entry.get('content') else ''
            
            # Check for operational issues based on title name
            title_lower = title.lower()
            is_operational = "resolved:" in title_lower
            
            return {
                "name": "GCP",
                "status": "Operational" if is_operational else "Issues Detected",
                "operational": is_operational,
                "last_update": latest_entry.updated,
                "title": title,
                "description": content[:200] + "..." if len(content) > 200 else content
            }
    except Exception as e:
        logging.error(f"Error fetching GCP status: {e}")
    
    return {
        "name": "GCP",
        "status": "Unknown",
        "operational": False,
        "last_update": "N/A",
        "title": "Error",
        "description": "Unable to fetch status"
    }

def get_azure_status() -> Dict[str, Any]:
    """
    Get Microsoft Azure status.
    
    Returns:
        Dict containing status information
    """
    try:
        # Azure Status API endpoint
        rss_url = 'https://rssfeed.azure.status.microsoft/en-us/status/feed/'
        feed = feedparser.parse(rss_url)
        
        if feed.entries:
            latest_entry = feed.entries[0]
            title = latest_entry.title
            description = latest_entry.description
            
            # Check for operational issues
            description_lower = description.lower()
            is_operational = "azure status" in description_lower
            
            return {
                "name": "Azure",
                "status": "Operational" if is_operational else "Issues Detected",
                "operational": is_operational,
                "last_update": latest_entry.published,
                "title": title,
                "description": description[:200] + "..." if len(description) > 200 else description
            }
    except Exception as e:
        logging.error(f"Error fetching Anthropic status: {e}")

    return {
        "name": "Azure",
        "status": "Unknown",
        "operational": False,
        "last_update": "N/A",
        "title": "Error",
        "description": "Unable to fetch status"
    }

def get_aws_status() -> Dict[str, Any]:
    """
    Get AWS service status from AWS Health Dashboard.
    
    Returns:
        Dict containing status information
    """
    try:
        # AWS Health Dashboard endpoint
        response = requests.get("https://health.aws.amazon.com/health/status", timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for event-state div class
            event_state_div = soup.find('div', class_='event-state')
            if event_state_div:
                # Check if there's a no-events sub div
                no_events_div = event_state_div.find('div', class_='no-events')
                is_operational = no_events_div is not None
                
                return {
                    "name": "AWS",
                    "status": "Operational" if is_operational else "Issues Detected",
                    "operational": is_operational,
                    "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "title": "Amazon Web Services",
                    "description": "All systems operational" if is_operational else "Active issues detected"
                }
            else:
                # If we can't find the event-state div, assume operational
                return {
                    "name": "AWS",
                    "status": "Operational",
                    "operational": True,
                    "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "title": "Amazon Web Services",
                    "description": "All systems operational"
                }
    except Exception as e:
        logging.error(f"Error fetching AWS status: {e}")
    
    return {
        "name": "AWS",
        "status": "Unknown",
        "operational": False,
        "last_update": "N/A",
        "title": "Error",
        "description": "Unable to fetch status"
    }