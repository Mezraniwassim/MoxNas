# MoxNAS Production Deployment Guide

## Overview

This guide covers production deployment strategies, container orchestration, monitoring setup, and operational best practices for MoxNAS in enterprise environments.

## Deployment Architecture

### Production Architecture Options

#### Option 1: Single Node Deployment
```
┌─────────────────────────────────────────┐
│              Load Balancer              │
│                (Nginx)                  │
├─────────────────────────────────────────┤
│             Application                 │
│          (MoxNAS + Gunicorn)           │
├─────────────────────────────────────────┤
│              Database                   │
│            (PostgreSQL)                 │
├─────────────────────────────────────────┤
│               Cache                     │
│              (Redis)                    │
├─────────────────────────────────────────┤
│             Monitoring                  │
│        (Prometheus + Grafana)          │
└─────────────────────────────────────────┘
```

#### Option 2: High Availability Deployment
```
┌─────────────────────────────────────────┐
│         Load Balancer Cluster           │
│          (HAProxy + Keepalived)         │
├─────────────────────────────────────────┤
│      Application Cluster (3 nodes)     │
│         MoxNAS + Gunicorn              │
├─────────────────────────────────────────┤
│       Database Cluster                  │
│    (PostgreSQL Primary + Replicas)     │
├─────────────────────────────────────────┤
│         Cache Cluster                   │
│       (Redis Cluster/Sentinel)         │
├─────────────────────────────────────────┤
│        Monitoring Stack                 │
│   (Prometheus HA + Grafana Cluster)    │
└─────────────────────────────────────────┘
```

## Container Deployment

### Docker Production Deployment

#### Step 1: Prepare Environment

```bash
# Create deployment directory
sudo mkdir -p /opt/moxnas-production
cd /opt/moxnas-production

# Download production configuration
wget https://raw.githubusercontent.com/your-org/moxnas/main/docker-compose.production.yml
wget https://raw.githubusercontent.com/your-org/moxnas/main/config/production/.env.example
```

#### Step 2: Configure Environment

```bash
# Create environment file
cp .env.example .env

# Generate secure secrets
export SECRET_KEY=$(openssl rand -base64 50)
export DB_PASSWORD=$(openssl rand -base64 32)
export REDIS_PASSWORD=$(openssl rand -base64 32)

# Update .env file
cat > .env << EOF
# Security
SECRET_KEY=${SECRET_KEY}
DEBUG=False
ALLOWED_HOSTS=your-domain.com,localhost

# Database
DB_NAME=moxnas
DB_USER=moxnas
DB_PASSWORD=${DB_PASSWORD}
DB_HOST=db
DB_PORT=5432

# Cache
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0

# Email
EMAIL_HOST=smtp.your-domain.com
EMAIL_PORT=587
EMAIL_HOST_USER=notifications@your-domain.com
EMAIL_HOST_PASSWORD=your-email-password
EMAIL_USE_TLS=True

# Monitoring
PROMETHEUS_ENABLED=True
GRAFANA_ADMIN_PASSWORD=secure-admin-password

# Storage
STORAGE_PATH=/mnt/storage
BACKUP_PATH=/mnt/backup
EOF
```

#### Step 3: Deploy with Docker Compose

