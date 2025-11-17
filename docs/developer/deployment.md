# Deployment Guide

## Overview

This guide covers deploying Insanity Cluster to various environments, from development to production.

## Deployment Options

### 1. Docker Compose (Recommended for Development)
### 2. Kubernetes (Recommended for Production)
### 3. Docker Swarm (Alternative for Production)
### 4. Manual Deployment (Not Recommended)

## Docker Compose Deployment

### Development Environment

**Prerequisites:**
- Docker 20.10+
- Docker Compose 2.0+
- 8GB RAM minimum
- 20GB disk space

**Steps:**

1. **Clone repository:**
```bash
git clone https://github.com/insanity-cluster/insanity-cluster.git
cd insanity-cluster
```

2. **Configure environment:**
```bash
cp .env.template .env
nano .env  # Edit configuration
```

3. **Start services:**
```bash
docker-compose up -d
```

4. **Verify deployment:**
```bash
docker-compose ps
curl http://localhost:8000/health
```

5. **View logs:**
```bash
docker-compose logs -f
```

### Production Environment

**docker-compose.prod.yml:**

```yaml
version: '3.8'

services:
  surface:
    image: insanity-cluster/surface:latest
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  inner:
    image: insanity-cluster/inner:latest
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '4'
          memory: 4G
    environment:
      - ENVIRONMENT=production
    restart: always

  crust:
    image: insanity-cluster/crust:latest
    deploy:
      replicas: 10
      resources:
        limits:
          cpus: '2'
          memory: 2G
    environment:
      - ENVIRONMENT=production
    restart: always

  postgres:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
    restart: always

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
    restart: always

  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdrant_data:/qdrant/storage
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
    restart: always

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - surface
    restart: always

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
```

**Deploy:**

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Kubernetes Deployment

### Prerequisites

- Kubernetes 1.24+
- kubectl configured
- Helm 3.0+ (optional)
- 16GB RAM minimum per node
- 100GB disk space

### Namespace Setup

```bash
kubectl apply -f k8s/namespace.yaml
```

**k8s/namespace.yaml:**
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: insanity-cluster
```

### Secrets

```bash
# Create secrets
kubectl create secret generic insanity-cluster-secrets \
  --from-literal=postgres-password=your-password \
  --from-literal=openai-api-key=sk-... \
  --from-literal=anthropic-api-key=sk-ant-... \
  -n insanity-cluster
```

### ConfigMap

```bash
kubectl apply -f k8s/configmap.yaml
```

### Database

```bash
kubectl apply -f k8s/postgres.yaml
```

**k8s/postgres.yaml:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: insanity-cluster
spec:
  ports:
    - port: 5432
  selector:
    app: postgres
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: insanity-cluster
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
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: insanity-cluster-secrets
              key: postgres-password
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "4"
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 100Gi
```

### Redis

```bash
kubectl apply -f k8s/redis.yaml
```

### Qdrant

```bash
kubectl apply -f k8s/qdrant.yaml
```

### Application Services

```bash
# Deploy SURFACE layer
kubectl apply -f k8s/surface.yaml

# Deploy INNER layer
kubectl apply -f k8s/inner.yaml

# Deploy CRUST layer
kubectl apply -f k8s/crust.yaml
```

**k8s/surface.yaml:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: surface
  namespace: insanity-cluster
spec:
  type: LoadBalancer
  ports:
    - port: 80
      targetPort: 8000
  selector:
    app: surface
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: surface
  namespace: insanity-cluster
spec:
  replicas: 3
  selector:
    matchLabels:
      app: surface
  template:
    metadata:
      labels:
        app: surface
    spec:
      containers:
      - name: surface
        image: insanity-cluster/surface:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          value: postgresql://postgres:5432/insanity_cluster
        - name: REDIS_URL
          value: redis://redis:6379
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: insanity-cluster-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "1Gi"
            cpu: "1"
          limits:
            memory: "2Gi"
            cpu: "2"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

### Ingress

```bash
kubectl apply -f k8s/ingress.yaml
```

**k8s/ingress.yaml:**
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: insanity-cluster-ingress
  namespace: insanity-cluster
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.insanitycluster.com
    secretName: insanity-cluster-tls
  rules:
  - host: api.insanitycluster.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: surface
            port:
              number: 80
```

### Auto-scaling

```bash
kubectl apply -f k8s/hpa.yaml
```

**k8s/hpa.yaml:**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: crust-hpa
  namespace: insanity-cluster
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: crust
  minReplicas: 5
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Verify Deployment

```bash
# Check pods
kubectl get pods -n insanity-cluster

# Check services
kubectl get svc -n insanity-cluster

# Check logs
kubectl logs -f deployment/surface -n insanity-cluster

# Test API
curl https://api.insanitycluster.com/health
```

## CI/CD Pipeline

### GitHub Actions

**.github/workflows/ci.yml:**

```yaml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-cov
    
    - name: Run tests
      run: |
        pytest --cov=insanity_cluster --cov-report=xml
      env:
        DATABASE_URL: postgresql://postgres:test@localhost:5432/test
        REDIS_URL: redis://localhost:6379
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  lint:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install linters
      run: |
        pip install black flake8 mypy
    
    - name: Run black
      run: black --check insanity_cluster
    
    - name: Run flake8
      run: flake8 insanity_cluster
    
    - name: Run mypy
      run: mypy insanity_cluster
