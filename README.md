# LLM & Cloud API Status Dashboard

A real-time Streamlit dashboard for monitoring LLM API and cloud service statuses.

## Features

- **LLM API Monitoring**: OpenAI, DeepSeek, Gemini, and Anthropic
- **Cloud Services Monitoring**: AWS, Google Cloud Platform, and Microsoft Azure
- **Real-time Updates**: Auto-refresh every 30 seconds
- **Visual Status Indicators**: Color-coded status cards
- **Summary Metrics**: Overall uptime percentages

## Installation

### Option 1: Using uv (Recommended)

1. Install uv if you haven't already:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# or
pip install uv
```

2. Setup the project:
```bash
# Setup dependencies and generate lock file
make setup
# or
uv sync
```

3. Run the dashboard:
```bash
# Using make
make run

# Or directly with uv
uv run streamlit run app_main.py

# Or using the run script
python run_dashboard_uv.py
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