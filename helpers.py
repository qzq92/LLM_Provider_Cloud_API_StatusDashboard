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
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
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

# Global ChromeDriver instances to prevent multiple creations
_chrome_driver_gemini = None
_chrome_driver_alicloud = None
_chrome_driver_dify = None

# Global session for HTTP requests to avoid connection pool issues
_http_session = None

def get_http_session():
    """Get or create a global HTTP session with proper connection pooling."""
    global _http_session
    if _http_session is None:
        _http_session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        # Configure adapter with retry strategy
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,  # Number of connection pools
            pool_maxsize=20,     # Maximum number of connections in pool
            pool_block=False     # Don't block when pool is full
        )
        
        _http_session.mount("http://", adapter)
        _http_session.mount("https://", adapter)
        
        # Set timeout for all requests
        _http_session.timeout = 10
        
        logger.info("Created new HTTP session with connection pooling")
    
    return _http_session

def cleanup_resources():
    """Clean up global resources to prevent connection pool issues."""
    global _chrome_driver_gemini, _chrome_driver_alicloud, _chrome_driver_dify, _http_session
    
    # Clean up Gemini Chrome driver
    if _chrome_driver_gemini is not None:
        try:
            _chrome_driver_gemini.quit()
            logger.info("Cleaned up Gemini Chrome driver")
        except Exception as e:
            logger.warning(f"Error cleaning up Gemini Chrome driver: {e}")
        finally:
            _chrome_driver_gemini = None
    
    # Clean up Alibaba Cloud Chrome driver
    if _chrome_driver_alicloud is not None:
        try:
            _chrome_driver_alicloud.quit()
            logger.info("Cleaned up Alibaba Cloud Chrome driver")
        except Exception as e:
            logger.warning(f"Error cleaning up Alibaba Cloud Chrome driver: {e}")
        finally:
            _chrome_driver_alicloud = None
    
    # Clean up Dify Chrome driver
    if _chrome_driver_dify is not None:
        try:
            _chrome_driver_dify.quit()
            logger.info("Cleaned up Dify Chrome driver")
        except Exception as e:
            logger.warning(f"Error cleaning up Dify Chrome driver: {e}")
        finally:
            _chrome_driver_dify = None
    
    # Clean up HTTP session
    if _http_session is not None:
        try:
            _http_session.close()
            logger.info("Cleaned up HTTP session")
        except Exception as e:
            logger.warning(f"Error cleaning up HTTP session: {e}")
        finally:
            _http_session = None

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
    
    Operational Status Logic:
    - Fetches the latest entry from OpenAI's RSS feed
    - Checks if the description contains "all impacted services have now fully recovered"
    - If found: Status = "Operational"
    - If not found: Status = "Disrupted"
    - If RSS parsing fails: Status = "Unknown"
    
    Returns:
        Dict containing status information
    """
    name = "OpenAI API Status"
    try:
        rss_url = 'https://status.openai.com/feed.rss'
        status_url = 'https://status.openai.com'
        session = get_http_session()
        response = session.get(rss_url)
        feed = feedparser.parse(response.content)
        
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
        "issue_link": "Refer to status page as no specific link is available"
        # "last_update": "N/A",
        # "title": "Error",
        # "description": "Unable to fetch status"
    }

async def get_deepseek_status() -> Dict[str, Any]:
    """
    Get DeepSeek API status from their RSS feed.
    
    Operational Status Logic:
    - Fetches the latest entry from DeepSeek's Atom feed
    - Checks if the latest feed content contains "resolved"
    - If found: Status = "Operational"
    - If not found: Status = "Disrupted"
    - If feed parsing fails: Status = "Unknown"
    
    Returns:
        Dict containing status information
    """
    name = "Deepseek API Status"
    try:
        rss_url = 'https://status.deepseek.com/history.atom'
        status_url = 'https://status.deepseek.com'
        session = get_http_session()
        response = session.get(rss_url)
        feed = feedparser.parse(response.content)
        
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
        "issue_link": "Refer to status page as no specific link is available"
        # "last_update": "N/A",
        # "title": "Error",
        # "description": "Unable to fetch status"
    }

async def get_langsmith_status() -> Dict[str, Any]:
    """
    Get LangSmith API status from their RSS feed.
    
    Operational Status Logic:
    - Fetches the latest entry from LangSmith's RSS feed
    - Checks if the description contains "resolved"
    - If found: Status = "Operational"
    - If not found: Status = "Disrupted"
    - If RSS parsing fails: Status = "Unknown"
    
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
            #logger.info(f"Langsmith description: {description_lower}")
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
        "issue_link": "Refer to status page as no specific link is available"
        # "last_update": "N/A",
        # "title": "Error",
        # "description": "Unable to fetch status"
    }


