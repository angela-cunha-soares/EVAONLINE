#!/bin/bash
# Copia certificados renovados para o Nginx do EVAonline e reinicia
set -e
DOMAIN="evaonline.app.br"
APP_DIR="/root/EVAONLINE"
cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem $APP_DIR/docker/nginx/ssl/fullchain.pem
cp /etc/letsencrypt/live/$DOMAIN/privkey.pem $APP_DIR/docker/nginx/ssl/privkey.pem
chmod 644 $APP_DIR/docker/nginx/ssl/fullchain.pem
chmod 600 $APP_DIR/docker/nginx/ssl/privkey.pem
cd $APP_DIR && docker compose restart nginx