```yaml
# docker-compose.production.yml
version: '3.8'

services:
  app:
    image: moxnas/moxnas:latest
    restart: unless-stopped
    environment:
      - DEBUG=False
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - app_data:/app/data
      - storage_data:/mnt/storage
      - backup_data:/mnt/backup
      - /etc/localtime:/etc/localtime:ro
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/system/health/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G

  db:
    image: postgres:15
    restart: unless-stopped
    environment:
      - POSTGRES_DB=${DB_NAME}
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./config/postgres/postgresql.conf:/etc/postgresql/postgresql.conf
    ports:
      - "127.0.0.1:5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "127.0.0.1:6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    volumes:
      - ./config/nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./config/nginx/moxnas.conf:/etc/nginx/conf.d/default.conf
      - ./ssl:/etc/nginx/ssl
      - app_static:/var/www/static
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - app
    healthcheck:
      test: ["CMD", "nginx", "-t"]
      interval: 30s
      timeout: 10s
      retries: 3

  prometheus:
    image: prom/prometheus:latest
    restart: unless-stopped
    volumes:
      - ./config/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "127.0.0.1:9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-lifecycle'

  grafana:
    image: grafana/grafana:latest
    restart: unless-stopped
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./config/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./config/grafana/datasources:/etc/grafana/provisioning/datasources
    ports:
      - "127.0.0.1:3000:3000"
    depends_on:
      - prometheus

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:
  app_data:
  app_static:
  storage_data:
  backup_data:

networks:
  default:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

#### Step 4: Start Services

```bash
# Create necessary directories
sudo mkdir -p config/{nginx,prometheus,grafana,postgres}
sudo mkdir -p ssl

# Generate SSL certificates (or use your own)
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/moxnas.key \
  -out ssl/moxnas.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=your-domain.com"

# Start services
docker-compose -f docker-compose.production.yml up -d

# Initialize database
docker-compose exec app python manage.py migrate
docker-compose exec app python manage.py createsuperuser
docker-compose exec app python manage.py collectstatic --noinput
```

### Kubernetes Deployment

#### Step 1: Create Namespace

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: moxnas
```

#### Step 2: Configure Secrets

```yaml
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: moxnas-secrets
  namespace: moxnas
type: Opaque
data:
  secret-key: <base64-encoded-secret-key>
  db-password: <base64-encoded-db-password>
  redis-password: <base64-encoded-redis-password>
```

#### Step 3: Database Deployment

```yaml
# postgres.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: moxnas
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15
        env:
        - name: POSTGRES_DB
          value: moxnas
        - name: POSTGRES_USER
          value: moxnas
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: moxnas-secrets
              key: db-password
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        livenessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - moxnas
            - -d
            - moxnas
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - moxnas
            - -d
            - moxnas
          initialDelaySeconds: 5
          periodSeconds: 5
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 50Gi
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: moxnas
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
```

#### Step 4: Application Deployment

```yaml
# moxnas.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: moxnas
  namespace: moxnas
spec:
  replicas: 3
  selector:
    matchLabels:
      app: moxnas
  template:
    metadata:
      labels:
        app: moxnas
    spec:
      containers:
      - name: moxnas
        image: moxnas/moxnas:latest
        env:
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: moxnas-secrets
              key: secret-key
        - name: DATABASE_URL
          value: "postgresql://moxnas:$(DB_PASSWORD)@postgres:5432/moxnas"
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: moxnas-secrets
              key: db-password
        - name: REDIS_URL
          value: "redis://:$(REDIS_PASSWORD)@redis:6379/0"
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: moxnas-secrets
              key: redis-password
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /api/system/health/live/
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /api/system/health/ready/
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        volumeMounts:
        - name: storage
          mountPath: /mnt/storage
        - name: backup
          mountPath: /mnt/backup
      volumes:
      - name: storage
        persistentVolumeClaim:
          claimName: moxnas-storage
      - name: backup
        persistentVolumeClaim:
          claimName: moxnas-backup
---
apiVersion: v1
kind: Service
metadata:
  name: moxnas
  namespace: moxnas
spec:
  selector:
    app: moxnas
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

#### Step 5: Ingress Configuration

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: moxnas-ingress
  namespace: moxnas
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - moxnas.your-domain.com
    secretName: moxnas-tls
  rules:
  - host: moxnas.your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: moxnas
            port:
              number: 8000
```

#### Step 6: Deploy to Kubernetes

```bash
# Apply configurations
kubectl apply -f namespace.yaml
kubectl apply -f secrets.yaml
kubectl apply -f postgres.yaml
kubectl apply -f redis.yaml
kubectl apply -f moxnas.yaml
kubectl apply -f ingress.yaml

# Check deployment status
kubectl get pods -n moxnas
kubectl get services -n moxnas

# Initialize database
kubectl exec -n moxnas deployment/moxnas -- python manage.py migrate
kubectl exec -n moxnas deployment/moxnas -- python manage.py createsuperuser
```

