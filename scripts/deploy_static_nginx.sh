#!/usr/bin/env bash
#
# Production-style deploy helper for Ubuntu hosts.
#
# It keeps the backend running behind Nginx and publishes the built React SPA
# into /var/www so Nginx can serve static files directly.
#
# Usage:
#   bash scripts/deploy_static_nginx.sh deploy
#   bash scripts/deploy_static_nginx.sh start
#   bash scripts/deploy_static_nginx.sh stop
#   bash scripts/deploy_static_nginx.sh restart
#   bash scripts/deploy_static_nginx.sh build
#   bash scripts/deploy_static_nginx.sh publish
#   bash scripts/deploy_static_nginx.sh nginx
#   bash scripts/deploy_static_nginx.sh status
#
# Common overrides:
#   WEB_ROOT=/var/www/wenjia-agent BACKEND_PORT=8000 bash scripts/deploy_static_nginx.sh deploy
#   BRANCH=main bash scripts/deploy_static_nginx.sh deploy

set -Eeuo pipefail
IFS=$'\n\t'

ACTION="${1:-deploy}"
BRANCH="${BRANCH:-main}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
WEB_ROOT="${WEB_ROOT:-/var/www/wenjia-agent}"
WEB_DIST="${WEB_DIST:-${WEB_ROOT}/dist}"
WEB_OWNER="${WEB_OWNER:-www-data:www-data}"
NGINX_CONF_SOURCE="${NGINX_CONF_SOURCE:-docs/vibe_coding/wenjia-agent.jiajiahome.top.conf}"
NGINX_CONF_TARGET="${NGINX_CONF_TARGET:-/etc/nginx/conf.d/wenjia-agent.conf}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="${ROOT_DIR}/apps/web/frontend"
RUN_DIR="${RUN_DIR:-${ROOT_DIR}/.run}"
LOG_DIR="${LOG_DIR:-${ROOT_DIR}/logs}"

BACKEND_PID="${RUN_DIR}/backend.pid"
BACKEND_LOG="${LOG_DIR}/backend.log"
FRONTEND_BUILD_LOG="${LOG_DIR}/frontend-build.log"

log() {
  printf '\033[1;34m[deploy]\033[0m %s\n' "$*"
}

die() {
  printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2
  exit 1
}

sudo_cmd() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

ensure_dirs() {
  mkdir -p "${RUN_DIR}" "${LOG_DIR}"
}

ensure_web_dist_safe() {
  case "${WEB_DIST}" in
    /var/www/*) ;;
    *) die "WEB_DIST must stay under /var/www for this script. Current: ${WEB_DIST}" ;;
  esac
}

is_running() {
  local pid_file="$1"
  [[ -f "${pid_file}" ]] && kill -0 "$(cat "${pid_file}")" 2>/dev/null
}

stop_backend() {
  if ! is_running "${BACKEND_PID}"; then
    rm -f "${BACKEND_PID}"
    log "Backend is not running."
    return 0
  fi

  local pid
  pid="$(cat "${BACKEND_PID}")"
  log "Stopping backend (pid ${pid})."
  kill -- "-${pid}" 2>/dev/null || kill "${pid}" 2>/dev/null || true

  for _ in {1..30}; do
    if ! kill -0 "${pid}" 2>/dev/null; then
      rm -f "${BACKEND_PID}"
      return 0
    fi
    sleep 0.2
  done

  log "Backend did not stop gracefully; killing."
  kill -9 -- "-${pid}" 2>/dev/null || kill -9 "${pid}" 2>/dev/null || true
  rm -f "${BACKEND_PID}"
}

pull_code() {
  if [[ ! -d "${ROOT_DIR}/.git" ]]; then
    log "No git repository found at ${ROOT_DIR}; skipping pull."
    return 0
  fi

  log "Pulling latest code from origin/${BRANCH}."
  git -C "${ROOT_DIR}" fetch origin "${BRANCH}"
  git -C "${ROOT_DIR}" checkout "${BRANCH}"
  git -C "${ROOT_DIR}" pull --ff-only origin "${BRANCH}"
}

start_backend() {
  ensure_dirs
  if is_running "${BACKEND_PID}"; then
    log "Backend already running (pid $(cat "${BACKEND_PID}"))."
    return 0
  fi

  log "Starting backend on ${BACKEND_HOST}:${BACKEND_PORT}."
  cd "${ROOT_DIR}"
  nohup setsid poetry run uvicorn apps.web.backend.main:app \
    --host "${BACKEND_HOST}" \
    --port "${BACKEND_PORT}" \
    >"${BACKEND_LOG}" 2>&1 &
  echo $! >"${BACKEND_PID}"
  sleep 1
  is_running "${BACKEND_PID}" || die "Backend failed to start. See ${BACKEND_LOG}."
}

build_frontend() {
  ensure_dirs
  log "Building frontend."
  cd "${FRONTEND_DIR}"
  npm ci >>"${FRONTEND_BUILD_LOG}" 2>&1
  npm run build >>"${FRONTEND_BUILD_LOG}" 2>&1
}

publish_frontend() {
  require_cmd rsync
  ensure_web_dist_safe
  build_frontend

  log "Publishing frontend dist to ${WEB_DIST}."
  sudo_cmd mkdir -p "${WEB_DIST}"
  sudo_cmd rsync -a --delete "${FRONTEND_DIR}/dist/" "${WEB_DIST}/"
  sudo_cmd chown -R "${WEB_OWNER}" "${WEB_ROOT}"
  sudo_cmd chmod -R u=rwX,g=rX,o=rX "${WEB_ROOT}"
}

install_nginx_conf() {
  require_cmd nginx
  local source_path
  if [[ "${NGINX_CONF_SOURCE}" = /* ]]; then
    source_path="${NGINX_CONF_SOURCE}"
  else
    source_path="${ROOT_DIR}/${NGINX_CONF_SOURCE}"
  fi
  [[ -f "${source_path}" ]] || die "Nginx config source not found: ${source_path}"

  log "Installing Nginx config to ${NGINX_CONF_TARGET}."
  sudo_cmd cp "${source_path}" "${NGINX_CONF_TARGET}"
  sudo_cmd nginx -t
  sudo_cmd systemctl reload nginx
}

restart_backend() {
  stop_backend
  start_backend
}

deploy_all() {
  pull_code
  publish_frontend
  restart_backend
  status_all
}

status_all() {
  if is_running "${BACKEND_PID}"; then
    log "Backend: running (pid $(cat "${BACKEND_PID}"), log ${BACKEND_LOG})"
  else
    log "Backend: stopped (log ${BACKEND_LOG})"
  fi
  log "Backend URL: http://${BACKEND_HOST}:${BACKEND_PORT}"
  log "Frontend dist: ${WEB_DIST}"
  log "Nginx should serve ${WEB_DIST} and proxy /api + /health to backend."
}

case "${ACTION}" in
  deploy)
    deploy_all
    ;;
  start)
    start_backend
    status_all
    ;;
  stop)
    stop_backend
    ;;
  restart)
    restart_backend
    status_all
    ;;
  build)
    build_frontend
    ;;
  publish)
    publish_frontend
    ;;
  nginx)
    install_nginx_conf
    ;;
  pull)
    pull_code
    ;;
  status)
    status_all
    ;;
  *)
    die "Unknown action: ${ACTION}. Use deploy | start | stop | restart | build | publish | nginx | pull | status."
    ;;
esac
