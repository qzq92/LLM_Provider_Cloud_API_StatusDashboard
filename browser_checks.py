"""
Browser-based status checks extracted from helpers.
"""
from typing import Dict, Any, Union
import logging
import threading
import time

import undetected_chromedriver as uc
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from status_payloads import build_operational_payload, build_unknown_payload

logger = logging.getLogger(__name__)

_STATE: Dict[str, Any] = {
    "chrome_driver_gemini": None,
    "chrome_driver_alicloud": None,
    "chrome_driver_dify": None,
}

BROWSER_TTL_OPERATIONAL_SECONDS = 120
BROWSER_TTL_DISRUPTED_SECONDS = 30
BROWSER_TTL_UNKNOWN_SECONDS = 20
_browser_status_cache: Dict[str, Dict[str, Any]] = {}
_browser_cache_lock = threading.Lock()
DRIVER_CHECK_ERRORS = (
    WebDriverException,
    TimeoutException,
    NoSuchElementException,
    RuntimeError,
    OSError,
    ValueError,
)
CLEANUP_BROWSER_ERRORS = (WebDriverException, RuntimeError, OSError, ValueError)


def get_cached_browser_status(cache_key: str) -> Union[Dict[str, Any], None]:
    """Return cached browser-derived status when entry TTL is still valid."""
    with _browser_cache_lock:
        cached_entry = _browser_status_cache.get(cache_key)
        if not cached_entry:
            return None
        age_seconds = time.monotonic() - cached_entry["timestamp"]
        ttl_seconds = cached_entry.get("ttl_seconds", BROWSER_TTL_OPERATIONAL_SECONDS)
        if age_seconds <= ttl_seconds:
            logger.info(
                "Using cached browser status for %s (age %.1fs / ttl %ss)",
                cache_key,
                age_seconds,
                ttl_seconds,
            )
            return cached_entry["data"]
        _browser_status_cache.pop(cache_key, None)
        return None


def _resolve_browser_ttl_seconds(status_data: Dict[str, Any]) -> int:
    """Map status value to adaptive browser-cache TTL seconds."""
    status_value = str(status_data.get("status", "Unknown")).strip().lower()
    if status_value == "operational":
        return BROWSER_TTL_OPERATIONAL_SECONDS
    if status_value == "disrupted":
        return BROWSER_TTL_DISRUPTED_SECONDS
    return BROWSER_TTL_UNKNOWN_SECONDS


def set_cached_browser_status(cache_key: str, status_data: Dict[str, Any]) -> None:
    """Store browser-derived status with status-sensitive TTL metadata."""
    ttl_seconds = _resolve_browser_ttl_seconds(status_data)
    with _browser_cache_lock:
        _browser_status_cache[cache_key] = {
            "timestamp": time.monotonic(),
            "data": status_data,
            "ttl_seconds": ttl_seconds,
        }


def cleanup_browser_resources() -> None:
    """Close all browser drivers managed by this module."""
    if _STATE["chrome_driver_gemini"] is not None:
        try:
            _STATE["chrome_driver_gemini"].quit()
            logger.info("Cleaned up Gemini Chrome driver")
        except CLEANUP_BROWSER_ERRORS as e:
            logger.warning("Error cleaning up Gemini Chrome driver: %s", e)
        finally:
            _STATE["chrome_driver_gemini"] = None

    if _STATE["chrome_driver_alicloud"] is not None:
        try:
            _STATE["chrome_driver_alicloud"].quit()
            logger.info("Cleaned up Alibaba Cloud Chrome driver")
        except CLEANUP_BROWSER_ERRORS as e:
            logger.warning("Error cleaning up Alibaba Cloud Chrome driver: %s", e)
        finally:
            _STATE["chrome_driver_alicloud"] = None

    if _STATE["chrome_driver_dify"] is not None:
        try:
            _STATE["chrome_driver_dify"].quit()
            logger.info("Cleaned up Dify Chrome driver")
        except CLEANUP_BROWSER_ERRORS as e:
            logger.warning("Error cleaning up Dify Chrome driver: %s", e)
        finally:
            _STATE["chrome_driver_dify"] = None


