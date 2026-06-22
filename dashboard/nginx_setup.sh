#!/bin/bash
# Eenmalige setup: voeg /dashboard/ toe aan nginx config
# Draai dit één keer op de VM: bash dashboard/nginx_setup.sh

NGINX_CONF="/etc/nginx/sites-available/ainstein"

# Controleer of het al is toegevoegd
if grep -q "location /dashboard/" "$NGINX_CONF" 2>/dev/null; then
    echo "✅ /dashboard/ locatie al aanwezig in nginx config."
    exit 0
fi

# Voeg de locatie toe vóór de laatste sluitende }
if [ ! -f "$NGINX_CONF" ]; then
    echo "❌ Nginx config niet gevonden op $NGINX_CONF"
    echo "   Pas het pad aan naar de juiste nginx config."
    exit 1
fi

# Backup
sudo cp "$NGINX_CONF" "${NGINX_CONF}.backup.$(date +%Y%m%d)"

# Voeg toe vóór laatste }
sudo sed -i 's|^}$|    location /dashboard/ {\n        alias /home/thomas/Ainstein/dashboard/;\n        index index.html;\n        add_header Cache-Control "no-cache";\n    }\n}|' "$NGINX_CONF"

sudo nginx -t && sudo systemctl reload nginx && echo "✅ nginx herladen — dashboard bereikbaar op /dashboard/"
