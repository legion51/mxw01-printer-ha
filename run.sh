#!/usr/bin/with-contenv bashio

# Read configuration
SERVER_PORT=$(bashio::config 'server_port')
ENABLE_PROXY=$(bashio::config 'enable_proxy')
CORS_ORIGIN=$(bashio::config 'cors_allow_origin')
DEBUG=$(bashio::config 'debug')
AUTO_CONNECT=$(bashio::config 'auto_connect')

# Log startup
bashio::log.info "Starting MXW01 Printer Addon..."
bashio::log.info "Server Port: ${SERVER_PORT}"
bashio::log.info "Proxy: ${ENABLE_PROXY}"
bashio::log.info "CORS Origin: ${CORS_ORIGIN}"
bashio::log.info "Debug: ${DEBUG}"
bashio::log.info "Auto Connect: ${AUTO_CONNECT}"

# Export environment variables
export SERVER_PORT="$SERVER_PORT"
export ENABLE_PROXY="$ENABLE_PROXY"
export CORS_ALLOW_ORIGIN="$CORS_ORIGIN"
export DEBUG="$DEBUG"
export NODE_ENV="production"

# Start Node.js server
cd /app
exec node server.js