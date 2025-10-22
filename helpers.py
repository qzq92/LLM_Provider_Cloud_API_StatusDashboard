"""
Helper functions for fetching API and cloud service statuses.
"""
from typing import Union, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import subprocess
import re
import logging
import requests
import feedparser
import undetected_chromedriver as uc
import pytz
import time
import asyncio
# Configure logging for helpers module
logger = logging.getLogger(__name__)
# Globals
gmt_tz = pytz.timezone('GMT')
sg_tz = pytz.timezone('Singapore')

# Global ChromeDriver instance to prevent multiple creations
_chrome_driver = None

# Chrome driver functions removed - using per-call synchronous approach

def parse_feed_date(entry, fallback_timezone=None):
    """
    Parse date from RSS/Atom feed entry, handling different formats.
    
    Args:
        entry: Feed entry object
        fallback_timezone: Timezone to use if parsing fails
    
    Returns:
        datetime object in Singapore timezone
    """
    if fallback_timezone is None:
        fallback_timezone = sg_tz
    
    # Try different date fields and formats
    date_fields = ['updated', 'published', 'pubDate']
    date_formats = [
        # ISO 8601 formats
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z", 
        "%Y-%m-%dT%H:%M:%SZ",
        # RSS formats
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S %z",
        # Simple formats
        "%Y-%m-%d %H:%M:%S"
    ]
    
    for field in date_fields:
        date_str = entry.get(field, '')
        if not date_str:
            continue
            
        # Handle Z suffix for UTC
        if date_str.endswith('Z'):
            date_str = date_str.replace('Z', '+00:00')
        
        for fmt in date_formats:
            try:
                if fmt.endswith('%z') or fmt.endswith('%Z'):
                    # Format includes timezone
                    parsed_time = datetime.strptime(date_str, fmt)
                    if parsed_time.tzinfo is None:
                        parsed_time = parsed_time.replace(tzinfo=gmt_tz)
                else:
                    # Format doesn't include timezone, assume GMT
                    parsed_time = datetime.strptime(date_str, fmt).replace(tzinfo=gmt_tz)
                
                return parsed_time.astimezone(sg_tz)
            except ValueError:
                continue
    
    # If all parsing fails, return current time
    logger.warning(f"Could not parse date from entry, using current time")
    return datetime.now(tz=fallback_timezone)

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
                        logger.info(f"Detected Chrome version: {major_version} from output: {version_text}")
                        return major_version
            except (subprocess.SubprocessError, FileNotFoundError):
                continue
        
        logger.warning("Could not detect Chrome version, will let undetected_chromedriver auto-detect")
        return None
    except Exception as e:
        logger.error(f"Error detecting Chrome version: {e}")
        return None


# API statuses
async def get_openai_status() -> Dict[str, Any]:
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
            # Use the new date parsing helper
            published_time_sg = parse_feed_date(latest_entry)
            # Check for operational issues
            description_lower = description.lower()

            is_operational = "all impacted services have now fully recovered" in description_lower
            
            return {
                "name": name,
                "status": "Operational" if is_operational else "Disrupted",
                "status_url": status_url,
                "issue_link": issue_link,
                # "last_update": published_time_sg,
                # "title": title,
                # "description": description[:200] + "..." if len(description) > 200 else description
            }
    except Exception as e:
        logger.error(f"Error fetching OpenAI status: {e}")
    
    return {
        "name": name,
        "status": "Unknown",
        "status_url": status_url,
        "issue_link": "Refer to status page as no spceific link is available"
        # "last_update": "N/A",
        # "title": "Error",
        # "description": "Unable to fetch status"
    }