## Monitoring and Observability

### Prometheus Configuration

```yaml
# config/prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "rules/*.yml"

scrape_configs:
  - job_name: 'moxnas'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/api/system/metrics/prometheus/'
    scrape_interval: 30s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

remote_write:
  - url: "http://thanos-receive:19291/api/v1/receive"
```

### Grafana Dashboards

#### System Overview Dashboard

```json
{
  "dashboard": {
    "title": "MoxNAS System Overview",
    "panels": [
      {
        "title": "System Health",
        "type": "stat",
        "targets": [
          {
            "expr": "moxnas_system_health_status",
            "legendFormat": "Health Status"
          }
        ]
      },
      {
        "title": "CPU Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "moxnas_cpu_usage_percent",
            "legendFormat": "CPU Core {{core}}"
          }
        ]
      },
      {
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "moxnas_memory_usage_bytes{type=\"used\"} / moxnas_memory_usage_bytes{type=\"total\"} * 100",
            "legendFormat": "Memory Usage %"
          }
        ]
      },
      {
        "title": "Service Status",
        "type": "table",
        "targets": [
          {
            "expr": "moxnas_service_status",
            "legendFormat": "{{service}}"
          }
        ]
      }
    ]
  }
}
```

### Alerting Rules

```yaml
# config/prometheus/rules/moxnas.yml
groups:
  - name: moxnas.rules
    rules:
      # High CPU usage
      - alert: HighCPUUsage
        expr: moxnas_cpu_usage_percent > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage detected"
          description: "CPU usage is above 80% for more than 5 minutes"

      # High memory usage
      - alert: HighMemoryUsage
        expr: (moxnas_memory_usage_bytes{type="used"} / moxnas_memory_usage_bytes{type="total"}) * 100 > 90
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High memory usage detected"
          description: "Memory usage is above 90% for more than 2 minutes"

      # Service down
      - alert: ServiceDown
        expr: moxnas_service_status == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service {{$labels.service}} is down"
          description: "Service {{$labels.service}} has been down for more than 1 minute"

      # High disk usage
      - alert: HighDiskUsage
        expr: (moxnas_disk_usage_bytes{type="used"} / moxnas_disk_usage_bytes{type="total"}) * 100 > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High disk usage detected"
          description: "Disk usage is above 85% for more than 5 minutes"

      # Database connection issues
      - alert: DatabaseConnectionFailed
        expr: moxnas_database_health_status == 0
        for: 30s
        labels:
          severity: critical
        annotations:
          summary: "Database connection failed"
          description: "Unable to connect to database for more than 30 seconds"
```

## High Availability Setup

### Load Balancer Configuration (HAProxy)

```
# /etc/haproxy/haproxy.cfg
global
    daemon
    log stdout local0
    chroot /var/lib/haproxy
    stats socket /run/haproxy/admin.sock mode 660 level admin
    stats timeout 30s
    user haproxy
    group haproxy

defaults
    mode http
    log global
    option httplog
    option dontlognull
    option http-server-close
    option forwardfor except 127.0.0.0/8
    option redispatch
    retries 3
    timeout http-request 10s
    timeout queue 1m
    timeout connect 10s
    timeout client 1m
    timeout server 1m
    timeout http-keep-alive 10s
    timeout check 10s
    maxconn 3000

frontend moxnas_frontend
    bind *:80
    bind *:443 ssl crt /etc/haproxy/certs/moxnas.pem
    redirect scheme https if !{ ssl_fc }
    default_backend moxnas_backend

backend moxnas_backend
    balance roundrobin
    option httpchk GET /api/system/health/ready/
    http-check expect status 200
    
    server moxnas1 10.0.1.10:8000 check
    server moxnas2 10.0.1.11:8000 check
    server moxnas3 10.0.1.12:8000 check

listen stats
    bind *:8404
    stats enable
    stats uri /stats
    stats refresh 30s
    stats admin if TRUE
```