async def get_llamaindex_status() -> Dict[str, Any]:
    """
    Get LlamaIndex status from their status page.
    
    Operational Status Logic:
    - Fetches the LlamaIndex status page HTML content
    - Searches for <p class="color-secondary"> elements
    - Checks if any element contains "no incidents reported today"
    - If found: Status = "Operational"
    - If not found: Status = "Disrupted"
    - If page parsing fails: Status = "Unknown"
    
    Returns:
        Dict containing status information
    """
    name = "LlamaIndex"
        status_url = 'https://llamaindex.statuspage.io/'
    try:
        # Use session to fetch the status page
        session = get_http_session()
        response = session.get(status_url)
        response.raise_for_status()
        
        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for the nested <p class="color-secondary"> element
        color_secondary_elements = soup.find_all('p', class_='color-secondary')
        
        is_operational = False
        for element in color_secondary_elements:
            text_content = element.get_text().strip().lower()
            key_phrase = "no incidents reported today"
            if key_phrase in text_content:
                logger.info(f"LlamaIndex: Found required key phrase {key_phrase} to indicate no issue")
                is_operational = True
                break
        
        return {
            "name": name,
            "status": "Operational" if is_operational else "Disrupted",
            "status_url": status_url,
            "issue_link": "Refer to status page as no specific link is available"
        }

    except Exception as e:
        logging.error(f"Error fetching LlamaIndex status: {e}")
    
    return {
        "name": name,
        "status": "Unknown",
        "status_url": status_url,
        "issue_link": "Refer to status page as no specific link is available"
    }


