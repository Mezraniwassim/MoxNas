# MoxNAS Docker Container
FROM debian:12-slim

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV NODE_MAJOR=20

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    gnupg2 \
    nginx \
    systemd \
    samba \
    nfs-kernel-server \
    vsftpd \
    openssh-server \
    snmp \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20
RUN curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Create moxnas user
RUN useradd -r -s /bin/bash -d /opt/moxnas -c "MoxNAS Service User" moxnas \
    && mkdir -p /opt/moxnas \
    && chown moxnas:moxnas /opt/moxnas

# Copy application files
COPY --chown=moxnas:moxnas backend/ /opt/moxnas/backend/
COPY --chown=moxnas:moxnas frontend/ /opt/moxnas/frontend/
COPY --chown=moxnas:moxnas requirements.txt /opt/moxnas/
COPY --chown=moxnas:moxnas .env /opt/moxnas/

# Set working directory
WORKDIR /opt/moxnas

# Install Python dependencies
RUN python3 -m venv venv \
    && venv/bin/pip install --no-cache-dir -r requirements.txt

# Build frontend
WORKDIR /opt/moxnas/frontend
RUN npm install \
    && npm run build \
    && rm -rf node_modules

# Setup backend
WORKDIR /opt/moxnas
RUN venv/bin/python backend/manage.py collectstatic --noinput

# Configure nginx for unprivileged container
RUN mkdir -p /var/lib/nginx/body /var/lib/nginx/fastcgi /var/lib/nginx/proxy /var/lib/nginx/scgi /var/lib/nginx/uwsgi \
    && chown -R moxnas:moxnas /var/lib/nginx /var/log/nginx /etc/nginx \
    && touch /var/run/nginx.pid \
    && chown moxnas:moxnas /var/run/nginx.pid

COPY <<EOF /etc/nginx/sites-available/moxnas
server {
    listen 80 default_server;
    server_name _;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /static/ {
        alias /opt/moxnas/backend/staticfiles/;
    }
}
EOF

RUN ln -sf /etc/nginx/sites-available/moxnas /etc/nginx/sites-enabled/ \
    && rm -f /etc/nginx/sites-enabled/default

# Create startup script
COPY <<EOF /opt/moxnas/start.sh
#!/bin/bash
set -e

# Initialize database if needed
if [ ! -f /opt/moxnas/backend/db.sqlite3 ]; then
    echo "🗄️ Initializing database..."
    cd /opt/moxnas/backend
    ../venv/bin/python manage.py migrate
    ../venv/bin/python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@moxnas.local', 'moxnas123')
    print('✅ Admin user created: admin/moxnas123')
"
    cd /opt/moxnas
fi

# Start nginx
nginx

# Start MoxNAS
echo "🚀 Starting MoxNAS..."
cd /opt/moxnas/backend
exec ../venv/bin/gunicorn moxnas.wsgi:application --bind 0.0.0.0:8000 --workers 2
EOF

RUN chmod +x /opt/moxnas/start.sh

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

# Set user and start
USER moxnas
CMD ["/opt/moxnas/start.sh"]