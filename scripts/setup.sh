#!/bin/bash

# CostByte Setup Script
# For Windows 10 Pro, Dell i7, 16GB RAM, 1TB SSD

echo "🚀 Setting up CostByte AI Job Application System"
echo "================================================"

# Check if running as administrator/root
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  Please run as administrator/root"
    exit 1
fi

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="Linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="Mac"
elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    OS="Windows"
else
    OS="Unknown"
fi

echo "📋 Detected OS: $OS"

# Install prerequisites
echo "📦 Installing prerequisites..."

if [ "$OS" == "Linux" ]; then
    # Ubuntu/Debian
    apt-get update
    apt-get install -y \
        curl \
        wget \
        git \
        python3 \
        python3-pip \
        python3-venv \
        nodejs \
        npm \
        docker.io \
        docker-compose \
        nginx \
        postgresql \
        redis-server \
        libpq-dev \
        build-essential \
        libssl-dev \
        libffi-dev \
        python3-dev
    
    systemctl enable docker
    systemctl start docker
    
elif [ "$OS" == "Windows" ]; then
    # Windows
    echo "📥 Please install the following manually:"
    echo "  1. Docker Desktop for Windows"
    echo "  2. Python 3.10+"
    echo "  3. Node.js 18+"
    echo "  4. Git for Windows"
    echo "  5. PostgreSQL 15"
    echo ""
    read -p "Press Enter after installations complete..."
fi

# Clone repository
echo "📥 Cloning CostByte repository..."
git clone https://github.com/costbyte/ai-job-system.git /opt/costbyte
cd /opt/costbyte

# Create virtual environment
echo "🐍 Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
cd frontend
npm install
cd ..

# Setup environment file
echo "⚙️  Configuring environment..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "📝 Please edit .env file with your configuration"
    echo "   Open .env and fill in all required values"
    read -p "Press Enter after editing .env file..."
fi

# Setup database
echo "🗄️  Setting up database..."
source .env
createdb -U postgres costbyte 2>/dev/null || true

# Run migrations
echo "🔄 Running migrations..."
python manage.py migrate

# Create superuser
echo "👑 Creating superuser..."
python manage.py createsuperuser --noinput --username admin --email admin@costbyte.co.za 2>/dev/null || true

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Setup SSL certificates
echo "🔒 Setting up SSL..."
mkdir -p infrastructure/docker/ssl
cd infrastructure/docker/ssl

# Generate self-signed certificate for development
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout costbyte.key \
    -out costbyte.crt \
    -subj "/C=ZA/ST=Gauteng/L=Johannesburg/O=CostByte/CN=costbyte.local"

cd ../../..

# Setup firewall
echo "🛡️  Configuring firewall..."
if [ "$OS" == "Linux" ]; then
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw allow 8000/tcp
    ufw allow 3000/tcp
    ufw --force enable
fi

# Setup systemd services
echo "🔄 Setting up system services..."
if [ "$OS" == "Linux" ]; then
    cat > /etc/systemd/system/costbyte-backend.service << EOF
[Unit]
Description=CostByte Backend Service
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=costbyte
Group=costbyte
WorkingDirectory=/opt/costbyte
EnvironmentFile=/opt/costbyte/.env
ExecStart=/opt/costbyte/venv/bin/gunicorn backend.core.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --threads 4 \
    --timeout 120
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    cat > /etc/systemd/system/costbyte-celery.service << EOF
[Unit]
Description=CostByte Celery Worker
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=costbyte
Group=costbyte
WorkingDirectory=/opt/costbyte
EnvironmentFile=/opt/costbyte/.env
ExecStart=/opt/costbyte/venv/bin/celery -A backend.core worker --loglevel=info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    cat > /etc/systemd/system/costbyte-celery-beat.service << EOF
[Unit]
Description=CostByte Celery Beat
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=costbyte
Group=costbyte
WorkingDirectory=/opt/costbyte
EnvironmentFile=/opt/costbyte/.env
ExecStart=/opt/costbyte/venv/bin/celery -A backend.core beat --loglevel=info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # Create costbyte user
    useradd -r -s /bin/false costbyte
    chown -R costbyte:costbyte /opt/costbyte
    
    # Enable services
    systemctl daemon-reload
    systemctl enable costbyte-backend
    systemctl enable costbyte-celery
    systemctl enable costbyte-celery-beat
    
    echo "✅ Systemd services configured"
fi

# Setup Nginx
echo "🌐 Configuring Nginx..."
if [ "$OS" == "Linux" ]; then
    cp infrastructure/nginx/sites-available/costbyte.conf /etc/nginx/sites-available/
    ln -sf /etc/nginx/sites-available/costbyte.conf /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    # Test Nginx configuration
    nginx -t
    systemctl restart nginx
fi

# Setup monitoring
echo "📊 Setting up monitoring..."
mkdir -p /opt/costbyte/logs
mkdir -p /opt/costbyte/media

# Setup backup cron job
echo "💾 Setting up backups..."
cat > /etc/cron.d/costbyte-backup << EOF
0 2 * * * costbyte /opt/costbyte/scripts/backup.sh >> /opt/costbyte/logs/backup.log 2>&1
0 3 * * 0 costbyte /opt/costbyte/scripts/cleanup.sh >> /opt/costbyte/logs/cleanup.log 2>&1
EOF

# Initialize AI models
echo "🤖 Initializing AI models..."
cd /opt/costbyte/ai_services
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

# Start services
echo "🚀 Starting services..."
if [ "$OS" == "Linux" ]; then
    systemctl start costbyte-backend
    systemctl start costbyte-celery
    systemctl start costbyte-celery-beat
    
    # Start frontend in background
    cd /opt/costbyte/frontend
    npm run build
    serve -s build -l 3000 &
    
    # Start AI services
    cd /opt/costbyte/ai_services
    python main.py &
fi

echo ""
echo "🎉 CostByte Setup Complete!"
echo "============================"
echo ""
echo "📱 Access URLs:"
echo "   Frontend:    http://localhost:3000"
echo "   Backend API: http://localhost:8000"
echo "   Admin Panel: http://localhost:8000/admin"
echo ""
echo "🔧 Default Admin Credentials:"
echo "   Username: admin"
echo "   Password: Check .env file"
echo ""
echo "📋 Next Steps:"
echo "   1. Configure payment gateways in .env"
echo "   2. Set up WhatsApp Business API"
echo "   3. Configure AI API keys"
echo "   4. Run tests: ./scripts/test.sh"
echo ""
echo "📞 Support: support@costbyte.co.za"
echo ""
