# LLM & Cloud API Status Dashboard

A 1 min refresh real-time Streamlit dashboard for monitoring LLM API and cloud service statuses with advanced async loading and graceful shutdown capabilities.

## Features

- **LLM API Monitoring**: OpenAI, DeepSeek, Gemini, Anthropic, Perplexity, and LangSmith
- **Cloud Services Monitoring**: AWS, Google Cloud Platform, and Microsoft Azure
- **Async Status Loading**: Non-blocking concurrent status checks using asyncio
- **Auto-refresh**: Every 60 seconds
- **Visual Status Indicators**: Color-coded status cards with source links
- **Summary Metrics**: Overall uptime percentages and service counts
- **Simple Controls**: Clean UI with essential refresh functionality
- **Chrome Integration**: Singleton Chrome driver for Gemini status scraping

## Environment pre-requisites
You need to have a python virtual env or Anaconda or Miniconda setup in order to run. There is no .env file required as no credentials are involved.

## Browser Requirements

### Chrome Browser (Required for Gemini)
The dashboard uses Chrome browser for scraping Google AI Studio status page. Chrome is required for Gemini status monitoring.

**Note**: The dashboard uses a singleton Chrome driver pattern to ensure only one browser instance runs at a time, even with async operations.

### Chrome Installation
Make sure you have Chrome browser installed on your system. The dashboard will automatically detect and use the installed Chrome version.

## Installation 

Please do not clone this repo into your OneDrive directory or , network drives, or different disk partitions. It would result in the following warning/error (os error 396):
```
warning: Failed to hardlink files; falling back to full copy. This may lead to degraded performance.
         If the cache and target directories are on different filesystems, hardlinking may not be supported.
         If this is intentional, set `export UV_LINK_MODE=copy` or use `--link-mode=copy` to suppress this warning.
error: Failed to install: blinker-1.9.0-py3-none-any.whl (blinker==1.9.0)
<redacted folder path>: The cloud operation cannot be performed on a file with incompatible hardlinks. (os error 396)
```
If that is not possible, you have to follow Option 2 below instead.
### Option 1: Using uv (Recommended)

1. Install uv if you haven't already:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# or
pip install uv
```

2. Setup the project:
```bash
uv sync
```

3. Run the dashboard:
```bash
uv run streamlit run app_main.py
```

### Option 2: Using pip (Traditional)

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Run the dashboard:
```bash
streamlit run app_main.py
```

## Usage

The dashboard will automatically:
- Fetch status information from various API endpoints using async operations
- Display real-time status with color-coded indicators and source links
- Show summary metrics for overall system health
- Auto-refresh every 60 seconds
- Run all status checks concurrently for faster loading

### Dashboard Controls

- **🔄 Refresh Now**: Manual refresh button
- **⏰ Last Refresh**: Shows last update time in GMT+8
- **⏳ Countdown**: Shows time until next auto-refresh

### Stopping the Dashboard

To stop the dashboard:
- **Browser Tab**: Close the browser tab
- **Terminal**: Press Ctrl+C in the terminal (for development)
- **Streamlit**: Use Streamlit's built-in stop functionality

## Status Indicators

- 🟢 **Green**: Service is operational
- 🔴 **Red**: Issues detected  
- 🟡 **Yellow**: Status unknown or error fetching data

### Status Card Information

Each status card includes:
- **Service Name**: Clear identification of the service
- **Status**: Current operational status
- **Source Link**: Direct link to the official status page
- **Last Update**: Timestamp of the last status check
- **Issue Details**: Additional information for disrupted services
- **Issue Links**: Direct links to incident reports (when available)

## Technical Architecture

### Async Status Loading
- **Concurrent Execution**: All status checks run simultaneously using `asyncio.gather()`
- **Non-blocking**: Chrome operations run in thread pool to avoid blocking
- **Error Resilience**: Individual service failures don't affect others
- **Performance**: ~50% faster than sequential loading

### Chrome Driver Management
- **Singleton Pattern**: Only one Chrome browser instance across all operations
- **Thread-Safe**: Uses threading locks instead of asyncio locks
- **Resource Efficient**: Automatic cleanup and driver management
- **Fallback Handling**: Graceful degradation when Chrome is unavailable

### Resource Management
- **Automatic Cleanup**: Chrome drivers are automatically managed
- **Simple Architecture**: Clean, straightforward implementation
- **Standard Streamlit**: Uses standard Streamlit patterns for reliability

## Development

### Available Commands (using Make)

```bash
make help          # Show all available commands
make setup         # Setup uv environment and install dependencies
make run           # Run the dashboard
make run-dev       # Run dashboard in development mode (auto-reload)
make test          # Run tests
make lint          # Run linting (flake8 + mypy)
make format        # Format code with black
make clean         # Clean up generated files
make update        # Update dependencies
make lock          # Generate/update lock file
make shell         # Activate uv shell
```

### Project Structure

- `app_main.py`: Main Streamlit application with async status loading
- `helpers.py`: Helper functions for fetching API statuses (async/sync)
- `pyproject.toml`: uv project configuration
- `requirements.txt`: Traditional pip dependencies (for compatibility)
- `Makefile`: Development commands
- `setup_uv.py`: Setup script for uv environment
- `run_dashboard_uv.py`: Run script using uv

## Dependencies

### Core Dependencies
- `streamlit>=1.28.0`: Web dashboard framework
- `requests>=2.31.0`: HTTP requests for API status
- `beautifulsoup4>=4.12.0`: HTML parsing
- `feedparser>=6.0.10`: RSS/Atom feed parsing
- `pytz>=2023.3`: Timezone handling

### Chrome Dependencies
- `selenium==4.32.0`: WebDriver automation
- `undetected-chromedriver==3.5.5`: Chrome driver management
- `webdriver-manager==4.0.2`: Automatic driver management

## Notes

- The dashboard uses RSS feeds and status pages to determine service availability
- Some services may show "Unknown" status if their status pages are not accessible or layout has changed
- Chrome browser is required for Gemini status monitoring
- The dashboard uses async operations for better performance and user experience
- All status checks run concurrently for faster loading times
- Simple and clean user interface with essential functionality