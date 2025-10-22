"""
Helper functions for fetching API and cloud service statuses.
"""
from typing import Union, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import subprocess
import re
import logging
import requests
import feedparser
import undetected_chromedriver as uc
import pytz
# Globals
gmt_tz = pytz.timezone('GMT')
sg_tz = pytz.timezone('Singapore')


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


# API statuses
def get_openai_status() -> Dict[str, Any]:
    """
    Get OpenAI API status from their RSS feed.
    
    Returns:
        Dict containing status information
    """
    name = "OpenAI API Status"
    try:
        rss_url = 'https://status.openai.com/feed.rss'
        status_url = 'https://status.openai.com'
        feed = feedparser.parse(rss_url)
        
        if feed.entries:
            latest_entry = feed.entries[0]
            title = latest_entry.title
            issue_link = latest_entry.link
            description = latest_entry.description
            published_time = datetime.strptime(latest_entry.published, "%a, %d %b %Y %H:%M:%S %Z")
            # Make it time aware due to GMT time. Convert to GMT+8
            published_time  = published_time.replace(tzinfo=gmt_tz)
            published_time_sg = published_time.astimezone(tz=sg_tz)
            # Check for operational issues
            description_lower = description.lower()

            is_operational = "all impacted services have now fully recovered" in description_lower
            
            return {
                "name": name,
                "status": "Operational" if is_operational else "Disrupted",
                "status_url": status_url,
                "issue_link": issue_link,
                "operational": is_operational,
                "last_update": published_time_sg,
                "title": title,
                "description": description[:200] + "..." if len(description) > 200 else description
            }
    except Exception as e:
        logging.error(f"Error fetching OpenAI status: {e}")
    
    return {
        "name": name,
        "status": "Unknown",
        "status_url": status_url,
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
    name = "Deepseek API Status"
    try:
        rss_url = 'https://status.deepseek.com/history.atom'
        status_url = 'https://status.deepseek.com'
        feed = feedparser.parse(rss_url)
        
        if feed.entries:
            latest_entry = feed.entries[0]
            title = latest_entry.title
            issue_link = latest_entry.link
            content = latest_entry.get('content', [{}])[0].get('value', '') if latest_entry.get('content') else ''
            updated_time_raw = latest_entry.get('updated')
            # Extract updated time which is isoformat
            updated_time = datetime.fromisoformat(updated_time_raw) # Already in Beijing time, which is same as GMT+8
            
            # Check for operational issues
            content_lower = content.lower()

            # Look for specific keywords in the content
            is_operational = "[resolved]" in content_lower
            
            return {
                "name": name,
                "status": "Operational" if is_operational else "Disrupted",
                "status_url": status_url,
                "issue_link": issue_link,
                "operational": is_operational,
                "last_update": updated_time,
                "title": title,
                "description": content[:200] + "..." if len(content) > 200 else content
            }
    except Exception as e:
        logging.error(f"Error fetching DeepSeek status: {e}")
    
    return {
        "name": name,
        "status": "Unknown",
        "status_url": status_url,
        "operational": False,
        "last_update": "N/A",
        "title": "Error",
        "description": "Unable to fetch status"
    }

def get_langsmith_status() -> Dict[str, Any]:
    """
    Get LangSmith API status from their RSS feed.
    
    Returns:
        Dict containing status information
    """
    name = "Langsmith US"
    try:
        rss_url = 'https://status.smith.langchain.com/feed.rss'
        status_url = 'https://status.smith.langchain.com'
        feed = feedparser.parse(rss_url)
        
        if feed.entries:
            latest_entry = feed.entries[0]
            title = latest_entry.title
            issue_link = latest_entry.link
            description = latest_entry.description
            published_time = datetime.strptime(latest_entry.published, "%a, %d %b %Y %H:%M:%S %Z")
            published_time  = published_time.replace(tzinfo=gmt_tz)
            published_time_sg = published_time.astimezone(tz=sg_tz)

            # Check for operational issues
            description_lower = description.lower()

            matched_keywords = ["elevated", "degrad", "latency", "outage", "failing"]

            # Set to false if any of the keyword exist in description
            is_operational = all(keyword not in description_lower for keyword in matched_keywords)
            return {
                "name": name,
                "status": "Operational" if is_operational else "Disrupted", 
                "status_url": status_url,
                "issue_link": issue_link,
                "operational": is_operational,
                "last_update": published_time_sg,
                "title": title,
                "description": description[:200] + "..." if len(description) > 200 else description
            }
    except Exception as e:
        logging.error(f"Error fetching LangSmith status: {e}")
    
    return {
        "name": name,
        "status": "Unknown",
        "status_url": status_url,
        "operational": False,
        "last_update": "N/A",
        "title": "Error",
        "description": "Unable to fetch status"
    }

def get_gemini_status() -> Dict[str, Any]:
    """
    Get Google Gemini API status from their status page.
    As the url does not provided any rss feed, content scraping is required to extract necessary information, 
    Returns:
        Dict containing status information
    """
    name = "Google AI Studio and Gemini API Status"

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = None
    html = None
    
    # Detect Chrome version dynamically
    chrome_version = get_chrome_version()
    logging.info(f"Detected Chrome version: {chrome_version}")
    status_url = 'https://aistudio.google.com/status'
    try:
        # Let undetected_chromedriver use the detected Chrome version
        # use_subprocess=True helps avoid session connection issues
        driver = uc.Chrome(options=chrome_options, use_subprocess=True, version_main=chrome_version)
        driver.get(status_url)
        # Wait for the first ms-status-daily-log element to be present
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "ms-status-daily-log")))

        html = driver.page_source
    except Exception as e:
        logging.error(f"Error getting Gemini status from url: {status_url}. Error: {e}")
    finally:
        if driver:
            logging.info("Quitting Chrome driver")
            try:
                driver.quit()
            except Exception as e:
                logging.error(f"Error quitting driver: {e}")
   
    if html:
        soup = BeautifulSoup(html, "html.parser")
        logging.info("Parsing html as BeautifulSoup object")
        # Find the first ms-status-daily-log element
        ms_status_log = soup.find("ms-status-daily-log")
        if ms_status_log:
            gmt_tz = pytz.timezone('GMT')
            current_time = datetime.now(tz=gmt_tz)
            logging.info("Found ms-status-daily-log element in the page")
            #print(ms_status_log.prettify())
            # Get string
            status_text = ms_status_log.get_text(separator="\n", strip=False)
            status_elem_list = status_text.split("\n")
            # We expect at least 3 elements in the list (title, status, published time)
            if len(status_elem_list) > 2:
                incident_title = status_elem_list[0]
                incident_status = " - ".join([status_elem_list[1] , status_elem_list[2]])
                published_time_str = str(status_elem_list[3]).strip()

                # Parse the string into a datetime object
                datetime_object = datetime.strptime(published_time_str, "%b %d, %H:%M")
                # Get current year
                datetime_object = datetime_object.replace(year=current_time.year)
                published_time = datetime_object.replace(tzinfo=gmt_tz)

            else:
                incident_title = status_elem_list[0]
                incident_status = "Unable to retrieve incident status due to unexpected format"
                published_time = current_time # Assume the incident is happening now

            sg_tz = pytz.timezone('Singapore')
            published_time_sg = published_time.astimezone(sg_tz)
            
            description = incident_status + str(published_time_sg)
            conditions_str_lower = ["unavailable", "gemini"]

            # Match all conditions in the incident status
            matched_conditions = all(condition in incident_status.lower() for condition in conditions_str_lower)
            if matched_conditions:
                is_operational = True
            else:
                is_operational = False

            # Insert into Redis cache
            return {
                "name": name,
                "status": "Operational" if is_operational else "Disrupted",
                "status_url": status_url,
                "operational": is_operational,
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "title": incident_title,
                "description": description[:200] + "..." if len(description) > 200 else description
            }
    except Exception as e:
        logging.error(f"Error fetching Gemini status: {e}")
    
    return {
        "name": name,
        "status": "Unknown",
        "status_url": status_url,
        "operational": False,
        "last_update": "N/A",
        "title": "Error",
        "description": "Unable to fetch status"
    }