async def get_deepseek_status() -> Dict[str, Any]:
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
            is_operational = True if "resolved" in content_lower else False
            
            return {
                "name": name,
                "status": "Operational" if is_operational else "Disrupted",
                "status_url": status_url,
                "issue_link": issue_link,
                # "last_update": updated_time,
                # "title": title,
                # "description": content[:200] + "..." if len(content) > 200 else content
            }
    except Exception as e:
        logger.error(f"Error fetching DeepSeek status: {e}")
    
    return {
        "name": name,
        "status": "Unknown",
        "status_url": status_url,
        "issue_link": "Refer to status page as no spceific link is available"
        # "last_update": "N/A",
        # "title": "Error",
        # "description": "Unable to fetch status"
    }

async def get_langsmith_status() -> Dict[str, Any]:
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
            # Use the new date parsing helper
            published_time_sg = parse_feed_date(latest_entry)

            # Check for operational issues
            description_lower = description.lower()
            logger.info(f"Langsmith description: {description_lower}")
            # Set to false if any of the keyword exist in description
            is_operational = "resolved" in description_lower
            return {
                "name": name,
                "status": "Operational" if is_operational else "Disrupted", 
                "status_url": status_url,
                "issue_link": issue_link,
                #"last_update": published_time_sg,
                # "title": title,
                # "description": description[:200] + "..." if len(description) > 200 else description
            }
    except Exception as e:
        logging.error(f"Error fetching LangSmith status: {e}")
    
    return {
        "name": name,
        "status": "Unknown",
        "status_url": status_url,
        "issue_link": "Refer to status page as no spceific link is available"
        # "last_update": "N/A",
        # "title": "Error",
        # "description": "Unable to fetch status"
    }

def get_gemini_status() -> Dict[str, Any]:
    """
    Get Google Gemini API status using Chrome driver (synchronous).
    Returns:
        Dict containing status information
    """
    name = "Google AI Studio and Gemini API Status"
    status_url = 'https://aistudio.google.com/status'
    
    # Use global Chrome driver instance to prevent multiple creations
    global _chrome_driver
    driver = None
    html = None
    
    try:
        # Check if we already have a driver instance
        if _chrome_driver is not None:
            try:
                # Test if the existing driver is still functional
                _chrome_driver.current_url
                driver = _chrome_driver
                logger.info("Reusing existing Chrome driver instance")
            except Exception:
                # Driver is no longer functional, create a new one
                logger.info("Existing driver is no longer functional, creating new one")
                _chrome_driver = None
        
        if _chrome_driver is None:
            logger.info("Creating new Chrome driver for Gemini status")
            
            # Try to get Chrome version first

            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")
            chrome_options.add_argument("--disable-javascript")
            
            # Try undetected_chromedriver first (more reliable)
            try:
                logger.info("Attempting to use undetected_chromedriver")
                _chrome_driver = uc.Chrome(
                    options=chrome_options, 
                    use_subprocess=True
                )
                logger.info("Successfully created undetected_chromedriver instance")
            except Exception as uc_error:
                logger.warning(f"undetected_chromedriver failed: {uc_error}")
                logger.info("Falling back to ChromeDriverManager")
                try:
                    # Fallback to ChromeDriverManager
                    options = webdriver.ChromeOptions()
                    options.add_argument('--headless')
                    options.add_argument("--disable-gpu")
                    options.add_argument("--disable-dev-shm-usage")
                    options.add_argument("--disable-extensions")
                    options.add_argument("--disable-plugins")
                    options.add_argument("--disable-images")
                    options.add_argument("--disable-javascript")
                    
                    driver_manager = ChromeDriverManager()
                    _chrome_driver = webdriver.Chrome(
                        service=Service(driver_manager.install()), 
                        options=options
                    )
                    logger.info("Successfully created ChromeDriverManager instance")
                except Exception as cm_error:
                    logger.error(f"ChromeDriverManager also failed: {cm_error}")
                    logger.warning("All Chrome methods failed")
                    _chrome_driver = None
        
        driver = _chrome_driver
        
        if driver is not None:
            logger.info("Using Chrome driver for Gemini status")
            # Navigate to the status page
            driver.get(status_url)
            # Wait for the first ms-status-daily-log element to be present
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "ms-status-daily-log")))
            html = driver.page_source
            logger.info("Successfully retrieved Gemini status page content")
        
    except Exception as e:
        logger.error(f"Error getting Gemini status from url: {status_url}. Error: {e}")
    finally:
        # Don't quit the global driver instance, keep it for reuse
        # Only quit if there was an error creating the driver
        if driver and driver != _chrome_driver:
            logger.info("Quitting temporary Chrome driver")
            try:
                driver.quit()
            except Exception as e:
                logger.error(f"Error quitting driver: {e}")

    if html:
        logger.info("Parsing html page of gemini")
        try:
            soup = BeautifulSoup(html, "html.parser")
            logger.info("Parsing html as BeautifulSoup object")
            
            # Try to find the ms-status-daily-log element first (Chrome method)
            ms_status_log = soup.find("ms-status-daily-log")
            if ms_status_log:
                gmt_tz = pytz.timezone('GMT')
                current_time = datetime.now(tz=gmt_tz)
                logger.info("Found ms-status-daily-log element in the page")
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

                is_operational = "resolved" in incident_status.lower()
                # Insert into Redis cache
                return {
                    "name": name,
                    "status": "Operational" if is_operational else "Disrupted",
                    "status_url": status_url,
                    "issue_link": "Refer to status page as no spceific link is available", # No specific issue link provided in the status page
                    # "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    # "title": incident_title,
                    # "description": description[:200] + "..." if len(description) > 200 else description
                }
            else:
                logger.warning("No ms-status-daily-log element found in Gemini status page")
                # Return error if the expected element is not found
                return {
                    "name": name,
                    "status": "Unknown",
                    "status_url": status_url,
                    "issue_link": "Refer to status page as no spceific link is available"
                    # "last_update": "N/A",
                    # "title": "Error",
                    # "description": "Expected status element not found on page"
                }
        except Exception as e:
            logger.error(f"Error fetching Gemini status: {e}")
    
    # If we reach here, Chrome method failed
    logger.warning("Chrome method failed for Gemini status, returning error status")
    return {
        "name": name,
        "status": "Unknown",
        "status_url": status_url,
        "issue_link": "Refer to status page as no spceific link is available"
        # "last_update": "N/A",
        # "title": "Error",
        # "description": "Unable to fetch status - Chrome method failed"
    }

