# Log Analyzer Troubleshooting Guide

## Common Issues and Solutions

### 1. Pod Crash Loop

**Symptoms:**
- Pods repeatedly restarting
- Status shows `CrashLoopBackOff`
- High restart count

**Diagnosis:**
```bash
# Check pod status
kubectl get pods -n log-analyzer

# Get pod logs
kubectl logs <pod-name> -n log-analyzer --previous

# Describe pod for events
kubectl describe pod <pod-name> -n log-analyzer
```

**Common Causes & Solutions:**

#### Application Configuration Issues
```bash
# Check configmap values
kubectl get configmap log-analyzer-config -n log-analyzer -o yaml

# Verify secret values
kubectl get secret log-analyzer-secret -n log-analyzer -o yaml
```

#### Resource Limits
```bash
# Check resource usage
kubectl top pods -n log-analyzer

# Increase resource limits in values.yaml:
resources:
  limits:
    cpu: 1000m
    memory: 1Gi
  requests:
    cpu: 200m
    memory: 256Mi
```

### 2. Out of Memory (OOM) Kills

**Symptoms:**
- Pods killed with exit code 137
- `OOMKilled` status in pod events
- Memory usage at 100%

**Diagnosis:**
```bash
# Check memory usage
kubectl top pods -n log-analyzer

# Check events for OOM kills
kubectl get events -n log-analyzer --sort-by='.lastTimestamp'
```

**Solutions:**
```yaml
# Increase memory limits
resources:
  limits:
    memory: 2Gi
  requests:
    memory: 512Mi

# Optimize application memory usage
# - Implement memory cleanup in Python
# - Use connection pooling
# - Limit file upload sizes
```

### 3. High CPU Usage

**Symptoms:**
- CPU usage consistently above 80%
- Slow response times
- HPA scaling to maximum replicas

**Diagnosis:**
```bash
# Monitor CPU usage
kubectl top pods -n log-analyzer
kubectl top nodes

# Check HPA status
kubectl get hpa -n log-analyzer
```

**Solutions:**
```yaml
# Optimize HPA configuration
autoscaling:
  targetCPUUtilizationPercentage: 60
  targetMemoryUtilizationPercentage: 70
  maxReplicas: 15

# Application optimizations:
# - Add Redis caching
# - Optimize SQL queries
# - Use async processing for heavy operations
```

### 4. Network Connectivity Issues

**Symptoms:**
- Timeouts connecting to external services
- Inter-pod communication failures
- DNS resolution problems

**Diagnosis:**
```bash
# Test DNS resolution
kubectl exec -it <pod-name> -n log-analyzer -- nslookup kubernetes.default

# Check network policies
kubectl get networkpolicies -n log-analyzer

# Test connectivity
kubectl exec -it <pod-name> -n log-analyzer -- curl http://redis-service:6379
```

**Solutions:**
```bash
# Check service endpoints
kubectl get endpoints -n log-analyzer

# Verify service selector labels
kubectl get pods -n log-analyzer --show-labels
kubectl get service log-analyzer-service -n log-analyzer -o yaml

# Check network policies
kubectl describe networkpolicy -n log-analyzer
```

### 5. Storage Issues

**Symptoms:**
- PVC stuck in `Pending` state
- "No space left on device" errors
- File upload failures

**Diagnosis:**
```bash
# Check PVC status
kubectl get pvc -n log-analyzer

# Check storage class
kubectl get storageclass

# Check disk usage in pods
kubectl exec -it <pod-name> -n log-analyzer -- df -h
```

**Solutions:**
```yaml
# Increase PVC size
persistence:
  uploads:
    size: 20Gi
  logs:
    size: 50Gi

# Use different storage class
persistence:
  uploads:
    storageClass: fast-ssd
```

### 6. Database Connection Issues

**Symptoms:**
- SQL operations failing
- Redis connection timeouts
- Database lock errors

**Diagnosis:**
```bash
# Check Redis connectivity
kubectl exec -it <redis-pod> -n log-analyzer -- redis-cli ping

# Check database files
kubectl exec -it <pod-name> -n log-analyzer -- ls -la /app/logs/

# Monitor database operations
kubectl logs <pod-name> -n log-analyzer | grep -i sql
```

**Solutions:**
```yaml
# Configure Redis properly
redis:
  master:
    persistence:
      enabled: true
    resources:
      limits:
        memory: 512Mi

# Add connection pooling
# Implement retry logic
# Use read replicas for heavy queries
```

### 7. Prometheus Metrics Issues

**Symptoms:**
- Missing metrics in Grafana
- Prometheus scraping failures
- Incorrect metric values

**Diagnosis:**
```bash
# Check Prometheus targets
kubectl port-forward svc/prometheus 9090:9090 -n monitoring
# Visit http://localhost:9090/targets

# Check metrics endpoint
kubectl exec -it <pod-name> -n log-analyzer -- curl http://localhost:5000/metrics

# Verify service annotations
kubectl get service log-analyzer-service -n log-analyzer -o yaml
```

**Solutions:**
```yaml
# Ensure proper annotations
metadata:
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "5000"
    prometheus.io/path: "/metrics"

# Check metric registration in application
# Verify Prometheus configuration
```

## Emergency Procedures

### Quick Recovery Commands

```bash
# Restart all pods
kubectl rollout restart deployment/log-analyzer -n log-analyzer

# Scale down and up
kubectl scale deployment log-analyzer --replicas=0 -n log-analyzer
kubectl scale deployment log-analyzer --replicas=3 -n log-analyzer

# Force pod recreation
kubectl delete pods -l app.kubernetes.io/name=log-analyzer -n log-analyzer

# Check cluster node health
kubectl get nodes
kubectl describe nodes
```

### Log Collection for Support

```bash
#!/bin/bash
# collect-logs.sh - Collect logs for support

NAMESPACE="log-analyzer"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
OUTPUT_DIR="logs-${TIMESTAMP}"

mkdir -p ${OUTPUT_DIR}

# Collect pod logs
kubectl logs -l app.kubernetes.io/name=log-analyzer -n ${NAMESPACE} --previous > ${OUTPUT_DIR}/pod-logs-previous.txt
kubectl logs -l app.kubernetes.io/name=log-analyzer -n ${NAMESPACE} > ${OUTPUT_DIR}/pod-logs-current.txt

# Collect events
kubectl get events -n ${NAMESPACE} --sort-by='.lastTimestamp' > ${OUTPUT_DIR}/events.txt

# Collect resource status
kubectl get all -n ${NAMESPACE} -o yaml > ${OUTPUT_DIR}/resources.yaml

# Collect metrics
kubectl top pods -n ${NAMESPACE} > ${OUTPUT_DIR}/pod-metrics.txt
kubectl top nodes > ${OUTPUT_DIR}/node-metrics.txt

# Create archive
tar -czf "support-logs-${TIMESTAMP}.tar.gz" ${OUTPUT_DIR}
echo "Logs collected in: support-logs-${TIMESTAMP}.tar.gz"
```

## Performance Tuning

### Application Level
- Enable Redis caching
- Optimize SQL queries
- Implement async processing
- Use connection pooling
- Add request/response caching

### Kubernetes Level
- Tune resource requests/limits
- Configure HPA properly
- Use node affinity/anti-affinity
- Implement pod disruption budgets
- Optimize storage classes

### Infrastructure Level
- Use faster storage (SSD)
- Increase node sizes
- Configure cluster autoscaling
- Optimize network policies
- Use load balancer session affinity