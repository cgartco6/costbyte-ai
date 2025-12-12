#!/bin/bash
# deploy.sh

echo "🚀 Deploying CostByte System..."

# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Create network
docker network create costbyte-network

# Build and deploy services
docker-compose -f docker-compose.prod.yml up -d --build

# Setup monitoring
docker run -d \
  --name=grafana \
  -p 3000:3000 \
  --network=costbyte-network \
  grafana/grafana

echo "✅ Deployment complete!"
echo "🌐 Access Dashboard: https://dashboard.costbyte.co.za"