### Database Replication (PostgreSQL)

#### Primary Server Configuration

```postgresql
# postgresql.conf
wal_level = replica
max_wal_senders = 3
max_replication_slots = 3
synchronous_commit = on
synchronous_standby_names = 'standby1'

# pg_hba.conf
host replication replicator 10.0.1.0/24 md5
```

#### Standby Server Configuration

```bash
# Create base backup
pg_basebackup -h primary-server -D /var/lib/postgresql/13/main -U replicator -P -v -R -W

# postgresql.conf
hot_standby = on
max_standby_streaming_delay = 30s
wal_receiver_status_interval = 10s
hot_standby_feedback = on
```

### Redis High Availability

#### Redis Sentinel Configuration

```redis
# sentinel.conf
port 26379
sentinel monitor moxnas-master 10.0.1.10 6379 2
sentinel auth-pass moxnas-master your-redis-password
sentinel down-after-milliseconds moxnas-master 30000
sentinel parallel-syncs moxnas-master 1
sentinel failover-timeout moxnas-master 180000
```

#### Application Configuration for Redis Sentinel

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': [
            'redis://10.0.1.10:26379/1',
            'redis://10.0.1.11:26379/1',
            'redis://10.0.1.12:26379/1',
        ],
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.SentinelClient',
            'CONNECTION_POOL_KWARGS': {
                'service_name': 'moxnas-master',
                'password': 'your-redis-password',
            },
        },
    }
}
```

## Backup and Disaster Recovery

### Automated Backup Script

```bash
#!/bin/bash
# /opt/scripts/backup-moxnas.sh

set -euo pipefail

# Configuration
BACKUP_DIR="/mnt/backup/moxnas"
RETENTION_DAYS=30
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "${BACKUP_DIR}/${DATE}"

# Backup database
echo "Backing up database..."
docker-compose exec -T db pg_dump -U moxnas moxnas | gzip > "${BACKUP_DIR}/${DATE}/database.sql.gz"

# Backup application data
echo "Backing up application data..."
docker-compose exec -T app tar czf - /app/data | cat > "${BACKUP_DIR}/${DATE}/app_data.tar.gz"

# Backup configuration
echo "Backing up configuration..."
tar czf "${BACKUP_DIR}/${DATE}/config.tar.gz" \
  docker-compose.production.yml \
  .env \
  config/

# Backup storage (if using ZFS)
if command -v zfs &> /dev/null; then
    echo "Creating ZFS snapshot..."
    zfs snapshot tank/storage@backup-${DATE}
    zfs send tank/storage@backup-${DATE} | gzip > "${BACKUP_DIR}/${DATE}/storage.zfs.gz"
fi

# Cleanup old backups
echo "Cleaning up old backups..."
find "${BACKUP_DIR}" -type d -mtime +${RETENTION_DAYS} -exec rm -rf {} +

# Upload to cloud storage (optional)
if [[ -n "${AWS_S3_BUCKET:-}" ]]; then
    echo "Uploading to S3..."
    aws s3 sync "${BACKUP_DIR}/${DATE}" "s3://${AWS_S3_BUCKET}/moxnas-backups/${DATE}/"
fi

echo "Backup completed: ${BACKUP_DIR}/${DATE}"
```

### Restore Procedure

```bash
#!/bin/bash
# /opt/scripts/restore-moxnas.sh

set -euo pipefail

BACKUP_DATE="${1:-latest}"
BACKUP_DIR="/mnt/backup/moxnas"

if [[ "${BACKUP_DATE}" == "latest" ]]; then
    BACKUP_DATE=$(ls -1 "${BACKUP_DIR}" | sort -r | head -n1)
fi

RESTORE_PATH="${BACKUP_DIR}/${BACKUP_DATE}"

if [[ ! -d "${RESTORE_PATH}" ]]; then
    echo "Backup not found: ${RESTORE_PATH}"
    exit 1
fi

echo "Restoring from backup: ${RESTORE_PATH}"

# Stop services
docker-compose down