```

**.github/workflows/build-and-push.yml:**

```yaml
name: Build and Push

on:
  push:
    branches: [ main ]
    tags: [ 'v*' ]

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2
    
    - name: Login to Docker Hub
      uses: docker/login-action@v2
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}
    
    - name: Build and push SURFACE
      uses: docker/build-push-action@v4
      with:
        context: .
        file: ./Dockerfile.surface
        push: true
        tags: insanity-cluster/surface:latest
    
    - name: Build and push INNER
      uses: docker/build-push-action@v4
      with:
        context: .
        file: ./Dockerfile.inner
        push: true
        tags: insanity-cluster/inner:latest
    
    - name: Build and push CRUST
      uses: docker/build-push-action@v4
      with:
        context: .
        file: ./Dockerfile.crust
        push: true
        tags: insanity-cluster/crust:latest
```

**.github/workflows/deploy-production.yml:**

```yaml
name: Deploy to Production

on:
  push:
    tags: [ 'v*' ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure kubectl
      uses: azure/k8s-set-context@v3
      with:
        method: kubeconfig
        kubeconfig: ${{ secrets.KUBE_CONFIG }}
    
    - name: Deploy to Kubernetes
      run: |
        kubectl set image deployment/surface surface=insanity-cluster/surface:${{ github.ref_name }} -n insanity-cluster
        kubectl set image deployment/inner inner=insanity-cluster/inner:${{ github.ref_name }} -n insanity-cluster
        kubectl set image deployment/crust crust=insanity-cluster/crust:${{ github.ref_name }} -n insanity-cluster
    
    - name: Wait for rollout
      run: |
        kubectl rollout status deployment/surface -n insanity-cluster
        kubectl rollout status deployment/inner -n insanity-cluster
        kubectl rollout status deployment/crust -n insanity-cluster
    
    - name: Verify deployment
      run: |
        kubectl get pods -n insanity-cluster
        curl -f https://api.insanitycluster.com/health || exit 1
```

## Database Migrations

### Running Migrations

```bash
# Development
docker-compose exec surface alembic upgrade head

# Production (Kubernetes)
kubectl exec -it deployment/surface -n insanity-cluster -- alembic upgrade head
```

### Creating Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "Add new table"

# Review migration
cat alembic/versions/xxx_add_new_table.py

# Apply migration
alembic upgrade head
```

## Monitoring Setup

### Prometheus

```bash
kubectl apply -f k8s/prometheus.yaml
```

### Grafana

```bash
kubectl apply -f k8s/grafana.yaml
```

### Alerts

```yaml
# k8s/prometheus-rules.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-rules
  namespace: insanity-cluster
data:
  alerts.yml: |
    groups:
    - name: insanity-cluster
      rules:
      - alert: HighErrorRate
        expr: rate(errors_total[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High error rate detected"
      
      - alert: HighCost
        expr: cost_per_day > 100
        for: 1h
        annotations:
          summary: "Daily cost exceeds $100"
      
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(task_duration_seconds_bucket[5m])) > 10
        for: 5m
        annotations:
          summary: "95th percentile latency > 10s"
```

## Backup and Recovery

### Database Backup

```bash
# Backup
kubectl exec -it postgres-0 -n insanity-cluster -- pg_dump -U postgres insanity_cluster > backup.sql

# Restore
kubectl exec -i postgres-0 -n insanity-cluster -- psql -U postgres insanity_cluster < backup.sql
```

### Automated Backups

```yaml
# k8s/backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: insanity-cluster
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:15
            command:
            - /bin/sh
            - -c
            - pg_dump -U postgres -h postgres insanity_cluster | gzip > /backup/backup-$(date +%Y%m%d).sql.gz
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
          restartPolicy: OnFailure
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
```

## Security Hardening

### TLS/SSL

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer
kubectl apply -f k8s/cluster-issuer.yaml
```

### Network Policies

```yaml
# k8s/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: surface-policy
  namespace: insanity-cluster
spec:
  podSelector:
    matchLabels:
      app: surface
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
```

## Troubleshooting Deployment

### Common Issues

**Pods not starting:**
```bash
kubectl describe pod <pod-name> -n insanity-cluster
kubectl logs <pod-name> -n insanity-cluster
```

**Database connection issues:**
```bash
kubectl exec -it deployment/surface -n insanity-cluster -- env | grep DATABASE
kubectl exec -it postgres-0 -n insanity-cluster -- psql -U postgres -c "SELECT 1"
```

**High memory usage:**
```bash
kubectl top pods -n insanity-cluster
kubectl describe node <node-name>
```

## Rollback

### Docker Compose

```bash
# Rollback to previous version
docker-compose down
git checkout <previous-tag>
docker-compose up -d
```

### Kubernetes

```bash
# Rollback deployment
kubectl rollout undo deployment/surface -n insanity-cluster

# Rollback to specific revision
kubectl rollout undo deployment/surface --to-revision=2 -n insanity-cluster

# Check rollout history
kubectl rollout history deployment/surface -n insanity-cluster
```

## Support

For deployment help:
- Documentation: https://docs.insanitycluster.com/deployment
- Discord: https://discord.gg/insanity-cluster
- Email: devops@insanitycluster.com
