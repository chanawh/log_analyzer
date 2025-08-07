#!/usr/bin/env python3
"""
Log Analyzer CLI Tool
A comprehensive CLI for managing and monitoring the Log Analyzer application.
"""

import click
import subprocess
import yaml
import json
import requests
import time
from pathlib import Path


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """Log Analyzer CLI - Manage your log analysis infrastructure."""
    pass


@cli.group()
def k8s():
    """Kubernetes cluster management commands."""
    pass


@cli.group()
def monitor():
    """Monitoring and health check commands."""
    pass


@cli.group()
def deploy():
    """Deployment management commands."""
    pass


@k8s.command()
@click.option('--namespace', '-n', default='log-analyzer', help='Kubernetes namespace')
@click.option('--output', '-o', type=click.Choice(['table', 'json', 'yaml']), default='table')
def status(namespace, output):
    """Check the status of all Kubernetes resources."""
    try:
        # Get pods
        result = subprocess.run([
            'kubectl', 'get', 'pods', 
            '-n', namespace, 
            '-o', 'json'
        ], capture_output=True, text=True, check=True)
        
        pods_data = json.loads(result.stdout)
        
        if output == 'json':
            click.echo(json.dumps(pods_data, indent=2))
        elif output == 'yaml':
            click.echo(yaml.dump(pods_data, default_flow_style=False))
        else:
            # Table output
            click.echo(f"{'NAME':<40} {'STATUS':<15} {'RESTARTS':<10} {'AGE':<10}")
            click.echo("-" * 80)
            
            for pod in pods_data['items']:
                name = pod['metadata']['name']
                status = pod['status']['phase']
                restarts = sum(c.get('restartCount', 0) for c in pod['status'].get('containerStatuses', []))
                age = pod['metadata']['creationTimestamp']
                
                click.echo(f"{name:<40} {status:<15} {restarts:<10} {age:<10}")
    
    except subprocess.CalledProcessError as e:
        click.echo(f"Error: {e.stderr}", err=True)
        raise click.Abort()


@k8s.command()
@click.option('--namespace', '-n', default='log-analyzer', help='Kubernetes namespace')
@click.argument('pod_name')
def logs(namespace, pod_name):
    """Get logs from a specific pod."""
    try:
        subprocess.run([
            'kubectl', 'logs', pod_name, 
            '-n', namespace, 
            '--follow'
        ], check=True)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error getting logs: {e}", err=True)
        raise click.Abort()


@k8s.command()
@click.option('--namespace', '-n', default='log-analyzer', help='Kubernetes namespace')
@click.argument('pod_name')
def exec(namespace, pod_name):
    """Execute into a pod."""
    try:
        subprocess.run([
            'kubectl', 'exec', '-it', pod_name, 
            '-n', namespace,
            '--', '/bin/sh'
        ], check=True)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error executing into pod: {e}", err=True)
        raise click.Abort()


@monitor.command()
@click.option('--url', default='http://localhost:5000', help='Application URL')
def health(url):
    """Check application health."""
    try:
        response = requests.get(f"{url}/health", timeout=10)
        response.raise_for_status()
        
        health_data = response.json()
        
        click.echo("🏥 Health Check Results:")
        click.echo(f"Status: {'✅ ' + health_data['status'].upper() if health_data['status'] == 'healthy' else '❌ ' + health_data['status'].upper()}")
        click.echo(f"Service: {health_data['service']}")
        click.echo(f"Version: {health_data['version']}")
        click.echo(f"Modules: {', '.join(health_data['modules'])}")
        
    except requests.exceptions.RequestException as e:
        click.echo(f"❌ Health check failed: {e}", err=True)
        raise click.Abort()


@monitor.command()
@click.option('--url', default='http://localhost:5000', help='Application URL')
def metrics(url):
    """Get application metrics."""
    try:
        response = requests.get(f"{url}/metrics", timeout=10)
        response.raise_for_status()
        
        click.echo("📊 Application Metrics:")
        click.echo(response.text)
        
    except requests.exceptions.RequestException as e:
        click.echo(f"❌ Metrics retrieval failed: {e}", err=True)
        raise click.Abort()