# Restore database
echo "Restoring database..."
docker-compose up -d db
sleep 30
zcat "${RESTORE_PATH}/database.sql.gz" | docker-compose exec -T db psql -U moxnas -d moxnas

# Restore application data
echo "Restoring application data..."
cat "${RESTORE_PATH}/app_data.tar.gz" | docker-compose exec -T app tar xzf - -C /

# Restore configuration
echo "Restoring configuration..."
tar xzf "${RESTORE_PATH}/config.tar.gz"

# Restore storage (if using ZFS)
if [[ -f "${RESTORE_PATH}/storage.zfs.gz" ]]; then
    echo "Restoring ZFS dataset..."
    zfs destroy tank/storage
    zcat "${RESTORE_PATH}/storage.zfs.gz" | zfs receive tank/storage
fi

# Start services
docker-compose up -d

echo "Restore completed from: ${RESTORE_PATH}"
```

## Security Hardening

### Network Security

#### Firewall Rules (UFW)

```bash
# Reset firewall
sudo ufw --force reset

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# SSH access
sudo ufw allow 22/tcp

# Web services
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# NAS services (restrict to internal network)
sudo ufw allow from 192.168.0.0/16 to any port 139
sudo ufw allow from 192.168.0.0/16 to any port 445
sudo ufw allow from 192.168.0.0/16 to any port 2049
sudo ufw allow from 192.168.0.0/16 to any port 21

# Monitoring (restrict to management network)
sudo ufw allow from 10.0.0.0/8 to any port 9090
sudo ufw allow from 10.0.0.0/8 to any port 3000

# Enable firewall
sudo ufw enable
```

#### SSL/TLS Configuration

```nginx
# config/nginx/ssl.conf
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
ssl_session_tickets off;

# HSTS
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";

# Security headers
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
add_header X-XSS-Protection "1; mode=block";
add_header Referrer-Policy "strict-origin-when-cross-origin";
```

### Application Security

#### Environment Variable Security

```bash
# Use Docker secrets for sensitive data
echo "your-secret-key" | docker secret create moxnas_secret_key -
echo "your-db-password" | docker secret create moxnas_db_password -

# Update docker-compose.yml
services:
  app:
    secrets:
      - moxnas_secret_key
      - moxnas_db_password
    environment:
      - SECRET_KEY_FILE=/run/secrets/moxnas_secret_key
      - DB_PASSWORD_FILE=/run/secrets/moxnas_db_password

secrets:
  moxnas_secret_key:
    external: true
  moxnas_db_password:
    external: true
```

#### Container Security

```dockerfile
# Dockerfile.optimized
FROM python:3.9-slim AS production

# Create non-root user
RUN groupadd -r moxnas && useradd --no-log-init -r -g moxnas moxnas

# Install security updates
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

# Set security options
USER moxnas
WORKDIR /app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8000/api/system/health/ || exit 1

# Run with non-root user
EXPOSE 8000
CMD ["gunicorn", "moxnas.wsgi:application", "--bind", "0.0.0.0:8000"]
```

### Access Control

#### Role-Based Access Control

```python
# backend/apps/users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('operator', 'Operator'),
        ('user', 'User'),
        ('readonly', 'Read Only'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    department = models.CharField(max_length=100, blank=True)
    last_password_change = models.DateTimeField(auto_now_add=True)
    failed_login_attempts = models.IntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)

class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=100)
    resource = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
    success = models.BooleanField(default=True)
    details = models.JSONField(default=dict)
```

## Performance Optimization

### Database Optimization

```postgresql
-- PostgreSQL tuning (postgresql.conf)
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 4MB
min_wal_size = 1GB
max_wal_size = 4GB
```

### Application Optimization

```python
# settings.py production optimizations
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'OPTIONS': {
            'MAX_CONNS': 20,
            'MIN_CONNS': 5,
            'CONN_MAX_AGE': 600,
        },
    }
}

# Cache configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://redis:6379/0',
        'OPTIONS': {
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
        },
    }
}