def get_dify_status() -> Dict[str, Any]:
    """Fetch Dify status page state using Selenium with caching."""
    name = "Dify.AI"
    status_url = "https://dify.statuspage.io/"
    cached_result = get_cached_browser_status("dify")
    if cached_result is not None:
        return cached_result

    driver = None
    try:
        if _STATE["chrome_driver_dify"] is not None:
            try:
                _STATE["chrome_driver_dify"].current_url
                driver = _STATE["chrome_driver_dify"]
                logger.info("Reusing existing Dify Chrome driver instance")
            except DRIVER_CHECK_ERRORS:
                logger.info("Existing Dify driver is no longer functional, creating new one")
                _STATE["chrome_driver_dify"] = None

        if _STATE["chrome_driver_dify"] is None:
            logger.info("Creating new Chrome driver for Dify status")
            chrome_options = Options()
            for arg in [
                "--headless",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-images",
                "--disable-javascript",
            ]:
                chrome_options.add_argument(arg)
            try:
                logger.info("Attempting to use undetected_chromedriver for Dify")
                _STATE["chrome_driver_dify"] = uc.Chrome(
                    options=chrome_options, use_subprocess=True
                )
            except DRIVER_CHECK_ERRORS as uc_error:
                logger.warning("undetected_chromedriver failed for Dify: %s", uc_error)
                options = webdriver.ChromeOptions()
                for arg in [
                    "--headless",
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-images",
                    "--disable-javascript",
                ]:
                    options.add_argument(arg)
                try:
                    driver_path = ChromeDriverManager().install()
                    logger.info("ChromeDriver available at: %s", driver_path)
                    _STATE["chrome_driver_dify"] = webdriver.Chrome(
                        service=Service(driver_path), options=options
                    )
                except DRIVER_CHECK_ERRORS as cm_error:
                    logger.error("ChromeDriverManager also failed for Dify: %s", cm_error)
                    _STATE["chrome_driver_dify"] = None

        driver = _STATE["chrome_driver_dify"]
        if driver is not None:
            driver.get(status_url)
            wait = WebDriverWait(driver, 10)
            try:
                for selector in ["div[class*='page-status']", "div[class*='status-none']"]:
                    try:
                        for element in driver.find_elements(By.CSS_SELECTOR, selector):
                            if element.is_displayed() and element.is_enabled():
                                driver.execute_script("arguments[0].click();", element)
                                time.sleep(0.3)
                                break
                    except DRIVER_CHECK_ERRORS as e:
                        logger.debug("Selector %s not found or clickable: %s", selector, e)
                time.sleep(0.3)
            except DRIVER_CHECK_ERRORS as e:
                logger.warning("Could not find expandable elements: %s", e)

            try:
                wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.page-status.status-none")
                    )
                )
                status_element = driver.find_element(
                    By.CSS_SELECTOR, "div.page-status.status-none"
                )
                is_operational = any(
                    "all systems operational" in h2.text.strip().lower()
                    for h2 in status_element.find_elements(By.TAG_NAME, "h2")
                )
                result = build_operational_payload(name, is_operational, status_url)
                set_cached_browser_status("dify", result)
                return result
            except DRIVER_CHECK_ERRORS as e:
                logger.warning(
                    "page-status status-none element not found after expansion: %s", e
                )
    except DRIVER_CHECK_ERRORS as e:
        logger.error("Error fetching Dify status: %s", e)

    result = build_unknown_payload(name, status_url)
    set_cached_browser_status("dify", result)
    return result


def get_gemini_status() -> Dict[str, Any]:
    """Fetch Gemini status page state using Selenium with caching."""
    name = "Google AI Studio and Gemini API Status"
    status_url = "https://aistudio.google.com/status"
    cached_result = get_cached_browser_status("gemini")
    if cached_result is not None:
        return cached_result

    driver = None
    try:
        if _STATE["chrome_driver_gemini"] is not None:
            try:
                _STATE["chrome_driver_gemini"].current_url
                driver = _STATE["chrome_driver_gemini"]
                logger.info("Reusing existing Gemini Chrome driver instance")
            except DRIVER_CHECK_ERRORS:
                logger.info("Existing Gemini driver is no longer functional, creating new one")
                _STATE["chrome_driver_gemini"] = None

        if _STATE["chrome_driver_gemini"] is None:
            chrome_options = Options()
            for arg in [
                "--headless",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-images",
                "--disable-javascript",
            ]:
                chrome_options.add_argument(arg)
            try:
                _STATE["chrome_driver_gemini"] = uc.Chrome(
                    options=chrome_options, use_subprocess=True
                )
            except DRIVER_CHECK_ERRORS as uc_error:
                logger.warning("undetected_chromedriver failed for Gemini: %s", uc_error)
                options = webdriver.ChromeOptions()
                for arg in [
                    "--headless",
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-images",
                    "--disable-javascript",
                ]:
                    options.add_argument(arg)
                try:
                    driver_path = ChromeDriverManager().install()
                    logger.info("ChromeDriver available at: %s", driver_path)
                    _STATE["chrome_driver_gemini"] = webdriver.Chrome(
                        service=Service(driver_path), options=options
                    )
                except DRIVER_CHECK_ERRORS as cm_error:
                    logger.error("ChromeDriverManager also failed for Gemini: %s", cm_error)
                    _STATE["chrome_driver_gemini"] = None

        driver = _STATE["chrome_driver_gemini"]
        if driver is not None:
            driver.get(status_url)
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "app-root")))
            try:
                for selector in [
                    "app-root",
                    "ms-status-page",
                    "div[class*='status-page-container']",
                    "div[class*='status-large']",
                ]:
                    try:
                        for element in driver.find_elements(By.CSS_SELECTOR, selector):
                            if element.is_displayed() and element.is_enabled():
                                driver.execute_script("arguments[0].click();", element)
                                time.sleep(0.3)
                                break
                    except DRIVER_CHECK_ERRORS as e:
                        logger.debug("Selector %s not found or clickable: %s", selector, e)
                time.sleep(0.3)
            except DRIVER_CHECK_ERRORS as e:
                logger.warning("Could not find expandable elements: %s", e)

            try:
                wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.status-large"))
                )
                status_element = driver.find_element(By.CSS_SELECTOR, "div.status-large")
                spans = status_element.find_elements(By.TAG_NAME, "span")
                is_operational = (
                    len(spans) >= 2
                    and "all systems operational" in spans[1].text.strip().lower()
                )
                result = build_operational_payload(name, is_operational, status_url)
                set_cached_browser_status("gemini", result)
                return result
            except DRIVER_CHECK_ERRORS as e:
                logger.warning("status-large operational element not found: %s", e)
    except DRIVER_CHECK_ERRORS as e:
        logger.error("Error fetching Gemini status: %s", e)

    result = build_unknown_payload(name, status_url)
    set_cached_browser_status("gemini", result)
    return result