# Add get perplexity status
async def get_perplexity_status() -> Dict[str, Any]:
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
            # Use the new date parsing helper
            published_time_sg = parse_feed_date(latest_entry)
            # Check for operational issues
            description_lower = description.lower()
            is_operational = "resolved" in description_lower and not "api outage" in description_lower
            
            return {
                "name": name,
                "status": "Operational" if is_operational else "Disrupted",
                "status_url": status_url,
                "issue_link": issue_link,
                # "last_update": published_time_sg,
                # "title": title,
                # "description": description[:200] + "..." if len(description) > 200 else description
            }
    except Exception as e:
        logger.error(f"Error fetching Perplexity status: {e}")
    
    return {
        "name": name,
        "status": "Unknown",
        "status_url": status_url,
        "issue_link": issue_link
        # "last_update": "N/A",
        # "title": "Error",
        # "description": "Unable to fetch status"
    }

async def get_anthropic_status() -> Dict[str, Any]:
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
            # Use the new date parsing helper
            published_time_sg = parse_feed_date(latest_entry)
            # Check for operational issues
            description_lower = description.lower()
            is_operational = "resolved" in description_lower
            
            return {
                "name": name,
                "status": "Operational" if is_operational else "Disrupted",
                "status_url": status_url,
                "issue_link": issue_link,
                # "last_update": published_time_sg,
                # "title": title,
                # "description": description[:200] + "..." if len(description) > 200 else description
            }
    except Exception as e:
        logger.error(f"Error fetching Anthropic status: {e}")
    
    return {
        "name": name,
        "status": "Unknown",
        "status_url": status_url,
        "issue_link": "Refer to status page as no spceific link is available"
        # "last_update": "N/A",
        # "title": "Error",
        # "description": "Unable to fetch status"
    }


