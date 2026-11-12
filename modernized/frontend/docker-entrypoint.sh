#!/bin/sh
# Inject the backend URL into config.js at container start so the frontend
# can point at the deployed backend service without a rebuild.
cat > /usr/share/nginx/html/config.js <<EOF
window.CARDDEMO_API_URL = "${BACKEND_URL}";
EOF
exec nginx -g "daemon off;"
