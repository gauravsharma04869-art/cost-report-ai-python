FROM python:3.13-slim

WORKDIR /app

# Install system dependencies for PDF parsing
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (for Docker layer caching)
COPY pyproject.toml README.md ./

# Install Python dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Copy the rest of the application
COPY src/ ./src/

# Create required directories
RUN mkdir -p data/samples data/lineage data/output

# Generate sample data on build
RUN python -c "
from src.cli.main import cli
from click.testing import CliRunner
runner = CliRunner()
for fac in ['hospital', 'snf', 'hospice', 'hha']:
    runner.invoke(cli, ['sample', '--facility', fac, '--rows', '30'])
print('Sample data generated for all facility types')
"

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/v1/health')" || exit 1

# App Runner expects port 8080
EXPOSE 8080

# Start the API server
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
