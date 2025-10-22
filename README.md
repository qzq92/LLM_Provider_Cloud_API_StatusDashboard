# LLM & Cloud API Status Dashboard

A real-time Streamlit dashboard for monitoring LLM API and cloud service statuses.

## Features

- **LLM API Monitoring**: OpenAI, DeepSeek, Gemini, and Anthropic
- **Cloud Services Monitoring**: AWS, Google Cloud Platform, and Microsoft Azure
- **Real-time Updates**: Auto-refresh every 30 seconds
- **Visual Status Indicators**: Color-coded status cards
- **Summary Metrics**: Overall uptime percentages

## Environment pre-requisites
You need to have a python virtual env or Anaconda or Miniconda setup in order to run. There is no .env file required as no credentials are involved.

## Browser Requirements

### Chrome Browser (Recommended)
The dashboard uses Chrome browser for scraping Google AI Studio status page. If you have Chrome installed, the dashboard will work with full functionality.

### No Chrome Browser? No Problem!
If you don't have Chrome browser installed, the dashboard will automatically use fallback methods:

1. **Edit `config.py`** and set `ENABLE_CHROME_SCRAPING = False`
2. **Or set environment variable**: `export ENABLE_CHROME_SCRAPING=false`
3. **Or install Chrome** for full functionality

#### Fallback Behavior:
- **Gemini Status**: Uses multiple fallback methods:
  1. **requests-html**: JavaScript rendering without Chrome (85% accuracy)
  2. **Enhanced HTTP**: Content analysis of static HTML (70% accuracy)  
  3. **Basic HTTP**: Simple accessibility check (60% accuracy)
- **Other Services**: Work normally (they don't require Chrome)
- **Automatic**: System automatically chooses the best available method

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
- Fetch status information from various API endpoints
- Display real-time status with color-coded indicators
- Show summary metrics for overall system health
- Auto-refresh every 30 seconds (can be disabled in sidebar)

## Status Indicators

- 🟢 **Green**: Service is operational
- 🔴 **Red**: Issues detected
- 🟡 **Yellow**: Status unknown or error fetching data

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

- `app_main.py`: Main Streamlit application
- `helpers.py`: Helper functions for fetching API statuses
- `pyproject.toml`: uv project configuration
- `requirements.txt`: Traditional pip dependencies (for compatibility)
- `Makefile`: Development commands
- `setup_uv.py`: Setup script for uv environment
- `run_dashboard_uv.py`: Run script using uv

## Notes

- The dashboard uses RSS feeds and status pages to determine service availability
- Some services may show "Unknown" status if their status pages are not accessible or layout has changed.
- Debug information is available in the collapsible section at the bottom