# Dify status
def get_dify_status() -> Dict[str, Any]:
    """
    Get Dify API status using Chrome driver.
    
    Operational Status Logic:
    - Uses Chrome driver to fetch the Dify status page
    - Waits for app-root element to load, then searches for expandable elements
    - Clicks on expandable elements to reveal hidden content
    - Searches for <div class="page-status status-none"> elements
    - Checks if any h2 contains "all systems operational"
    - If found: Status = "Operational"
    - If not found: Status = "Disrupted"
    - If Chrome driver fails or element not found: Status = "Unknown"
    
    Returns:
        Dict containing status information
    """
    name = "Dify.AI API Status"
    status_url = 'https://dify.statuspage.io/'
    
    # Use dedicated Dify Chrome driver instance to prevent interference
    global _chrome_driver_dify
    driver = None
    
    try:
        # Check if we already have a Dify driver instance
        if _chrome_driver_dify is not None:
            try:
                # Test if the existing driver is still functional
                _chrome_driver_dify.current_url
                driver = _chrome_driver_dify
                logger.info("Reusing existing Dify Chrome driver instance")
            except Exception:
                # Driver is no longer functional, create a new one
                logger.info("Existing Dify driver is no longer functional, creating new one")
                _chrome_driver_dify = None
        
        if _chrome_driver_dify is None:
            logger.info("Creating new Chrome driver for Dify status")
            
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
                logger.info("Attempting to use undetected_chromedriver for Dify")
                _chrome_driver_dify = uc.Chrome(
                    options=chrome_options, 
                    use_subprocess=True
                )
                logger.info("Successfully created undetected_chromedriver instance for Dify")
            except Exception as uc_error:
                logger.warning(f"undetected_chromedriver failed for Dify: {uc_error}")
                logger.info("Falling back to ChromeDriverManager for Dify")
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
                    _chrome_driver_dify = webdriver.Chrome(
                        service=Service(driver_manager.install()), 
                        options=options
                    )
                    logger.info("Successfully created ChromeDriverManager instance for Dify")
                except Exception as cm_error:
                    logger.error(f"ChromeDriverManager also failed for Dify: {cm_error}")
                    logger.warning("All Chrome methods failed for Dify")
                    _chrome_driver_dify = None
        
        driver = _chrome_driver_dify
        
        if driver is not None:
            logger.info("Using Chrome driver for Dify status")
            # Navigate to the status page
            driver.get(status_url)
            # Wait for the page to load
            wait = WebDriverWait(driver, 15)
            
            # Wait for the main app-root element to be present first
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "app-root")))
            logger.info("Dify: Found app-root element, now looking for expandable elements")
            
            # Try to find and click expandable elements to reveal the status
            try:
                # Look for clickable elements that might expand the status section
                expandable_selectors = [
                    "app-root",
                    "div[class*='page-status']",
                    "div[class*='status-none']"
                ]
                
                for selector in expandable_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                logger.info(f"Dify: Found expandable element: {selector}")
                                driver.execute_script("arguments[0].click();", element)
                                time.sleep(1)  # Wait for expansion
                                break
                    except Exception as e:
                        logger.debug(f"Selector {selector} not found or clickable: {e}")
                        continue
                
                # Additional wait for content to expand after clicking
                time.sleep(1)
                
            except Exception as e:
                logger.warning(f"Could not find expandable elements: {e}")
            
            # Check for page-status status-none elements and h2 text
            try:
                # Wait for the specific status element to be present
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.page-status.status-none")))
                logger.info("Found page-status status-none element after expansion")
                
                # Get the element and find h2 elements
                status_element = driver.find_element(By.CSS_SELECTOR, "div.page-status.status-none")
                h2_elements = status_element.find_elements(By.TAG_NAME, "h2")
                
                is_operational = False
                
                # Check h2 elements for the text content
                for h2 in h2_elements:
                    text_content = h2.text.strip().lower()
                    logger.info(f"Dify status text content from h2: {text_content}")
                    
                    key_phrase = "all systems operational"
                    if key_phrase in text_content:
                        logger.info(f"Dify: Found required key phrase {key_phrase} to indicate no issue")
                        is_operational = True
                        break
                
                if not is_operational:
                    logger.info("Dify: No required key phrase found - status is Disrupted")
                
                return {
                    "name": name,
                    "status": "Operational" if is_operational else "Disrupted",
                    "status_url": status_url,
                    "issue_link": "Refer to status page as no specific link is available"
                }
                
            except Exception as e:
                logger.warning(f"page-status status-none element not found after expansion: {e}")
    
    except Exception as e:
        logger.error(f"Error fetching Dify status: {e}")
    
    return {
        "name": name,
        "status": "Unknown",
        "status_url": status_url,
        "issue_link": "Refer to status page as no specific link is available"
    }

