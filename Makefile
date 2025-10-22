.PHONY: help install run setup clean test lint format

help: ## Show this help message
	@echo "LLM & Cloud API Status Dashboard - Available commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Setup uv environment and install dependencies
	@echo "🚀 Setting up uv environment..."
	uv sync
	@echo "✅ Setup complete!"

install: setup ## Alias for setup

run: ## Run the dashboard
	@echo "🚀 Starting dashboard..."
	uv run streamlit run app_main.py --server.port 8501 --server.address localhost

run-dev: ## Run dashboard in development mode
	@echo "🚀 Starting dashboard in development mode..."
	uv run streamlit run app_main.py --server.port 8501 --server.address localhost --server.runOnSave true

test: ## Run tests
	@echo "🧪 Running tests..."
	uv run pytest

lint: ## Run linting
	@echo "🔍 Running linting..."
	uv run flake8 .
	uv run mypy .

format: ## Format code
	@echo "🎨 Formatting code..."
	uv run black .

clean: ## Clean up generated files
	@echo "🧹 Cleaning up..."
	rm -rf .venv
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

update: ## Update dependencies
	@echo "🔄 Updating dependencies..."
	uv sync --upgrade

lock: ## Generate/update lock file
	@echo "🔒 Generating lock file..."
	uv lock

shell: ## Activate uv shell
	@echo "🐚 Activating uv shell..."
	uv shell