# Add get perplexity status
def get_perplexity_status() -> Dict[str, Any]:
    """
    Get Perplexity API status from their rss feed

    Returns:
        Dict containing status information
    """
    name = "Perplexity API Status"
    try:
        rss_url = 'https://status.perplexity.com/history.rss'
        status_url = 'https://status.perplexity.com'
        feed = feedparser.parse(rss_url)
        
        if feed.entries:
            latest_entry = feed.entries[0]
            title = latest_entry.title
            issue_link = latest_entry.link
            description = latest_entry.description
            published_time = datetime.strptime(latest_entry.published, "%a, %d %b %Y %H:%M:%S %z")
            published_time  = published_time.replace(tzinfo=gmt_tz)
            published_time_sg = published_time.astimezone(tz=sg_tz)
            # Check for operational issues
            description_lower = description.lower()
            is_operational = "resolved" in description_lower and not "api outage" in description_lower
            
            return {
                "name": name,
                "status": "Operational" if is_operational else "Disrupted",
                "status_url": status_url,
                "issue_link": issue_link,
                "operational": is_operational,
                "last_update": published_time_sg,
                "title": title,
                "description": description[:200] + "..." if len(description) > 200 else description
            }
    except Exception as e:
        logging.error(f"Error fetching Perplexity status: {e}")
    
    return {
        "name": name,
        "status": "Unknown",
        "status_url": status_url,
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
    name = "Anthropic API Status"
    try:
        rss_url = 'https://status.anthropic.com/history.rss'
        status_url = 'https://status.anthropic.com'
        feed = feedparser.parse(rss_url)
        
        if feed.entries:
            latest_entry = feed.entries[0]
            title = latest_entry.title
            issue_link = latest_entry.link
            description = latest_entry.description
            # Extract Published time and make it timezone aware
            published_time = datetime.strptime(latest_entry.published, "%a, %d %b %Y %H:%M:%S %z")
            published_time  = published_time.replace(tzinfo=gmt_tz)
            published_time_sg = published_time.astimezone(tz=sg_tz)
            # Check for operational issues
            description_lower = description.lower()
            is_operational = "resolved" in description_lower
            
            return {
                "name": name,
                "status": "Operational" if is_operational else "Disrupted",
                "status_url": status_url,
                "issue_link": issue_link,
                "operational": is_operational,
                "last_update": published_time_sg,
                "title": title,
                "description": description[:200] + "..." if len(description) > 200 else description
            }
    except Exception as e:
        logging.error(f"Error fetching Anthropic status: {e}")
    
    return {
        "name": name,
        "status": "Unknown",
        "status_url": status_url,
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
    name = "Google Cloud Platform Status"
    try:
        # GCP Status API endpoint
        rss_url = 'https://status.cloud.google.com/en/feed.atom'
        status_url = 'https://status.cloud.google.com'
        feed = feedparser.parse(rss_url)
        
        if feed.entries:
            latest_entry = feed.entries[0]
            title = latest_entry.title
            content = latest_entry.get('content', [{}])[0].get('value', '') if latest_entry.get('content') else ''
            published_time = datetime.strptime(latest_entry.published, "%a, %d %b %Y %H:%M:%S %Z")
            published_time  = published_time.replace(tzinfo=gmt_tz)
            published_time_sg = published_time.astimezone(tz=sg_tz)
            # Check for operational issues based on title name
            title_lower = title.lower()
            is_operational = "resolved:" in title_lower
            
            return {
                "name": name,
                "status": "Operational" if is_operational else "Disrupted",
                "status_url": status_url,
                "operational": is_operational,
                "last_update": published_time_sg,
                "title": title,
                "description": content[:200] + "..." if len(content) > 200 else content
            }
    except Exception as e:
        logging.error(f"Error fetching GCP status: {e}")
    
    return {
        "name": name,
        "status": "Unknown",
        "status_url": status_url,
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
    name = "Microsoft Azure Status US"
    try:
        # Azure Status API endpoint
        rss_url = 'https://rssfeed.azure.status.microsoft/en-us/status/feed/'
        status_url = 'https://status.azure.com'
        feed = feedparser.parse(rss_url)
        
        if feed.entries:
            latest_entry = feed.entries[0]
            title = latest_entry.title
            description = latest_entry.description
            
            # Check for operational issues
            description_lower = description.lower()
            is_operational = "azure status" in description_lower
            
            return {
                "name": name,
                "status": "Operational" if is_operational else "Disrupted",
                "status_url": status_url,
                "operational": is_operational,
                "last_update": latest_entry.published,
                "title": title,
                "description": description[:200] + "..." if len(description) > 200 else description
            }
    except Exception as e:
        logging.error(f"Error fetching Anthropic status: {e}")

    return {
        "name": name,
        "status": "Unknown",
        "status_url": status_url,
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
    name = "Amazon Web Service (AWS) Cloud Status"
    try:
        # AWS Health Dashboard endpoint
        status_url = 'https://health.aws.amazon.com/health/status'
        response = requests.get(status_url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for event-state div class
            event_state_div = soup.find('div', class_='event-state')
            if event_state_div:
                # Check if there's a no-events sub div
                no_events_div = event_state_div.find('div', class_='no-events')
                is_operational = no_events_div is not None
                
                return {
                    "name": "Amazon Web Service (AWS) Cloud",
                    "status": "Operational" if is_operational else "Disrupted",
                    "status_url": status_url,
                    "operational": is_operational,
                    "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "title": "Amazon Web Services",
                    "description": "All systems operational" if is_operational else "Active Disrupted"
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