@deploy.command()
@click.option('--environment', '-e', type=click.Choice(['development', 'staging', 'production']), 
              default='development', help='Deployment environment')
@click.option('--namespace', '-n', help='Kubernetes namespace (defaults to environment name)')
def install(environment, namespace):
    """Install Log Analyzer using Helm."""
    if not namespace:
        namespace = f"log-analyzer-{environment}"
    
    try:
        # Create namespace if it doesn't exist
        subprocess.run([
            'kubectl', 'create', 'namespace', namespace
        ], check=False)  # Don't fail if namespace exists
        
        # Install using Helm
        helm_cmd = [
            'helm', 'upgrade', '--install', 'log-analyzer',
            './helm/log-analyzer',
            '--namespace', namespace,
            '--values', f'./helm/log-analyzer/values-{environment}.yaml',
            '--wait', '--timeout', '10m'
        ]
        
        click.echo(f"🚀 Installing Log Analyzer in {environment} environment...")
        subprocess.run(helm_cmd, check=True)
        
        click.echo(f"✅ Successfully deployed to {namespace} namespace!")
        
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Deployment failed: {e}", err=True)
        raise click.Abort()


@deploy.command()
@click.option('--environment', '-e', type=click.Choice(['development', 'staging', 'production']), 
              default='development', help='Deployment environment')
@click.option('--namespace', '-n', help='Kubernetes namespace (defaults to environment name)')
def uninstall(environment, namespace):
    """Uninstall Log Analyzer using Helm."""
    if not namespace:
        namespace = f"log-analyzer-{environment}"
    
    try:
        subprocess.run([
            'helm', 'uninstall', 'log-analyzer',
            '--namespace', namespace
        ], check=True)
        
        click.echo(f"✅ Successfully uninstalled from {namespace} namespace!")
        
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Uninstall failed: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--scenario', type=click.Choice(['pod-crash', 'oom', 'high-cpu', 'network-issue']),
              required=True, help='Failure scenario to simulate')
@click.option('--namespace', '-n', default='log-analyzer', help='Kubernetes namespace')
def simulate(scenario, namespace):
    """Simulate failure scenarios for testing."""
    click.echo(f"🎭 Simulating {scenario} scenario...")
    
    scenarios = {
        'pod-crash': _simulate_pod_crash,
        'oom': _simulate_oom,
        'high-cpu': _simulate_high_cpu,
        'network-issue': _simulate_network_issue
    }
    
    if scenario in scenarios:
        scenarios[scenario](namespace)
    else:
        click.echo(f"Unknown scenario: {scenario}")


def _simulate_pod_crash(namespace):
    """Simulate a pod crash."""
    try:
        # Get a random pod
        result = subprocess.run([
            'kubectl', 'get', 'pods', '-n', namespace,
            '-o', 'jsonpath={.items[0].metadata.name}'
        ], capture_output=True, text=True, check=True)
        
        pod_name = result.stdout.strip()
        if pod_name:
            subprocess.run([
                'kubectl', 'delete', 'pod', pod_name, '-n', namespace
            ], check=True)
            click.echo(f"💥 Simulated crash for pod: {pod_name}")
        else:
            click.echo("No pods found to crash")
            
    except subprocess.CalledProcessError as e:
        click.echo(f"Error simulating pod crash: {e}", err=True)


def _simulate_oom(namespace):
    """Simulate out of memory condition."""
    click.echo("🧠 Creating memory pressure...")
    # Implementation would deploy a memory-intensive job


def _simulate_high_cpu(namespace):
    """Simulate high CPU usage."""
    click.echo("🔥 Creating CPU pressure...")
    # Implementation would deploy a CPU-intensive job


def _simulate_network_issue(namespace):
    """Simulate network connectivity issues."""
    click.echo("🌐 Simulating network issues...")
    # Implementation would create network policies or chaos


if __name__ == '__main__':
    cli()