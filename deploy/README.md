# MCP Base64 Server Deployment Guide

This directory contains deployment configurations and scripts for the MCP Base64 Server.

## Quick Start

### Local Development

```bash
# Start with stdio transport (default)
./start.sh

# Start with HTTP transport and API server
./start.sh -t http -s

# Start with debug logging
./start.sh -l DEBUG
```

### Docker Deployment

```bash
# Start with Docker Compose
./docker-deploy.sh start

# Start in development mode
./docker-deploy.sh start --dev

# Start in production mode
./docker-deploy.sh start --prod --detach

# View logs
./docker-deploy.sh logs

# Stop services
./docker-deploy.sh stop

# Clean up
./docker-deploy.sh clean
```

## Deployment Options

### 1. Local Python Deployment

**Requirements:**
- Python 3.9+
- pip
- Virtual environment (recommended)

**Setup:**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start server
python main.py --transport stdio
```

### 2. Docker Deployment

**Requirements:**
- Docker
- Docker Compose

**Configuration:**
1. Copy `.env.example` to `.env` and modify as needed
2. Choose appropriate docker-compose service:
   - `mcp-base64-server`: Production service
   - `mcp-base64-server-dev`: Development service with volume mounts
   - `mcp-base64-stdio`: Stdio-only service for MCP clients

**Commands:**
```bash
# Build and start
docker-compose up --build mcp-base64-server

# Start in background
docker-compose up -d mcp-base64-server

# View logs
docker-compose logs -f mcp-base64-server

# Stop
docker-compose down
```

### 3. Production Deployment with Nginx

**Setup:**
1. Configure SSL certificates in `deploy/ssl/`
2. Update `deploy/nginx.conf` with your domain
3. Start with monitoring stack:

```bash
docker-compose up -d mcp-base64-server nginx prometheus grafana
```

**Access:**
- Web Interface: http://localhost
- API Endpoints: http://localhost/encode, http://localhost/decode
- MCP Transport: http://localhost/mcp
- Monitoring: http://localhost:3001 (Grafana)

## Configuration Files

### Environment Variables (.env)

Copy `.env.example` to `.env` and configure:

```bash
# Server settings
TRANSPORT_TYPE=http
HTTP_API_PORT=8080
MCP_HTTP_PORT=3000

# Logging
LOG_LEVEL=INFO

# Security
CORS_ORIGINS=*
```

### YAML Configuration

- `config.yaml`: Default configuration
- `config.prod.yaml`: Production-optimized settings

### Docker Configuration

- `Dockerfile`: Multi-stage build for optimized images
- `docker-compose.yml`: Complete deployment stack
- `deploy/nginx.conf`: Reverse proxy configuration
- `deploy/prometheus.yml`: Monitoring configuration

## Deployment Scripts

### start.sh / start.bat

Cross-platform startup script with options:

```bash
./start.sh [OPTIONS]

Options:
  -t, --transport TYPE     Transport type (stdio/http)
  -s, --enable-http-server Enable HTTP API server
  -l, --log-level LEVEL    Log level (DEBUG/INFO/WARNING/ERROR)
  -c, --config FILE        Configuration file path
  -p, --http-port PORT     HTTP API server port
  -m, --mcp-port PORT      MCP HTTP transport port
```

### docker-deploy.sh

Docker deployment automation:

```bash
./docker-deploy.sh [ACTION] [OPTIONS]

Actions:
  start     Start services
  stop      Stop services
  restart   Restart services
  build     Build images
  logs      Show logs
  status    Show status
  clean     Clean up

Options:
  --dev     Development mode
  --prod    Production mode
  --build   Force rebuild
  -d        Detached mode
```

## Monitoring and Logging

### Logging

Logs are written to:
- Console output (configurable format)
- File: `logs/mcp-base64-server.log` (with rotation)

Log levels: DEBUG, INFO, WARNING, ERROR

### Monitoring Stack

When using the full docker-compose stack:

- **Prometheus**: Metrics collection (port 9090)
- **Grafana**: Dashboards and visualization (port 3001)
- **Redis**: Caching and session storage (port 6379)

### Health Checks

- HTTP API: `GET /health`
- Docker: Built-in health checks
- Prometheus: Service discovery and monitoring

## Security Considerations

### Production Checklist

- [ ] Configure specific CORS origins (not `*`)
- [ ] Enable SSL/TLS with valid certificates
- [ ] Set up proper firewall rules
- [ ] Configure rate limiting
- [ ] Use non-root user in containers
- [ ] Regularly update dependencies
- [ ] Monitor logs for suspicious activity
- [ ] Set up backup procedures

### SSL/TLS Setup

1. Obtain SSL certificates
2. Place in `deploy/ssl/` directory
3. Update nginx configuration
4. Enable HTTPS in docker-compose

```bash
# Generate self-signed certificates for testing
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout deploy/ssl/server.key \
  -out deploy/ssl/server.crt
```

## Troubleshooting

### Common Issues

1. **Port conflicts**: Check if ports 8080, 3000 are available
2. **Permission errors**: Ensure proper file permissions
3. **Docker issues**: Check Docker daemon status
4. **Python dependencies**: Verify all packages are installed

### Debug Mode

Enable debug logging:
```bash
./start.sh -l DEBUG
```

Or set environment variable:
```bash
export LOG_LEVEL=DEBUG
```

### Container Logs

```bash
# View all logs
docker-compose logs

# Follow specific service logs
docker-compose logs -f mcp-base64-server

# View last 100 lines
docker-compose logs --tail=100 mcp-base64-server
```

### Performance Tuning

1. **Worker processes**: Adjust `MAX_WORKERS` in environment
2. **Memory limits**: Set Docker memory constraints
3. **Connection pooling**: Configure nginx upstream settings
4. **Caching**: Enable Redis for session/response caching

## Backup and Recovery

### Data Backup

```bash
# Backup configuration
tar -czf backup-config-$(date +%Y%m%d).tar.gz config.yaml config.prod.yaml .env

# Backup logs
tar -czf backup-logs-$(date +%Y%m%d).tar.gz logs/

# Backup Docker volumes
docker run --rm -v mcp-base64-server_redis-data:/data -v $(pwd):/backup alpine tar czf /backup/redis-backup-$(date +%Y%m%d).tar.gz /data
```

### Recovery

```bash
# Restore configuration
tar -xzf backup-config-YYYYMMDD.tar.gz

# Restart services
./docker-deploy.sh restart
```

## Scaling

### Horizontal Scaling

1. Use Docker Swarm or Kubernetes
2. Configure load balancer (nginx upstream)
3. Shared storage for logs and configuration
4. Database for session management

### Vertical Scaling

1. Increase container resources
2. Adjust worker processes
3. Optimize Python application settings

## Support

For issues and questions:
1. Check logs for error messages
2. Verify configuration files
3. Test with minimal configuration
4. Check network connectivity
5. Review security settings