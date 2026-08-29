#!/usr/bin/env bashio
set -e

bashio::log.info "Starting MXW01 Printer Addon..."

SERVER_PORT=$(bashio::config 'server_port')
ENABLE_PROXY=$(bashio::config 'enable_proxy')
CORS_ORIGIN=$(bashio::config 'cors_allow_origin')
DEBUG=$(bashio::config 'debug')

bashio::log.info "Configuration:"
bashio::log.info "  Port: $SERVER_PORT"
bashio::log.info "  Proxy: $ENABLE_PROXY"
bashio::log.info "  CORS Origin: $CORS_ORIGIN"
bashio::log.info "  Debug: $DEBUG"

export SERVER_PORT="$SERVER_PORT"
export ENABLE_PROXY="$ENABLE_PROXY"
export CORS_ALLOW_ORIGIN="$CORS_ORIGIN"
export DEBUG="$DEBUG"
export NODE_ENV="production"

cd /app
exec node server.js