def get_alicloud_status() -> Dict[str, Any]:
    """Fetch Alibaba Cloud status page state using Selenium with caching."""
    name = "Alibaba Cloud Health Status"
    status_url = "https://status.alibabacloud.com"
    cached_result = get_cached_browser_status("alicloud")
    if cached_result is not None:
        return cached_result

    driver = None
    try:
        if _STATE["chrome_driver_alicloud"] is not None:
            try:
                _STATE["chrome_driver_alicloud"].current_url
                driver = _STATE["chrome_driver_alicloud"]
            except DRIVER_CHECK_ERRORS:
                _STATE["chrome_driver_alicloud"] = None

        if _STATE["chrome_driver_alicloud"] is None:
            chrome_options = Options()
            for arg in [
                "--headless",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-images",
                "--disable-javascript",
            ]:
                chrome_options.add_argument(arg)
            try:
                _STATE["chrome_driver_alicloud"] = uc.Chrome(
                    options=chrome_options, use_subprocess=True
                )
            except DRIVER_CHECK_ERRORS as uc_error:
                logger.warning("undetected_chromedriver failed for Alibaba Cloud: %s", uc_error)
                options = webdriver.ChromeOptions()
                for arg in [
                    "--headless",
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-images",
                    "--disable-javascript",
                    "--no-sandbox",
                    "--remote-debugging-port=9222",
                ]:
                    options.add_argument(arg)
                try:
                    driver_path = ChromeDriverManager().install()
                    logger.info("ChromeDriver available at: %s", driver_path)
                    _STATE["chrome_driver_alicloud"] = webdriver.Chrome(
                        service=Service(driver_path), options=options
                    )
                except DRIVER_CHECK_ERRORS as cm_error:
                    logger.error(
                        "ChromeDriverManager also failed for Alibaba Cloud: %s", cm_error
                    )
                    _STATE["chrome_driver_alicloud"] = None

        driver = _STATE["chrome_driver_alicloud"]
        if driver is not None:
            driver.get(status_url)
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.ID, "container")))
            try:
                for selector in [".cms-title-con-tt", ".cms-title-bt"]:
                    try:
                        for element in driver.find_elements(By.CSS_SELECTOR, selector):
                            if element.is_displayed() and element.is_enabled():
                                driver.execute_script("arguments[0].click();", element)
                                time.sleep(0.3)
                                break
                    except DRIVER_CHECK_ERRORS as e:
                        logger.debug("Selector %s not found or clickable: %s", selector, e)
                time.sleep(0.5)
            except DRIVER_CHECK_ERRORS as e:
                logger.warning("Could not find expandable elements: %s", e)

            try:
                wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "cms-title-noEvent-child"))
                )
                element = driver.find_element(By.CLASS_NAME, "cms-title-noEvent-child")
                text_content = element.text.strip().lower()
                is_operational = "no incident, everything is normal" in text_content
                result = build_operational_payload(name, is_operational, status_url)
                set_cached_browser_status("alicloud", result)
                return result
            except DRIVER_CHECK_ERRORS as e:
                logger.error("Error parsing Alibaba Cloud status: %s", e)
    except DRIVER_CHECK_ERRORS as e:
        logger.error("Error getting Alibaba Cloud status from url %s: %s", status_url, e)

    result = build_unknown_payload(name, status_url)
    set_cached_browser_status("alicloud", result)
    return result