# Cloud related status using single RSS source
async def get_gcp_status() -> Dict[str, Any]:
    """
    Get Google Cloud Platform status (Global).
    
    Returns:
        Dict containing status information
    """
    name = "Google Cloud Platform Status (Global)"
    try:
        # GCP Status API endpoint
        rss_url = 'https://status.cloud.google.com/en/feed.atom'
        status_url = 'https://status.cloud.google.com'
        logger.info(f"Parsing GCP status feed as feedparser object from {rss_url}")
        feed = feedparser.parse(rss_url)
        
        if feed.entries:
            latest_entry = feed.entries[0]
            title = latest_entry.title
            content = latest_entry.get('content', [{}])[0].get('value', '') if latest_entry.get('content') else ''
            # Use the new date parsing helper
            published_time_sg = parse_feed_date(latest_entry)
            # Check for operational issues based on title name
            title_lower = title.lower()
            is_operational = "resolved:" in title_lower
            
            return {
                "name": name,
                "status": "Operational" if is_operational else "Disrupted",
                "status_url": status_url,
                "issue_link": "Refer to status page as no spceific link is available", # No specific issue link provided in the status page
            }
    except Exception as e:
        logger.error(f"Error fetching GCP status: {e}")
    
    return {
        "name": name,
        "status": "Unknown",
        "status_url": status_url,
        "issue_link": "Refer to status page as no spceific link is available"
    }

async def get_azure_status() -> Dict[str, Any]:
    """
    Get Microsoft Azure status (US).
    
    Returns:
        Dict containing status information
    """
    name = "Microsoft Azure Status US"
    try:
        # Azure Status API endpoint
        rss_url = 'https://rssfeed.azure.status.microsoft/en-us/status/feed/'
        status_url = 'https://status.azure.com'
        logger.info("Parsing Azure status feed as feedparser object")
        feed = feedparser.parse(rss_url)
        #logger.info(f"Feed: {feed}")
        if feed.entries:
            logger.info("Found feed in Azure")
    
            return {
                "name": name,
                "status": "Disrupted",
                "status_url": status_url,
                "issue_link": "Refer to status page as no spceific link is available", # No specific issue link provided in the status page
            }
        # No feed found, assume operational
        else:
            return {
                "name": name,
                "status": "Operational",
                "status_url": status_url,
                "issue_link": "Refer to status page as no spceific link is available", # No specific issue link provided in the status page
            }
    except Exception as e:
        logger.error(f"Error fetching Azure status: {e}")

    return {
        "name": name,
        "status": "Unknown",
        "status_url": status_url,
        "issue_link": "Refer to status page as no spceific link is available"
    }

async def get_aws_status() -> Dict[str, Any]:
    """
    Get AWS service status from AWS Global Health Dashboard.
    
    Returns:
        Dict containing status information
    """
    name = "Amazon Web Service (AWS) Global Cloud Status"
    try:
        # AWS Health Dashboard endpoint
        rss_url = 'https://status.aws.amazon.com/rss/all.rss'
        status_url = 'https://health.aws.amazon.com/health/status'
        logger.info("Parsing AWS status feed as feedparser object")
        feed = feedparser.parse(rss_url)
        #logger.info(f"Feed: {feed}")
        if feed.entries:
            logger.info("Found feed in AWS")

            return {
                "name": name,
                "status": "Disrupted",
                "status_url": status_url,
                "issue_link": "Refer to status page as no spceific link is available", # No specific issue link provided in the status page
            }
        # No feed found, assume operational
        else:
            return {
                "name": name,
                "status": "Operational",
                "status_url": status_url,
                "issue_link": "Refer to status page as no spceific link is available", # No specific issue link provided in the status page
            }

    except Exception as e:
        logger.error(f"Error fetching AWS status: {e}")
    
    return {
        "name": name,
        "status": "Unknown",
        "status_url": status_url,
        "issue_link": "Refer to status page as no spceific link is available"
    }