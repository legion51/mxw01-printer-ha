#!/usr/bin/with-contenv bashio
set -e

export MXW01_DEVICE_ADDRESS="$(bashio::config 'device_address')"
export MXW01_DEVICE_NAME="$(bashio::config 'device_name')"
export MXW01_AUTO_CONNECT="$(bashio::config 'auto_connect')"
export MXW01_LOG_LEVEL="$(bashio::config 'log_level')"
export MXW01_KEEP_ALIVE="$(bashio::config 'keep_alive')"
export MXW01_KEEP_ALIVE_INTERVAL="$(bashio::config 'keep_alive_interval')"

bashio::log.info "Starting MXW01 printer bridge"
bashio::log.info "Integration URL for a local repository: http://local-mxw01-printer:8099"
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8099 --log-level "${MXW01_LOG_LEVEL}"
