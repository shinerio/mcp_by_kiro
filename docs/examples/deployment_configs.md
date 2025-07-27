# 部署配置示例

本文档提供了MCP Base64服务器在不同环境和场景下的部署配置示例，包括开发、测试、生产环境以及各种容器化部署方案。

## 目录

- [开发环境配置](#开发环境配置)
- [测试环境配置](#测试环境配置)
- [生产环境配置](#生产环境配置)
- [Docker部署](#docker部署)
- [Kubernetes部署](#kubernetes部署)
- [云平台部署](#云平台部署)
- [负载均衡配置](#负载均衡配置)
- [监控和日志配置](#监控和日志配置)

## 开发环境配置

### 基础开发配置

**文件**: `config/development.yaml`

```yaml
# 开发环境配置
server:
  name: "mcp-base64-server-dev"
  version: "1.0.0-dev"
  description: "MCP Base64 Server - Development Environment"

# 传输配置 - 开发时推荐使用HTTP便于调试
transport:
  type: "http"
  http:
    host: "localhost"
    port: 3000

# 启用HTTP服务器用于Web界面测试
http_server:
  enabled: true
  host: "127.0.0.1"  # 仅本地访问
  port: 8080

# 开发环境日志配置
logging:
  level: "DEBUG"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
  use_structured_format: false
  use_colors: true
  log_file_path: "logs/development.log"
  max_file_size: 10485760  # 10MB
  backup_count: 3

# 开发调试设置
debug:
  enabled: true
  inspector_port: 9000
  hot_reload: true
  profiling: true

# 性能监控（开发环境启用详细监控）
performance:
  enabled: true
  interval: 1.0
  detailed_metrics: true
```

**启动命令**:
```bash
# 使用开发配置启动
python main.py --config config/development.yaml

# 或使用命令行参数
python main.py \
  --transport http \
  --enable-http-server \
  --log-level DEBUG
```

### 热重载开发配置

**文件**: `scripts/dev-server.py`

```python
#!/usr/bin/env python3
"""
开发服务器脚本 - 支持热重载
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ServerRestartHandler(FileSystemEventHandler):
    def __init__(self):
        self.process = None
        self.restart_server()
    
    def on_modified(self, event):
        if event.is_directory:
            return
        
        # 只监控Python文件
        if event.src_path.endswith('.py'):
            print(f"📝 File changed: {event.src_path}")
            self.restart_server()
    
    def restart_server(self):
        if self.process:
            print("🔄 Restarting server...")
            self.process.terminate()
            self.process.wait()
        
        print("🚀 Starting server...")
        self.process = subprocess.Popen([
            sys.executable, "main.py",
            "--config", "config/development.yaml"
        ])
    
    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.wait()

def main():
    handler = ServerRestartHandler()
    observer = Observer()
    observer.schedule(handler, ".", recursive=True)
    observer.start()
    
    try:
        print("👀 Watching for file changes... Press Ctrl+C to stop")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping development server...")
        observer.stop()
        handler.stop()
    
    observer.join()

if __name__ == "__main__":
    main()
```

## 测试环境配置

### 自动化测试配置

**文件**: `config/testing.yaml`

```yaml
# 测试环境配置
server:
  name: "mcp-base64-server-test"
  version: "1.0.0-test"
  description: "MCP Base64 Server - Testing Environment"

# 测试环境使用stdio模式
transport:
  type: "stdio"

# 禁用HTTP服务器（测试时不需要）
http_server:
  enabled: false

# 测试环境日志配置
logging:
  level: "INFO"
  format: "%(asctime)s - %(levelname)s - %(message)s"
  use_structured_format: true
  use_colors: false
  log_file_path: "logs/testing.log"

# 禁用调试功能
debug:
  enabled: false

# 性能监控（测试环境收集基础指标）
performance:
  enabled: true
  interval: 5.0
  detailed_metrics: false
```

### CI/CD配置

**文件**: `.github/workflows/test.yml`

```yaml
name: Test MCP Base64 Server

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, '3.10', 3.11]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run unit tests
      run: |
        python -m pytest tests/ -v --cov=services --cov-report=xml
    
    - name: Run integration tests
      run: |
        python -m pytest test_integration.py -v
    
    - name: Test MCP protocol
      run: |
        # 启动服务器并测试MCP协议
        timeout 30s python main.py --config config/testing.yaml &
        sleep 5
        python test_mcp_inspector_integration.py
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### Docker测试配置

**文件**: `docker/test.Dockerfile`

```dockerfile
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt requirements-test.txt ./

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt -r requirements-test.txt

# 复制源代码
COPY . .

# 创建日志目录
RUN mkdir -p logs

# 运行测试
CMD ["python", "-m", "pytest", "-v", "--cov=services"]
```

## 生产环境配置

### 基础生产配置

**文件**: `config/production.yaml`

```yaml
# 生产环境配置
server:
  name: "mcp-base64-server"
  version: "1.0.0"
  description: "MCP Base64 Server - Production"

# 生产环境推荐HTTP模式（更稳定）
transport:
  type: "http"
  http:
    host: "0.0.0.0"
    port: 3000

# 启用HTTP服务器
http_server:
  enabled: true
  host: "0.0.0.0"
  port: 8080

# 生产环境日志配置
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  use_structured_format: true
  use_colors: false
  log_file_path: "/var/log/mcp-base64-server/server.log"
  max_file_size: 104857600  # 100MB
  backup_count: 10

# 禁用调试功能
debug:
  enabled: false

# 生产环境性能监控
performance:
  enabled: true
  interval: 10.0
  detailed_metrics: false

# 安全配置
security:
  rate_limiting:
    enabled: true
    requests_per_minute: 100
    requests_per_hour: 1000
  
  cors:
    enabled: true
    allowed_origins: ["https://yourdomain.com"]
    allowed_methods: ["GET", "POST", "OPTIONS"]
  
  ssl:
    enabled: true
    cert_file: "/etc/ssl/certs/server.crt"
    key_file: "/etc/ssl/private/server.key"

# 资源限制
limits:
  max_request_size: 1048576  # 1MB
  max_concurrent_requests: 100
  request_timeout: 30
```

### 高可用配置

**文件**: `config/production-ha.yaml`

```yaml
# 高可用生产环境配置
server:
  name: "mcp-base64-server-ha"
  version: "1.0.0"
  description: "MCP Base64 Server - High Availability"

# 集群配置
cluster:
  enabled: true
  node_id: "${NODE_ID}"
  nodes:
    - "mcp-server-1:3000"
    - "mcp-server-2:3000"
    - "mcp-server-3:3000"

# 健康检查配置
health_check:
  enabled: true
  endpoint: "/health"
  interval: 30
  timeout: 5
  retries: 3

# 负载均衡配置
load_balancer:
  algorithm: "round_robin"
  health_check_interval: 10
  max_failures: 3
  recovery_time: 60

# 数据持久化（如果需要）
persistence:
  enabled: false
  type: "redis"
  connection_string: "redis://redis-cluster:6379"

# 监控和告警
monitoring:
  prometheus:
    enabled: true
    port: 9090
    metrics_path: "/metrics"
  
  alerts:
    enabled: true
    webhook_url: "https://alerts.yourdomain.com/webhook"
    thresholds:
      error_rate: 0.05
      response_time_p95: 1000
      memory_usage: 0.8
```

## Docker部署

### 基础Docker配置

**文件**: `Dockerfile`

```dockerfile
# 多阶段构建
FROM python:3.11-slim as builder

# 设置构建参数
ARG BUILD_DATE
ARG VERSION
ARG VCS_REF

# 设置标签
LABEL org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="mcp-base64-server" \
      org.label-schema.description="MCP Base64 Server" \
      org.label-schema.version=$VERSION \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.vcs-url="https://github.com/your-repo/mcp-base64-server" \
      org.label-schema.schema-version="1.0"

# 安装构建依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir --user -r requirements.txt

# 生产阶段
FROM python:3.11-slim

# 创建非root用户
RUN groupadd -r mcp && useradd -r -g mcp mcp

# 从构建阶段复制依赖
COPY --from=builder /root/.local /home/mcp/.local

# 设置工作目录
WORKDIR /app

# 复制应用代码
COPY --chown=mcp:mcp . .

# 创建必要目录
RUN mkdir -p logs && chown -R mcp:mcp logs

# 切换到非root用户
USER mcp

# 设置环境变量
ENV PATH=/home/mcp/.local/bin:$PATH
ENV PYTHONPATH=/app

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# 暴露端口
EXPOSE 3000 8080

# 启动命令
CMD ["python", "main.py", "--config", "config/production.yaml"]
```

### Docker Compose配置

**文件**: `docker-compose.yml`

```yaml
version: '3.8'

services:
  mcp-base64-server:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        BUILD_DATE: ${BUILD_DATE:-$(date -u +'%Y-%m-%dT%H:%M:%SZ')}
        VERSION: ${VERSION:-1.0.0}
        VCS_REF: ${VCS_REF:-$(git rev-parse --short HEAD)}
    
    container_name: mcp-base64-server
    
    ports:
      - "3000:3000"  # MCP端口
      - "8080:8080"  # HTTP API端口
    
    environment:
      - MCP_LOG_LEVEL=INFO
      - MCP_TRANSPORT_TYPE=http
    
    volumes:
      - ./logs:/app/logs
      - ./config/production.yaml:/app/config/production.yaml:ro
    
    restart: unless-stopped
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.1'
          memory: 128M

  # 可选：添加反向代理
  nginx:
    image: nginx:alpine
    container_name: mcp-nginx
    
    ports:
      - "80:80"
      - "443:443"
    
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    
    depends_on:
      - mcp-base64-server
    
    restart: unless-stopped

  # 可选：添加监控
  prometheus:
    image: prom/prometheus:latest
    container_name: mcp-prometheus
    
    ports:
      - "9090:9090"
    
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
    
    restart: unless-stopped

volumes:
  prometheus_data:

networks:
  default:
    name: mcp-network
```

### Docker Swarm配置

**文件**: `docker-stack.yml`

```yaml
version: '3.8'

services:
  mcp-base64-server:
    image: mcp-base64-server:latest
    
    ports:
      - "3000:3000"
      - "8080:8080"
    
    environment:
      - MCP_LOG_LEVEL=INFO
      - MCP_TRANSPORT_TYPE=http
      - NODE_ID={{.Node.ID}}
    
    configs:
      - source: mcp_config
        target: /app/config/production.yaml
    
    secrets:
      - ssl_cert
      - ssl_key
    
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
        order: start-first
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.1'
          memory: 128M
      placement:
        constraints:
          - node.role == worker
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    
    networks:
      - mcp-network

  nginx:
    image: nginx:alpine
    
    ports:
      - "80:80"
      - "443:443"
    
    configs:
      - source: nginx_config
        target: /etc/nginx/nginx.conf
    
    secrets:
      - ssl_cert
      - ssl_key
    
    deploy:
      replicas: 2
      placement:
        constraints:
          - node.role == manager
    
    networks:
      - mcp-network

configs:
  mcp_config:
    file: ./config/production.yaml
  nginx_config:
    file: ./nginx/nginx.conf

secrets:
  ssl_cert:
    file: ./ssl/server.crt
  ssl_key:
    file: ./ssl/server.key

networks:
  mcp-network:
    driver: overlay
    attachable: true
```

## Kubernetes部署

### 基础Kubernetes配置

**文件**: `k8s/namespace.yaml`

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: mcp-base64
  labels:
    name: mcp-base64
```

**文件**: `k8s/configmap.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-base64-config
  namespace: mcp-base64
data:
  production.yaml: |
    server:
      name: "mcp-base64-server-k8s"
      version: "1.0.0"
      description: "MCP Base64 Server - Kubernetes"
    
    transport:
      type: "http"
      http:
        host: "0.0.0.0"
        port: 3000
    
    http_server:
      enabled: true
      host: "0.0.0.0"
      port: 8080
    
    logging:
      level: "INFO"
      format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
      use_structured_format: true
      use_colors: false
    
    debug:
      enabled: false
    
    performance:
      enabled: true
      interval: 10.0
```

**文件**: `k8s/secret.yaml`

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mcp-base64-secret
  namespace: mcp-base64
type: Opaque
data:
  ssl-cert: LS0tLS1CRUdJTi... # base64编码的SSL证书
  ssl-key: LS0tLS1CRUdJTi...  # base64编码的SSL私钥
```

**文件**: `k8s/deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-base64-server
  namespace: mcp-base64
  labels:
    app: mcp-base64-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcp-base64-server
  template:
    metadata:
      labels:
        app: mcp-base64-server
    spec:
      containers:
      - name: mcp-base64-server
        image: mcp-base64-server:1.0.0
        ports:
        - containerPort: 3000
          name: mcp-port
        - containerPort: 8080
          name: http-port
        
        env:
        - name: MCP_LOG_LEVEL
          value: "INFO"
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        
        volumeMounts:
        - name: config-volume
          mountPath: /app/config
          readOnly: true
        - name: ssl-volume
          mountPath: /app/ssl
          readOnly: true
        
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
      
      volumes:
      - name: config-volume
        configMap:
          name: mcp-base64-config
      - name: ssl-volume
        secret:
          secretName: mcp-base64-secret
      
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
```

**文件**: `k8s/service.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: mcp-base64-service
  namespace: mcp-base64
  labels:
    app: mcp-base64-server
spec:
  selector:
    app: mcp-base64-server
  ports:
  - name: mcp-port
    port: 3000
    targetPort: 3000
    protocol: TCP
  - name: http-port
    port: 8080
    targetPort: 8080
    protocol: TCP
  type: ClusterIP
```

**文件**: `k8s/ingress.yaml`

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mcp-base64-ingress
  namespace: mcp-base64
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  tls:
  - hosts:
    - mcp.yourdomain.com
    secretName: mcp-base64-tls
  rules:
  - host: mcp.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: mcp-base64-service
            port:
              number: 8080
      - path: /mcp
        pathType: Prefix
        backend:
          service:
            name: mcp-base64-service
            port:
              number: 3000
```

### Helm Chart配置

**文件**: `helm/Chart.yaml`

```yaml
apiVersion: v2
name: mcp-base64-server
description: A Helm chart for MCP Base64 Server
type: application
version: 1.0.0
appVersion: "1.0.0"
keywords:
  - mcp
  - base64
  - ai
  - tools
home: https://github.com/your-repo/mcp-base64-server
sources:
  - https://github.com/your-repo/mcp-base64-server
maintainers:
  - name: Your Name
    email: your.email@example.com
```

**文件**: `helm/values.yaml`

```yaml
# 默认值配置
replicaCount: 3

image:
  repository: mcp-base64-server
  pullPolicy: IfNotPresent
  tag: "1.0.0"

nameOverride: ""
fullnameOverride: ""

serviceAccount:
  create: true
  annotations: {}
  name: ""

podAnnotations: {}

podSecurityContext:
  fsGroup: 1000

securityContext:
  capabilities:
    drop:
    - ALL
  readOnlyRootFilesystem: true
  runAsNonRoot: true
  runAsUser: 1000

service:
  type: ClusterIP
  mcpPort: 3000
  httpPort: 8080

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
  hosts:
    - host: mcp.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
          port: 8080
        - path: /mcp
          pathType: Prefix
          port: 3000
  tls:
    - secretName: mcp-base64-tls
      hosts:
        - mcp.yourdomain.com

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 128Mi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80
  targetMemoryUtilizationPercentage: 80

nodeSelector: {}

tolerations: []

affinity: {}

config:
  logLevel: INFO
  transportType: http
  enableHttpServer: true
  enableDebug: false
```

## 云平台部署

### AWS ECS配置

**文件**: `aws/task-definition.json`

```json
{
  "family": "mcp-base64-server",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::123456789012:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "mcp-base64-server",
      "image": "123456789012.dkr.ecr.us-west-2.amazonaws.com/mcp-base64-server:latest",
      "portMappings": [
        {
          "containerPort": 3000,
          "protocol": "tcp"
        },
        {
          "containerPort": 8080,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "MCP_LOG_LEVEL",
          "value": "INFO"
        },
        {
          "name": "MCP_TRANSPORT_TYPE",
          "value": "http"
        }
      ],
      "secrets": [
        {
          "name": "SSL_CERT",
          "valueFrom": "arn:aws:secretsmanager:us-west-2:123456789012:secret:mcp-ssl-cert"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/mcp-base64-server",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": [
          "CMD-SHELL",
          "curl -f http://localhost:8080/health || exit 1"
        ],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

### Google Cloud Run配置

**文件**: `gcp/service.yaml`

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: mcp-base64-server
  annotations:
    run.googleapis.com/ingress: all
    run.googleapis.com/execution-environment: gen2
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/minScale: "1"
        autoscaling.knative.dev/maxScale: "10"
        run.googleapis.com/cpu-throttling: "false"
        run.googleapis.com/memory: "512Mi"
        run.googleapis.com/cpu: "1000m"
    spec:
      containerConcurrency: 100
      timeoutSeconds: 300
      containers:
      - image: gcr.io/your-project/mcp-base64-server:latest
        ports:
        - containerPort: 8080
        env:
        - name: MCP_LOG_LEVEL
          value: "INFO"
        - name: MCP_TRANSPORT_TYPE
          value: "http"
        - name: PORT
          value: "8080"
        resources:
          limits:
            cpu: "1000m"
            memory: "512Mi"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Azure Container Instances配置

**文件**: `azure/container-group.yaml`

```yaml
apiVersion: 2019-12-01
location: eastus
name: mcp-base64-server
properties:
  containers:
  - name: mcp-base64-server
    properties:
      image: yourregistry.azurecr.io/mcp-base64-server:latest
      resources:
        requests:
          cpu: 0.5
          memoryInGb: 0.5
      ports:
      - port: 3000
        protocol: TCP
      - port: 8080
        protocol: TCP
      environmentVariables:
      - name: MCP_LOG_LEVEL
        value: INFO
      - name: MCP_TRANSPORT_TYPE
        value: http
      livenessProbe:
        httpGet:
          path: /health
          port: 8080
        initialDelaySeconds: 30
        periodSeconds: 10
  osType: Linux
  restartPolicy: Always
  ipAddress:
    type: Public
    ports:
    - protocol: TCP
      port: 3000
    - protocol: TCP
      port: 8080
    dnsNameLabel: mcp-base64-server
tags:
  environment: production
  application: mcp-base64-server
```

## 负载均衡配置

### Nginx负载均衡

**文件**: `nginx/nginx.conf`

```nginx
upstream mcp_backend {
    least_conn;
    server mcp-server-1:3000 max_fails=3 fail_timeout=30s;
    server mcp-server-2:3000 max_fails=3 fail_timeout=30s;
    server mcp-server-3:3000 max_fails=3 fail_timeout=30s;
}

upstream http_backend {
    least_conn;
    server mcp-server-1:8080 max_fails=3 fail_timeout=30s;
    server mcp-server-2:8080 max_fails=3 fail_timeout=30s;
    server mcp-server-3:8080 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name mcp.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name mcp.yourdomain.com;
    
    ssl_certificate /etc/ssl/certs/server.crt;
    ssl_certificate_key /etc/ssl/private/server.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    
    # 安全头部
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
    
    # 速率限制
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
    
    # MCP端点
    location /mcp {
        proxy_pass http://mcp_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # HTTP API端点
    location / {
        proxy_pass http://http_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS支持
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
        add_header Access-Control-Allow-Headers "Content-Type, Authorization";
        
        if ($request_method = 'OPTIONS') {
            return 204;
        }
    }
    
    # 健康检查
    location /nginx-health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

### HAProxy配置

**文件**: `haproxy/haproxy.cfg`

```
global
    daemon
    maxconn 4096
    log stdout local0
    
defaults
    mode http
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms
    option httplog
    option dontlognull
    
frontend mcp_frontend
    bind *:80
    bind *:443 ssl crt /etc/ssl/certs/server.pem
    redirect scheme https if !{ ssl_fc }
    
    # 根据路径分发请求
    acl is_mcp path_beg /mcp
    acl is_api path_beg /api
    acl is_health path_beg /health
    
    use_backend mcp_backend if is_mcp
    use_backend api_backend if is_api
    use_backend api_backend if is_health
    default_backend web_backend

backend mcp_backend
    balance roundrobin
    option httpchk GET /health
    server mcp1 mcp-server-1:3000 check
    server mcp2 mcp-server-2:3000 check
    server mcp3 mcp-server-3:3000 check

backend api_backend
    balance roundrobin
    option httpchk GET /health
    server api1 mcp-server-1:8080 check
    server api2 mcp-server-2:8080 check
    server api3 mcp-server-3:8080 check

backend web_backend
    balance roundrobin
    option httpchk GET /health
    server web1 mcp-server-1:8080 check
    server web2 mcp-server-2:8080 check
    server web3 mcp-server-3:8080 check

listen stats
    bind *:8404
    stats enable
    stats uri /stats
    stats refresh 30s
```

## 监控和日志配置

### Prometheus监控配置

**文件**: `monitoring/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  - job_name: 'mcp-base64-server'
    static_configs:
      - targets: ['mcp-server-1:9090', 'mcp-server-2:9090', 'mcp-server-3:9090']
    metrics_path: /metrics
    scrape_interval: 10s
    
  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:9113']
    
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
```

### Grafana仪表板配置

**文件**: `monitoring/grafana-dashboard.json`

```json
{
  "dashboard": {
    "id": null,
    "title": "MCP Base64 Server Dashboard",
    "tags": ["mcp", "base64"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(mcp_requests_total[5m])",
            "legendFormat": "{{instance}} - {{method}}"
          }
        ]
      },
      {
        "id": 2,
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(mcp_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "id": 3,
        "title": "Error Rate",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rate(mcp_errors_total[5m]) / rate(mcp_requests_total[5m])",
            "legendFormat": "Error Rate"
          }
        ]
      }
    ]
  }
}
```

### ELK Stack日志配置

**文件**: `logging/logstash.conf`

```
input {
  beats {
    port => 5044
  }
}

filter {
  if [fields][service] == "mcp-base64-server" {
    json {
      source => "message"
    }
    
    date {
      match => [ "timestamp", "ISO8601" ]
    }
    
    mutate {
      add_field => { "service" => "mcp-base64-server" }
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "mcp-base64-server-%{+YYYY.MM.dd}"
  }
}
```

**文件**: `logging/filebeat.yml`

```yaml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/mcp-base64-server/*.log
  fields:
    service: mcp-base64-server
  fields_under_root: true
  multiline.pattern: '^\d{4}-\d{2}-\d{2}'
  multiline.negate: true
  multiline.match: after

output.logstash:
  hosts: ["logstash:5044"]

processors:
- add_host_metadata:
    when.not.contains.tags: forwarded
```

---

这些配置示例涵盖了从开发到生产的各种部署场景。根据你的具体需求选择合适的配置，并根据实际环境进行调整。