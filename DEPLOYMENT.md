# Production Deployment Guide for Resume Matcher

This guide covers deployment to various platforms.

## 1. Linux Server with systemd

### Create systemd service file
```bash
# /etc/systemd/system/resume-matcher.service
[Unit]
Description=AI Resume Matcher Application
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/resume-matcher
ExecStart=/var/www/resume-matcher/venv/bin/gunicorn \
    --workers 4 \
    --bind 0.0.0.0:5000 \
    --timeout 120 \
    --access-logfile /var/log/resume-matcher/access.log \
    --error-logfile /var/log/resume-matcher/error.log \
    run:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Start service
```bash
sudo systemctl daemon-reload
sudo systemctl enable resume-matcher
sudo systemctl start resume-matcher
sudo systemctl status resume-matcher
```

## 2. Nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/resume-matcher
upstream resume_matcher {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    client_max_body_size 50M;

    location / {
        proxy_pass http://resume_matcher;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 120s;
    }

    location /api {
        proxy_pass http://resume_matcher;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Content-Type application/json;
        proxy_read_timeout 120s;
    }

    # SSL (after installing certificate)
    # listen 443 ssl http2;
    # ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
}
```

Enable and restart:
```bash
sudo ln -s /etc/nginx/sites-available/resume-matcher /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 3. Docker Deployment

### Build image
```bash
docker build -t resume-matcher:latest .
```

### Run container
```bash
docker run -d \
    --name resume-matcher \
    -p 5000:5000 \
    -e FLASK_ENV=production \
    -e SECRET_KEY=your-secret-key \
    -v /data/resume-matcher/logs:/app/logs \
    -v /data/resume-matcher/models:/app/models \
    -v /data/resume-matcher/uploads:/app/uploads \
    resume-matcher:latest
```

## 4. Docker Compose (Production)

```bash
docker-compose -f docker-compose.yml up -d
```

## 5. Cloud Platforms

### Heroku
```bash
# Create Procfile
web: gunicorn -w 4 -b 0.0.0.0:$PORT run:app

# Deploy
heroku create resume-matcher
git push heroku main
heroku config:set FLASK_ENV=production
```

### AWS EC2
```bash
# Install dependencies
sudo apt-get update
sudo apt-get install python3 python3-pip python3-venv nginx

# Clone and setup
git clone <repo> /var/www/resume-matcher
cd /var/www/resume-matcher
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python train_models.py

# Use systemd as described above
```

### DigitalOcean App Platform
```yaml
name: resume-matcher
services:
  - name: web
    image:
      registry: docker.io
      registry_type: DOCKER_HUB
      repository: resume-matcher
      tag: latest
    http_port: 5000
    envs:
      - key: FLASK_ENV
        value: production
```

## 6. Monitoring & Logging

### Check application status
```bash
curl http://localhost:5000/api/dashboard/health
curl http://localhost:5000/api/dashboard/stats
```

### View logs
```bash
# Using systemd
sudo journalctl -u resume-matcher -f

# Using Docker
docker logs -f resume-matcher

# Application logs
tail -f logs/app.log
```

### Log rotation (logrotate)
```bash
# /etc/logrotate.d/resume-matcher
/var/log/resume-matcher/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload resume-matcher > /dev/null 2>&1 || true
    endscript
}
```

## 7. Performance Optimization

### Enable gzip compression (nginx)
```nginx
gzip on;
gzip_min_length 1000;
gzip_types text/plain text/css application/json application/javascript;
```

### Increase worker processes
```bash
# For 4 CPU cores
gunicorn --workers 8 --worker-class gevent run:app
```

### Enable caching
```nginx
# nginx
location /static {
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

## 8. Security Hardening

### Set environment variables securely
```bash
# .env (never commit to git)
FLASK_ENV=production
SECRET_KEY=<generate-with-secrets.token_hex(32)>

# Add to .gitignore
echo ".env" >> .gitignore
```

### SSL/TLS with Let's Encrypt
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot certonly --nginx -d yourdomain.com
sudo certbot renew --dry-run  # Test auto-renewal
```

### Firewall configuration
```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## 9. Database Integration (Optional)

If adding PostgreSQL:

```bash
# Install
sudo apt-get install postgresql postgresql-contrib

# Create database
sudo -u postgres createdb resume_matcher
sudo -u postgres createuser resume_user
```

Update `app/utils/config.py`:
```python
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
SQLALCHEMY_TRACK_MODIFICATIONS = False
```

## 10. Monitoring & Alerts

### Using Prometheus & Grafana
1. Add prometheus middleware to Flask
2. Expose metrics on `/metrics`
3. Configure Prometheus scrape config
4. Create dashboards in Grafana

## Troubleshooting

### Models not loaded
```bash
python train_models.py
```

### Permission denied errors
```bash
sudo chown -R www-data:www-data /var/www/resume-matcher
sudo chmod -R 755 /var/www/resume-matcher
```

### Memory issues with large files
```bash
# Increase swap (if on small server)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

For 24/7 uptime, consider:
- Load balancing (nginx, HAproxy)
- Database backup strategy
- Automated health checks
- Alerting system
- CDN for static files