# Static file optimization
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True
```

### Nginx Optimization

```nginx
# config/nginx/nginx.conf
worker_processes auto;
worker_connections 1024;
worker_rlimit_nofile 2048;

# Performance optimizations
sendfile on;
tcp_nopush on;
tcp_nodelay on;
keepalive_timeout 65;
types_hash_max_size 2048;

# Gzip compression
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types
    text/plain
    text/css
    text/xml
    text/javascript
    application/javascript
    application/xml+rss
    application/json;

# Caching
location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# Rate limiting
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
location /api/ {
    limit_req zone=api burst=20 nodelay;
}
```

## Maintenance and Operations

### Scheduled Maintenance Tasks

```bash
# /etc/cron.d/moxnas-maintenance
# Daily backup at 2 AM
0 2 * * * root /opt/scripts/backup-moxnas.sh

# Weekly cleanup at 3 AM Sunday
0 3 * * 0 root /opt/scripts/cleanup-logs.sh

# Monthly security updates at 4 AM on 1st
0 4 1 * * root /opt/scripts/security-updates.sh

# Health check every 5 minutes
*/5 * * * * root /opt/scripts/health-check.sh
```

### Log Management

```bash
#!/bin/bash
# /opt/scripts/cleanup-logs.sh

# Rotate application logs
find /var/log/moxnas -name "*.log" -size +100M -exec logrotate -f /etc/logrotate.d/moxnas {} \;

# Clean old Docker logs
docker system prune -af --filter "until=72h"

# Clean old backup files
find /mnt/backup -type f -mtime +30 -delete

# Clean temporary files
find /tmp -type f -mtime +7 -delete

echo "Log cleanup completed at $(date)"
```

### Update Procedures

```bash
#!/bin/bash
# /opt/scripts/update-moxnas.sh

set -euo pipefail

# Backup before update
/opt/scripts/backup-moxnas.sh

# Pull latest images
docker-compose -f docker-compose.production.yml pull

# Update services with rolling update
docker-compose -f docker-compose.production.yml up -d --no-deps app

# Wait for health check
sleep 30
if ! curl -f http://localhost/api/system/health/; then
    echo "Health check failed, rolling back..."
    docker-compose -f docker-compose.production.yml rollback
    exit 1
fi

# Update database
docker-compose exec app python manage.py migrate

# Restart remaining services
docker-compose -f docker-compose.production.yml restart nginx prometheus grafana

echo "Update completed successfully"
```

## Troubleshooting

### Common Production Issues

#### Service Discovery Issues

```bash
# Check service connectivity
docker-compose exec app ping db
docker-compose exec app ping redis

# Check DNS resolution
docker-compose exec app nslookup db
docker-compose exec app nslookup redis

# Check port connectivity
docker-compose exec app nc -zv db 5432
docker-compose exec app nc -zv redis 6379
```

#### Performance Issues

```bash
# Monitor resource usage
docker stats

# Check application metrics
curl http://localhost/api/system/metrics/

# Database performance
docker-compose exec db psql -U moxnas -c "SELECT * FROM pg_stat_activity;"

# Redis performance
docker-compose exec redis redis-cli info stats
```

#### Storage Issues

```bash
# Check disk space
df -h

# Check ZFS pool status
zpool status

# Check mount points
mount | grep moxnas

# Check file permissions
ls -la /mnt/storage
```

### Disaster Recovery Procedures

#### Complete System Recovery

1. **Assess Damage**: Determine scope of failure
2. **Restore Infrastructure**: Deploy clean environment
3. **Restore Data**: Apply latest backup
4. **Validate Services**: Verify all services functional
5. **Resume Operations**: Switch traffic to recovered system

#### Service-Specific Recovery

```bash
# Database recovery
docker-compose stop app
docker-compose exec db pg_restore -U moxnas -d moxnas /backup/database.dump
docker-compose start app

# Application recovery
docker-compose pull app
docker-compose up -d app

# Storage recovery
zfs rollback tank/storage@latest-snapshot
```

For additional support and troubleshooting resources, refer to the [Technical Documentation](technical-documentation.md) and [User Guide](user-guide.md).