def get_gemini_status() -> Dict[str, Any]:
    """
    Get Google Gemini API status using Chrome driver.
    
    Operational Status Logic:
    - Uses Chrome driver to fetch the Gemini status page
    - Waits for app-root element to load, then searches for expandable elements
    - Clicks on expandable elements to reveal hidden content
    - Searches for <div class="status-large operational"> elements
    - Checks if any span contains "all systems operational"
    - If found: Status = "Operational"
    - If not found: Status = "Disrupted"
    - If Chrome driver fails or element not found: Status = "Unknown"
    
    Returns:
        Dict containing status information
    """
    name = "Google AI Studio and Gemini API Status"
    status_url = 'https://aistudio.google.com/status'
    
    # Use dedicated Gemini Chrome driver instance to prevent interference
    global _chrome_driver_gemini
    driver = None
    
    try:
        # Check if we already have a Gemini driver instance
        if _chrome_driver_gemini is not None:
            try:
                # Test if the existing driver is still functional
                _chrome_driver_gemini.current_url
                driver = _chrome_driver_gemini
                logger.info("Reusing existing Gemini Chrome driver instance")
            except Exception:
                # Driver is no longer functional, create a new one
                logger.info("Existing Gemini driver is no longer functional, creating new one")
                _chrome_driver_gemini = None
        
        if _chrome_driver_gemini is None:
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
                logger.info("Attempting to use undetected_chromedriver for Gemini")
                _chrome_driver_gemini = uc.Chrome(
                    options=chrome_options, 
                    use_subprocess=True
                )
                logger.info("Successfully created undetected_chromedriver instance for Gemini")
            except Exception as uc_error:
                logger.warning(f"undetected_chromedriver failed for Gemini: {uc_error}")
                logger.info("Falling back to ChromeDriverManager for Gemini")
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
                    _chrome_driver_gemini = webdriver.Chrome(
                        service=Service(driver_manager.install()), 
                        options=options
                    )
                    logger.info("Successfully created ChromeDriverManager instance for Gemini")
                except Exception as cm_error:
                    logger.error(f"ChromeDriverManager also failed for Gemini: {cm_error}")
                    logger.warning("All Chrome methods failed for Gemini")
                    _chrome_driver_gemini = None
        
        driver = _chrome_driver_gemini
        
        if driver is not None:
            logger.info("Using Chrome driver for Gemini status")
            # Navigate to the status page
            driver.get(status_url)
            # Wait for the page to load
            wait = WebDriverWait(driver, 15)
            
            # Wait for the main app-root element to be present first
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "app-root")))
            logger.info("Gemini: Found app-root element, now looking for expandable elements")
            
            # Try to find and click expandable elements to reveal the status
            try:
                # Look for clickable elements that might expand the status section
                # Following the hierarchy: app-root > ms-status-page > div > div.status-page-container > div.status-large
                expandable_selectors = [
                    "app-root",
                    "ms-status-page",
                    "div[class*='status-page-container']",
                    "div[class*='status-large']",
                ]
                
                for selector in expandable_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                logger.info(f"Gemini: Found expandable element: {selector}")
                                driver.execute_script("arguments[0].click();", element)
                                time.sleep(1)  # Wait for expansion
                                break
                    except Exception as e:
                        logger.debug(f"Selector {selector} not found or clickable: {e}")
                        continue
                
                # Additional wait for content to expand after clicking
                time.sleep(1)
                
            except Exception as e:
                logger.warning(f"Could not find expandable elements: {e}")
            
            # Check for its second child span to see if there is text "All Systems Operational" using lowercase check
            try:
                # Wait for the specific status element to be present
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.status-large")))
                logger.info("Found status-large element after expansion")
                
                # Get the element and find all spans
                status_element = driver.find_element(By.CSS_SELECTOR, "div.status-large")
                spans = status_element.find_elements(By.TAG_NAME, "span")
                
                is_operational = False

                # Check the second span (index 1) for the text content
                if len(spans) >= 2:
                    text_content = spans[1].text.strip().lower()
                    logger.info(f"Gemini status text content from second span: {text_content}")

                    key_phrase = "all systems operational"
                    if key_phrase in text_content:
                        logger.info(f"Gemini: Found required key phrase {key_phrase} to indicate no issue")
                        is_operational = True
                    else:
                        logger.info("Gemini: No required key phrase found - status is Disrupted")
                    
                return {
                    "name": name,
                    "status": "Operational" if is_operational else "Disrupted",
                    "status_url": status_url,
                        "issue_link": "Refer to status page as no specific link is available"
                    }
            except Exception as e:
                logger.warning(f"status-large operational element not found after expansion: {e}")
    
        except Exception as e:
            logger.error(f"Error fetching Gemini status: {e}")
    
    return {
        "name": name,
        "status": "Unknown",
        "status_url": status_url,
        "issue_link": "Refer to status page as no specific link is available"
    }

# Add get perplexity status
async def get_perplexity_status() -> Dict[str, Any]:
    """
    Get Perplexity API status from their RSS feed.
    
    Operational Status Logic:
    - Fetches the latest entry from Perplexity's RSS feed
    - Checks if the description contains "resolved" AND does not contain "api outage"
    - If both conditions met: Status = "Operational"
    - If not: Status = "Disrupted"
    - If RSS parsing fails: Status = "Unknown"

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
    
    Operational Status Logic:
    - Fetches the latest entry from Anthropic's RSS feed
    - Checks if the description contains "resolved"
    - If found: Status = "Operational"
    - If not found: Status = "Disrupted"
    - If RSS parsing fails: Status = "Unknown"
    
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
        "issue_link": "Refer to status page as no specific link is available"
        # "last_update": "N/A",
        # "title": "Error",
        # "description": "Unable to fetch status"
    }


# Cloud related status using single RSS source
async def get_gcp_status() -> Dict[str, Any]:
    """
    Get Google Cloud Platform status (Global).
    
    Operational Status Logic:
    - Fetches the latest entry from GCP's Atom feed
    - Checks if the title contains "resolved:"
    - If found: Status = "Operational"
    - If not found: Status = "Disrupted"
    - If feed parsing fails: Status = "Unknown"
    
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
            logger.info("Found feed in GCP, if latest feed shows resolved, means there are no issues")
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
                "issue_link": "Refer to status page as no specific link is available", # No specific issue link provided in the status page
            }
    except Exception as e:
        logger.error(f"Error fetching GCP status: {e}")
    
    return {
        "name": name,
        "status": "Unknown",
        "status_url": status_url,
        "issue_link": "Refer to status page as no specific link is available"
    }

