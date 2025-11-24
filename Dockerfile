FROM python:3.10-slim

# Create working directory
WORKDIR /app

# Copy dependencies first
COPY requirements.txt .

# Install build tools only in builder
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Security: create non-root user FIRST
RUN useradd -m appuser

# Create directory and set ownership while still root
RUN mkdir -p /app/data && chown -R appuser:appuser /app

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Switch to non-root user
USER appuser

# Export port
EXPOSE 8000

# Run app
CMD ["./entrypoint.sh"]