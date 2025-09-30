#!/bin/bash

# Docker Setup Script for OSAA Data Pipeline
# This script sets up the application for local Docker deployment

set -e

echo "🐳 Setting up OSAA Data Pipeline for Docker deployment..."

# Create necessary directories
echo "📁 Creating local directories..."
mkdir -p data/raw data/staging data/master output sqlMesh

# Create .env file from template if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "✅ Created .env file. Please update the values as needed."
else
    echo "ℹ️  .env file already exists, skipping creation."
fi

# Set permissions for entrypoint script
chmod +x entrypoint.sh

# Build Docker image
echo "🔨 Building Docker image..."
docker build -t osaa-data-pipeline:latest .

echo ""
echo "✅ Docker setup completed!"
echo ""
echo "🚀 Available commands:"
echo "   docker-compose up -d          # Start the application"
echo "   docker-compose down           # Stop the application"
echo "   docker-compose logs -f        # View logs"
echo "   docker-compose exec osaa-data-pipeline bash  # Access container shell"
echo ""
echo "🌐 Access the application at: http://localhost:8080"
echo "   Default credentials: admin / ChangeThisPassword123!"
echo ""
echo "📁 Local data will be stored in:"
echo "   - ./data/     (input data)"
echo "   - ./output/   (processed results)"
echo "   - ./sqlMesh/  (database files)"