async def get_azure_status() -> Dict[str, Any]:
    """
    Get Microsoft Azure status (US).
    
    Operational Status Logic:
    - Fetches entries from Azure's RSS feed
    - If feed entries exist: Status = "Disrupted" (indicates ongoing issues)
    - If no feed entries: Status = "Operational" (no incidents reported)
    - If feed parsing fails: Status = "Unknown"
    
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
            logger.info("Found feed in Azure, indicates ongoing issues")
    
            return {
                "name": name,
                "status": "Disrupted",
                "status_url": status_url,
                "issue_link": "Refer to status page as no specific link is available", # No specific issue link provided in the status page
            }
        # No feed found, assume operational
        else:
            logger.info("Azure: No feed found, indicates normal status")
            return {
                "name": name,
                "status": "Operational",
                "status_url": status_url,
                "issue_link": "Refer to status page as no specific link is available", # No specific issue link provided in the status page
            }
    except Exception as e:
        logger.error(f"Error fetching Azure status: {e}")

    return {
        "name": name,
        "status": "Unknown",
        "status_url": status_url,
        "issue_link": "Refer to status page as no specific link is available"
    }

async def get_aws_status() -> Dict[str, Any]:
    """
    Get AWS service status from AWS Global Health Dashboard.
    
    Operational Status Logic:
    - Fetches entries from AWS's RSS feed
    - If feed entries exist: Status = "Disrupted" (indicates ongoing issues)
    - If no feed entries: Status = "Operational" (no incidents reported)
    - If feed parsing fails: Status = "Unknown"
    
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
            logger.info("Found feed in AWS, indicates ongoing issues")

            return {
                "name": name,
                "status": "Disrupted",
                "status_url": status_url,
                "issue_link": "Refer to status page as no specific link is available", # No specific issue link provided in the status page
            }
        # No feed found, assume operational
        else:
            logger.info("AWS: No feed found, indicates normal status")
            return {
                "name": name,
                "status": "Operational",
                "status_url": status_url,
                "issue_link": "Refer to status page as no specific link is available", # No specific issue link provided in the status page
            }

    except Exception as e:
        logger.error(f"Error fetching AWS status: {e}")
    
    return {
        "name": name,
        "status": "Unknown",
        "status_url": status_url,
        "issue_link": "Refer to status page as no specific link is available"
    }


