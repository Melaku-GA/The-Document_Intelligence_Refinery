# Document Intelligence Refinery - Docker Configuration

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ src/
COPY scripts/ scripts/
COPY test/ test/
COPY docs/ docs/
COPY rubric/ rubric/
COPY Data/ Data/
COPY .refinery/ .refinery/

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Create output directories
RUN mkdir -p .refinery/profiles .refinery/chunks .refinery/pageindex .refinery/vectors

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python", "-m", "src.main"]

# Build command:
# docker build -t document-intelligence-refinery .

# Run command:
# docker run -v $(pwd)/Data:/app/Data -v $(pwd)/.refinery:/app/.refinery document-intelligence-refinery
