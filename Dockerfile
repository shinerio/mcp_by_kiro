# MCP Base64 Server Dockerfile
# Multi-stage build for optimized production image

# Build stage
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN groupadd -r mcpuser && useradd -r -g mcpuser mcpuser

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/mcpuser/.local

# Copy application code
COPY . .

# Set ownership of application files
RUN chown -R mcpuser:mcpuser /app

# Switch to non-root user
USER mcpuser

# Add local Python packages to PATH
ENV PATH=/home/mcpuser/.local/bin:$PATH

# Set Python path
ENV PYTHONPATH=/app

# Expose ports
# 8080 for HTTP API server
# 3000 for HTTP MCP transport
EXPOSE 8080 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default command - can be overridden
CMD ["python", "main.py", "--transport", "http", "--enable-http-server"]

# Labels for metadata
LABEL maintainer="MCP Base64 Server Team"
LABEL version="1.0.0"
LABEL description="MCP Base64 Server - Provides base64 encoding/decoding via MCP protocol"
LABEL org.opencontainers.image.source="https://github.com/your-org/mcp-base64-server"