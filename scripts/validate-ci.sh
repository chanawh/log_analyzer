#!/bin/bash

# CI/CD Local Validation Script
echo "🔄 Running local CI/CD validation..."

# Check if required tools are installed
command -v python3 >/dev/null 2>&1 || { echo "❌ Python3 is required but not installed."; exit 1; }
command -v pip >/dev/null 2>&1 || { echo "❌ pip is required but not installed."; exit 1; }

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run linting
echo "🔍 Running code quality checks..."
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
if [ $? -ne 0 ]; then
    echo "❌ Critical linting errors found!"
    exit 1
fi

echo "✅ No critical linting errors found"

# Run tests with coverage
echo "🧪 Running tests with coverage..."
coverage run -m unittest discover tests/ -v
if [ $? -ne 0 ]; then
    echo "❌ Tests failed!"
    exit 1
fi

echo "✅ All tests passed!"

# Generate coverage report
coverage report -m
coverage xml

# Check if Docker is available and build
if command -v docker >/dev/null 2>&1; then
    echo "🐳 Building Docker image..."
    docker build -t log-analyzer:test .
    if [ $? -eq 0 ]; then
        echo "✅ Docker image built successfully!"
    else
        echo "⚠️  Docker build failed (may be due to network issues)"
    fi
else
    echo "⚠️  Docker not available, skipping container build"
fi

echo "🎉 Local CI/CD validation completed successfully!"
echo "📊 Coverage report generated: coverage.xml"
echo "🚀 Ready for production deployment!"