# Log Analyzer - Production-Ready Kubernetes Deployment

[![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white)](https://kubernetes.io/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com/)
[![Helm](https://img.shields.io/badge/Helm-0F1689?style=for-the-badge&logo=helm&logoColor=white)](https://helm.sh/)
[![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?style=for-the-badge&logo=prometheus&logoColor=white)](https://prometheus.io/)
[![Grafana](https://img.shields.io/badge/Grafana-F46800?style=for-the-badge&logo=grafana&logoColor=white)](https://grafana.com/)

A comprehensive, cloud-native log analysis tool with production-grade Kubernetes deployment, monitoring, and observability features.

## 🚀 Features

### Core Application
- **SSH Module**: Connect to remote servers, browse directories, and download files
- **Log Analysis**: Filter, summarize, and analyze log files with advanced search capabilities
- **SQL Module**: Import logs to SQLite database and execute complex queries
- **REST API**: 18 comprehensive endpoints for all operations
- **GUI Interface**: User-friendly Tkinter interface

### Cloud-Native Features
- **Kubernetes-Ready**: Complete K8s manifests with autoscaling and resource management
- **Helm Charts**: Customizable deployment with environment-specific values
- **Multi-Cloud Support**: AWS EKS, GCP GKE, Azure AKS configurations
- **Monitoring Stack**: Prometheus metrics and Grafana dashboards
- **Security**: Pod security contexts, RBAC, network policies
- **Observability**: Structured logging, distributed tracing, alerting

## 📊 Architecture

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐
│    Users    │───▶│ Load Balancer/   │───▶│ Log Analyzer    │
│             │    │ Ingress          │    │ API Pods        │
└─────────────┘    └──────────────────┘    └─────────────────┘
                                                     │
                                           ┌─────────┴─────────┐
                                           │                   │
                                           ▼                   ▼
                                   ┌─────────────┐    ┌─────────────┐
                                   │ Redis Cache │    │ Persistent  │
                                   │             │    │ Storage     │
                                   └─────────────┘    └─────────────┘
                                           │
                   ┌───────────────────────┴───────────────────────┐
                   │                                               │
                   ▼                                               ▼
           ┌─────────────┐                                ┌─────────────┐
           │ Prometheus  │                                │  Grafana    │
           │ Monitoring  │                                │ Dashboards  │
           └─────────────┘                                └─────────────┘
```

## 🛠 Quick Start

### Prerequisites
- Kubernetes cluster (1.24+)
- Helm 3.0+
- kubectl configured
- Docker (for building images)

### 1. Clone Repository
```bash
git clone https://github.com/chanawh/log_analyzer.git
cd log_analyzer
```

### 2. Build Docker Image
```bash
docker build -t log-analyzer:latest .
```

### 3. Deploy with Helm
```bash
# Development environment
helm upgrade --install log-analyzer ./helm/log-analyzer \
  --namespace log-analyzer --create-namespace \
  --values ./helm/log-analyzer/values.yaml

# Production environment  
helm upgrade --install log-analyzer ./helm/log-analyzer \
  --namespace log-analyzer-prod --create-namespace \
  --values ./helm/log-analyzer/values-production.yaml
```

### 4. Access Application
```bash
# Port forward to access locally
kubectl port-forward svc/log-analyzer 8080:80 -n log-analyzer

# Visit http://localhost:8080
```

## 🔧 Configuration

### Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Flask environment | `production` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `REDIS_URL` | Redis connection URL | `redis://redis-service:6379/0` |
| `MAX_CONTENT_LENGTH` | Max upload size | `16777216` (16MB) |

### Helm Values
```yaml
# Custom values.yaml
replicaCount: 5

resources:
  limits:
    cpu: 1000m
    memory: 1Gi
  requests:
    cpu: 200m
    memory: 256Mi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilizationPercentage: 60

persistence:
  uploads:
    size: 20Gi
  logs:
    size: 50Gi
```

## 🏭 Production Deployment

### Cloud Providers

#### AWS EKS
```bash
cd cloud-providers/aws/terraform
terraform init
terraform plan -var="cluster_name=log-analyzer-eks"
terraform apply
```

#### GCP GKE
```bash
cd cloud-providers/gcp/terraform
terraform init
terraform plan -var="project_id=your-project-id"
terraform apply
```

#### Azure AKS
```bash
cd cloud-providers/azure/terraform
terraform init
terraform plan -var="resource_group=log-analyzer-rg"
terraform apply
```

### Monitoring Setup

1. **Deploy Prometheus**
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace
```

2. **Import Grafana Dashboards**
```bash
kubectl apply -f monitoring/grafana/dashboards/
```

3. **Configure Alerting**
```bash
kubectl apply -f monitoring/prometheus/alert_rules.yml
```

## 📊 Monitoring & Observability

### Metrics Available
- HTTP request duration and rate
- Error rates and types
- Resource utilization (CPU, Memory)
- SSH connection statistics
- Log processing metrics
- Database query performance

### Grafana Dashboards
- **Application Overview**: Key metrics and health status
- **Infrastructure**: Node and pod resource usage
- **Business Metrics**: Log processing volume and patterns
- **Alerts**: Active alerts and incident tracking

### Health Checks
```bash
# Application health
curl http://your-domain/health

# Kubernetes health
kubectl get pods -n log-analyzer

# Using CLI tool
./cli/log-analyzer-cli.py monitor health
```

## 🔍 Troubleshooting

### Common Issues

1. **Pod Crash Loops**
```bash
kubectl logs <pod-name> -n log-analyzer --previous
kubectl describe pod <pod-name> -n log-analyzer
```

2. **High Memory Usage**
```bash
kubectl top pods -n log-analyzer
# Increase memory limits in values.yaml
```

3. **Storage Issues**
```bash
kubectl get pvc -n log-analyzer
# Check storage class and available space
```

See [Troubleshooting Guide](docs/troubleshooting/README.md) for detailed solutions.

## 🛡 Security

### Security Features
- **Pod Security Contexts**: Non-root containers with read-only filesystems
- **RBAC**: Least-privilege service accounts
- **Network Policies**: Restricted inter-pod communication
- **Secrets Management**: Encrypted secret storage
- **Image Scanning**: Vulnerability scanning in CI/CD

### Security Hardening
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop:
    - ALL
```

## 🚀 CLI Tools

Use the included CLI for operations:

```bash
# Check cluster status
./cli/log-analyzer-cli.py k8s status

# Monitor health
./cli/log-analyzer-cli.py monitor health

# Deploy to production
./cli/log-analyzer-cli.py deploy install -e production

# Simulate failures for testing
./cli/log-analyzer-cli.py simulate --scenario pod-crash
```

## 📈 Scaling

### Horizontal Pod Autoscaling
```yaml
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilizationPercentage: 60
  targetMemoryUtilizationPercentage: 70
```

### Cluster Autoscaling
- Configured per cloud provider
- Automatic node scaling based on pod demands
- Cost optimization through spot instances

## 🔄 CI/CD Pipeline

### GitOps Workflow
1. Code changes trigger automated builds
2. Docker images pushed to registry
3. Helm charts updated with new versions
4. ArgoCD/Flux deploys to clusters
5. Automated testing and validation

### Deployment Strategies
- **Blue-Green**: Zero-downtime deployments
- **Canary**: Gradual rollout with monitoring
- **Rolling**: Default Kubernetes strategy

## 📚 Documentation

- [API Documentation](API_DOCUMENTATION.md)
- [Deployment Guide](docs/deployment/)
- [Operations Manual](docs/operations/)
- [Troubleshooting Guide](docs/troubleshooting/)

## 🏅 Certifications & Badges

- **Cloud Native**: CNCF Landscape Compatible
- **Security**: OWASP Best Practices
- **Monitoring**: Prometheus Certified
- **Kubernetes**: CKA/CKAD Ready

## 🔧 Optional Integrations

### Rancher Management
```bash
# Add cluster to Rancher
rancher cluster add --name log-analyzer-cluster
```

### Thanos Long-term Storage
```yaml
# Enable Thanos sidecar
prometheus:
  prometheusSpec:
    thanos:
      enabled: true
      objectStorageConfig:
        key: thanos.yaml
        name: thanos-storage-config
```

### DuckDB Analytics
```python
# Enhanced log analytics with DuckDB
import duckdb
conn = duckdb.connect('logs.db')
conn.execute("""
  SELECT COUNT(*), log_level, DATE_TRUNC('hour', timestamp) as hour
  FROM logs 
  WHERE timestamp >= NOW() - INTERVAL '24 hours'
  GROUP BY log_level, hour
  ORDER BY hour;
""")
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/chanawh/log_analyzer/issues)
- **Discussions**: [GitHub Discussions](https://github.com/chanawh/log_analyzer/discussions)
- **Documentation**: [Wiki](https://github.com/chanawh/log_analyzer/wiki)

---

Made with ❤️ for the cloud-native community