def get_alicloud_status() -> Dict[str, Any]:
    """
    Get Alibaba Cloud status from their status page using Chrome driver.
    
    Operational Status Logic:
    - Uses Chrome driver to fetch the Alibaba Cloud status page
    - Waits for main container to load, then searches for expandable elements
    - Clicks on expandable elements (buttons, toggles) to reveal hidden content
    - Searches for <div class="cms-title-noEvent-child"> elements after expansion
    - If found: Status = "Operational" (no incidents)
    - If not found: Status = "Disrupted" (incidents present)
    - If Chrome driver fails or element not found: Status = "Unknown"
    
    Returns:
        Dict containing status information
    """
    name = "Alibaba Cloud Health Status"
    status_url = 'https://status.alibabacloud.com'
    
    # Use dedicated Alibaba Cloud Chrome driver instance to prevent interference
    global _chrome_driver_alicloud
    driver = None
    
    try:
        # Check if we already have an Alibaba Cloud driver instance
        if _chrome_driver_alicloud is not None:
            try:
                # Test if the existing driver is still functional
                _chrome_driver_alicloud.current_url
                driver = _chrome_driver_alicloud
                logger.info("Reusing existing Alibaba Cloud Chrome driver instance")
            except Exception:
                # Driver is no longer functional, create a new one
                logger.info("Existing Alibaba Cloud driver is no longer functional, creating new one")
                _chrome_driver_alicloud = None
        
        if _chrome_driver_alicloud is None:
            logger.info("Creating new Chrome driver for Alibaba Cloud status")
            
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
                logger.info("Attempting to use undetected_chromedriver for Alibaba Cloud")
                _chrome_driver_alicloud = uc.Chrome(
                    options=chrome_options, 
                    use_subprocess=True
                )
                logger.info("Successfully created undetected_chromedriver instance for Alibaba Cloud")
            except Exception as uc_error:
                logger.warning(f"undetected_chromedriver failed for Alibaba Cloud: {uc_error}")
                logger.info("Falling back to ChromeDriverManager for Alibaba Cloud")
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
                    _chrome_driver_alicloud = webdriver.Chrome(
                        service=Service(driver_manager.install()), 
                        options=options
                    )
                    logger.info("Successfully created ChromeDriverManager instance for Alibaba Cloud")
                except Exception as cm_error:
                    logger.error(f"ChromeDriverManager also failed for Alibaba Cloud: {cm_error}")
                    logger.warning("All Chrome methods failed for Alibaba Cloud")
                    _chrome_driver_alicloud = None
        
        driver = _chrome_driver_alicloud
        
        if driver is not None:
            logger.info("Using Chrome driver for Alibaba Cloud status")
            # Navigate to the status page
            driver.get(status_url)
            # Wait for the page to load
            wait = WebDriverWait(driver, 15)
            
            # Wait for the main container to be present first
            wait.until(EC.presence_of_element_located((By.ID, "container")))
            logger.info("Found main container, now looking for expandable elements")
            
            # Try to find and click expandable elements to reveal the status
            try:
                # Look for clickable elements that might expand the status section
                # Common patterns: buttons, links, or divs with click handlers
                expandable_selectors = [
                    ".cms-title-con-tt",  # Based on your hierarchy description
                    ".cms-title-bt"       # Based on your hierarchy description
                ]
                
                for selector in expandable_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                logger.info(f"Found expandable element: {selector}")
                                driver.execute_script("arguments[0].click();", element)
                                time.sleep(1)  # Wait for expansion
                                break
                    except Exception as e:
                        logger.debug(f"Selector {selector} not found or clickable: {e}")
                        continue
                
                # Additional wait for content to expand after clicking
                time.sleep(2)
                
            except Exception as e:
                logger.warning(f"Could not find expandable elements: {e}")
            
            # Now wait for the specific status element to be present
            try:
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "cms-title-noEvent-child")))
                logger.info("Found cms-title-noEvent-child element after expansion")
                
                # Get the element and check its text content
                element = driver.find_element(By.CLASS_NAME, "cms-title-noEvent-child")
                is_operational = False
                # Use Selenium WebElement's text property
                text_content = element.text.strip().lower()
                logger.info(f"Alibaba Cloud text content: {text_content}")
                
                key_phrase = "no incident, everything is normal"
                if key_phrase in text_content:
                    logger.info(f"Alibaba Cloud: Found required key phrase {key_phrase} to indicate no issue")
                    is_operational = True
                else:
                    logger.info("Alibaba Cloud: No required key phrase found - status is Disrupted")
                
                return {
                    "name": name,
                    "status": "Operational" if is_operational else "Disrupted",
                    "status_url": status_url,
                    "issue_link": "Refer to status page as no specific link is available"
                }
                
            except Exception as e:
                logger.error(f"Error parsing Alibaba Cloud status: {e}")
                return {
                    "name": name,
                    "status": "Unknown",
                    "status_url": status_url,
                    "issue_link": "Refer to status page as no specific link is available"
                }
        
    except Exception as e:
        logger.error(f"Error getting Alibaba Cloud status from url: {status_url}. Error: {e}")
    
    # If we reach here, Chrome method failed
    logger.warning("Chrome method failed for Alibaba Cloud status, returning error status")
    return {
        "name": name,
        "status": "Unknown",
        "status_url": status_url,
        "issue_link": "Refer to status page as no specific link is available"
    }