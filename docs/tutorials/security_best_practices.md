# 安全最佳实践指南

本文档提供了MCP Base64服务器和AI代理集成的安全最佳实践。

## 目录

- [安全威胁模型](#安全威胁模型)
- [输入验证和清理](#输入验证和清理)
- [认证和授权](#认证和授权)
- [传输安全](#传输安全)
- [数据保护](#数据保护)
- [访问控制](#访问控制)
- [审计和监控](#审计和监控)
- [部署安全](#部署安全)

## 安全威胁模型

### 主要威胁

1. **恶意输入注入**: 通过base64参数注入恶意代码
2. **未授权访问**: 绕过认证机制访问工具
3. **数据泄露**: 敏感信息被未授权获取
4. **拒绝服务攻击**: 大量请求导致服务不可用
5. **中间人攻击**: 传输过程中数据被截获

### 风险评估

| 威胁类型 | 可能性 | 影响程度 | 风险等级 | 缓解措施 |
|---------|--------|----------|----------|----------|
| 恶意输入注入 | 高 | 中 | 高 | 输入验证、参数清理 |
| 未授权访问 | 中 | 高 | 高 | 认证机制、访问控制 |
| 数据泄露 | 低 | 高 | 中 | 数据加密、访问日志 |
| 拒绝服务攻击 | 中 | 中 | 中 | 速率限制、负载均衡 |

## 输入验证和清理

### 输入验证框架

```python
import re
import html
import base64
from typing import Any, Dict

class InputValidator:
    def __init__(self):
        self.rules = {
            'base64': {
                'pattern': r'^[A-Za-z0-9+/]*={0,2}$',
                'max_length': 1398101,  # 1MB base64编码后的长度
                'forbidden_patterns': [r'javascript:', r'<script', r'eval\(']
            },
            'text': {
                'max_length': 1048576,
                'forbidden_patterns': [r'<script', r'javascript:', r'onload=']
            }
        }
    
    def validate_input(self, value: str, rule_name: str) -> Dict[str, Any]:
        """验证输入"""
        if rule_name not in self.rules:
            raise ValueError(f"Unknown validation rule: {rule_name}")
        
        rule = self.rules[rule_name]
        result = {'valid': True, 'sanitized_value': value, 'errors': []}
        
        # 长度检查
        if len(value) > rule.get('max_length', 1048576):
            result['valid'] = False
            result['errors'].append("Input too long")
        
        # 模式匹配
        if 'pattern' in rule and not re.match(rule['pattern'], value):
            result['valid'] = False
            result['errors'].append("Invalid format")
        
        # 禁止模式检查
        for pattern in rule.get('forbidden_patterns', []):
            if re.search(pattern, value, re.IGNORECASE):
                result['valid'] = False
                result['errors'].append(f"Forbidden pattern: {pattern}")
        
        # 清理输入
        if result['valid']:
            result['sanitized_value'] = self._sanitize_input(value, rule_name)
        
        return result
    
    def _sanitize_input(self, value: str, rule_name: str) -> str:
        """清理输入"""
        sanitized = value
        
        # 移除控制字符
        sanitized = ''.join(
            char for char in sanitized 
            if ord(char) >= 32 or char in '\t\n\r'
        )
        
        if rule_name == 'text':
            sanitized = html.escape(sanitized)
        elif rule_name == 'base64':
            sanitized = re.sub(r'\s+', '', sanitized)
        
        return sanitized
```

### 参数验证装饰器

```python
from functools import wraps

def validate_parameters(parameter_rules: Dict[str, str]):
    """参数验证装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            validator = InputValidator()
            validation_errors = []
            
            for param_name, rule_name in parameter_rules.items():
                if param_name in kwargs:
                    value = kwargs[param_name]
                    result = validator.validate_input(value, rule_name)
                    
                    if not result['valid']:
                        validation_errors.extend([
                            f"{param_name}: {error}" for error in result['errors']
                        ])
                    else:
                        kwargs[param_name] = result['sanitized_value']
            
            if validation_errors:
                raise ValidationError(f"Validation failed: {'; '.join(validation_errors)}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# 使用示例
class Base64Service:
    @validate_parameters({'text': 'text'})
    async def encode(self, text: str) -> str:
        return base64.b64encode(text.encode('utf-8')).decode('ascii')
    
    @validate_parameters({'base64_string': 'base64'})
    async def decode(self, base64_string: str) -> str:
        return base64.b64decode(base64_string).decode('utf-8')
```

## 认证和授权

### JWT认证

```python
import jwt
from datetime import datetime, timedelta
from typing import Dict, List

class JWTAuthenticator:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.algorithm = 'HS256'
        self.token_expiry = timedelta(hours=24)
    
    def generate_token(self, user_id: str, permissions: List[str]) -> str:
        """生成访问令牌"""
        payload = {
            'user_id': user_id,
            'permissions': permissions,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + self.token_expiry
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid token")
```

### 基于角色的访问控制

```python
from enum import Enum
from dataclasses import dataclass
from typing import Set

class Permission(Enum):
    BASE64_ENCODE = "base64:encode"
    BASE64_DECODE = "base64:decode"
    ADMIN_ACCESS = "admin:access"

@dataclass
class Role:
    name: str
    permissions: Set[Permission]

class RBACManager:
    def __init__(self):
        self.roles = {
            'user': Role('user', {Permission.BASE64_ENCODE, Permission.BASE64_DECODE}),
            'admin': Role('admin', {Permission.BASE64_ENCODE, Permission.BASE64_DECODE, Permission.ADMIN_ACCESS}),
            'readonly': Role('readonly', {Permission.BASE64_DECODE})
        }
        self.user_roles = {}
    
    def assign_role(self, user_id: str, role_name: str):
        """分配角色"""
        if role_name not in self.roles:
            raise ValueError(f"Role '{role_name}' does not exist")
        
        if user_id not in self.user_roles:
            self.user_roles[user_id] = set()
        
        self.user_roles[user_id].add(role_name)
    
    def check_permission(self, user_id: str, permission: Permission) -> bool:
        """检查权限"""
        user_roles = self.user_roles.get(user_id, set())
        
        for role_name in user_roles:
            if role_name in self.roles:
                role = self.roles[role_name]
                if permission in role.permissions:
                    return True
        
        return False
```

## 传输安全

### TLS配置

```python
import ssl

class TLSConfiguration:
    def create_ssl_context(self, cert_file: str, key_file: str) -> ssl.SSLContext:
        """创建安全的SSL上下文"""
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        
        # 设置TLS版本
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.maximum_version = ssl.TLSVersion.TLSv1_3
        
        # 加载证书
        context.load_cert_chain(cert_file, key_file)
        
        # 安全选项
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1
        
        return context
```

### 消息完整性验证

```python
import hmac
import hashlib
import time

class MessageIntegrityVerifier:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key.encode('utf-8')
        self.hash_algorithm = hashlib.sha256
    
    def sign_message(self, message: Dict[str, Any]) -> str:
        """对消息进行签名"""
        message['timestamp'] = int(time.time())
        message_str = json.dumps(message, sort_keys=True)
        
        signature = hmac.new(
            self.secret_key,
            message_str.encode('utf-8'),
            self.hash_algorithm
        ).hexdigest()
        
        return signature
    
    def verify_message(self, message: Dict[str, Any], signature: str) -> bool:
        """验证消息签名"""
        try:
            message_str = json.dumps(message, sort_keys=True)
            expected_signature = hmac.new(
                self.secret_key,
                message_str.encode('utf-8'),
                self.hash_algorithm
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
        except Exception:
            return False
```

## 数据保护

### 敏感数据加密

```python
from cryptography.fernet import Fernet
import base64

class DataEncryption:
    def __init__(self, key: str):
        self.cipher = Fernet(key.encode())
    
    def encrypt(self, data: str) -> str:
        """加密数据"""
        encrypted_data = self.cipher.encrypt(data.encode('utf-8'))
        return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
    
    def decrypt(self, encrypted_data: str) -> str:
        """解密数据"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted_data = self.cipher.decrypt(encrypted_bytes)
            return decrypted_data.decode('utf-8')
        except Exception as e:
            raise DecryptionError(f"Failed to decrypt data: {str(e)}")
```

### 数据脱敏

```python
import re

class DataMasker:
    def __init__(self):
        self.patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b\d{3}-\d{3}-\d{4}\b',
            'ip_address': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
        }
    
    def mask_data(self, text: str) -> str:
        """脱敏数据"""
        masked_text = text
        
        # 脱敏邮箱
        masked_text = re.sub(self.patterns['email'], self._mask_email, masked_text)
        
        # 脱敏电话
        masked_text = re.sub(self.patterns['phone'], "***-***-****", masked_text)
        
        # 脱敏IP地址
        masked_text = re.sub(self.patterns['ip_address'], "***.***.***", masked_text)
        
        return masked_text
    
    def _mask_email(self, match) -> str:
        email = match.group(0)
        local, domain = email.split('@')
        
        if len(local) <= 2:
            masked_local = '*' * len(local)
        else:
            masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
        
        return f"{masked_local}@{domain}"
```

## 访问控制

### IP访问控制

```python
import ipaddress
from typing import Set

class IPAccessController:
    def __init__(self):
        self.whitelist: Set[ipaddress.IPv4Network] = set()
        self.blacklist: Set[ipaddress.IPv4Network] = set()
        self.whitelist_enabled = False
        self.blacklist_enabled = True
    
    def add_to_blacklist(self, ip_or_network: str):
        """添加到黑名单"""
        network = ipaddress.ip_network(ip_or_network, strict=False)
        self.blacklist.add(network)
    
    def is_allowed(self, ip_address: str) -> bool:
        """检查IP是否被允许"""
        try:
            ip = ipaddress.ip_address(ip_address)
        except ValueError:
            return False
        
        # 检查黑名单
        if self.blacklist_enabled:
            for network in self.blacklist:
                if ip in network:
                    return False
        
        # 检查白名单
        if self.whitelist_enabled:
            for network in self.whitelist:
                if ip in network:
                    return True
            return False
        
        return True
```

### 速率限制

```python
import time
from collections import defaultdict

class RateLimiter:
    def __init__(self):
        self.request_counts = defaultdict(list)
        self.limits = {
            'per_minute': 60,
            'per_hour': 1000
        }
    
    def is_allowed(self, client_id: str) -> bool:
        """检查是否允许请求"""
        current_time = time.time()
        
        # 清理过期记录
        self.request_counts[client_id] = [
            t for t in self.request_counts[client_id]
            if current_time - t < 3600  # 保留1小时内的记录
        ]
        
        requests = self.request_counts[client_id]
        
        # 检查每分钟限制
        minute_requests = [t for t in requests if current_time - t < 60]
        if len(minute_requests) >= self.limits['per_minute']:
            return False
        
        # 检查每小时限制
        if len(requests) >= self.limits['per_hour']:
            return False
        
        # 记录请求
        self.request_counts[client_id].append(current_time)
        
        return True
```

## 审计和监控

### 安全事件监控

```python
from enum import Enum
from dataclasses import dataclass
import time

class SecurityEventType(Enum):
    AUTHENTICATION_FAILURE = "auth_failure"
    MALICIOUS_INPUT = "malicious_input"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

@dataclass
class SecurityEvent:
    event_type: SecurityEventType
    timestamp: float
    user_id: str
    client_ip: str
    details: dict
    severity: str

class SecurityEventMonitor:
    def __init__(self):
        self.events = []
        self.alert_thresholds = {
            SecurityEventType.AUTHENTICATION_FAILURE: 5,
            SecurityEventType.MALICIOUS_INPUT: 1
        }
    
    def record_event(self, event: SecurityEvent):
        """记录安全事件"""
        self.events.append(event)
        self._check_alert_conditions(event)
    
    def _check_alert_conditions(self, event: SecurityEvent):
        """检查告警条件"""
        if event.event_type not in self.alert_thresholds:
            return
        
        threshold = self.alert_thresholds[event.event_type]
        current_time = time.time()
        
        # 统计5分钟内的同类事件
        recent_events = [
            e for e in self.events
            if e.event_type == event.event_type
            and current_time - e.timestamp <= 300
        ]
        
        if len(recent_events) >= threshold:
            self._trigger_alert(event.event_type, recent_events)
    
    def _trigger_alert(self, event_type: SecurityEventType, events):
        """触发告警"""
        print(f"SECURITY ALERT: {event_type.value} threshold exceeded")
        print(f"Event count: {len(events)} in last 5 minutes")
```

## 部署安全

### 安全配置检查清单

#### 服务器配置
- [ ] 使用非root用户运行服务
- [ ] 禁用不必要的端口和服务
- [ ] 配置防火墙规则
- [ ] 启用自动安全更新
- [ ] 配置日志轮转

#### 应用配置
- [ ] 使用强密码和密钥
- [ ] 启用HTTPS/TLS
- [ ] 配置CORS策略
- [ ] 设置安全头部
- [ ] 启用速率限制

#### 监控配置
- [ ] 配置日志收集
- [ ] 设置安全告警
- [ ] 监控系统资源
- [ ] 配置备份策略

### Docker安全配置

```dockerfile
FROM python:3.11-slim

# 创建非root用户
RUN groupadd -r mcp && useradd -r -g mcp mcp

# 设置工作目录
WORKDIR /app

# 复制文件并设置权限
COPY --chown=mcp:mcp . .

# 切换到非root用户
USER mcp

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# 暴露端口
EXPOSE 8080

# 启动命令
CMD ["python", "main.py"]
```

### 环境变量安全

```bash
# 使用环境变量存储敏感信息
export MCP_SECRET_KEY="your-secret-key-here"
export MCP_JWT_SECRET="your-jwt-secret-here"
export MCP_DB_PASSWORD="your-db-password-here"

# 在生产环境中使用密钥管理服务
# 例如 AWS Secrets Manager, Azure Key Vault, HashiCorp Vault
```

---

通过实施这些安全最佳实践，可以显著提高MCP Base64服务器的安全性。记住安全是一个持续的过程，需要定期评估和更新安全策略。