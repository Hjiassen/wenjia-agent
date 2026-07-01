#!/usr/bin/env bash
#
# Lightweight dev-server runner for an Ubuntu host that already has the
# environment installed. It pulls code and starts/restarts the backend + Vite
# frontend with pid files and logs.
#
# Usage:
#   bash scripts/deploy_ubuntu.sh restart
#   bash scripts/deploy_ubuntu.sh start
#   bash scripts/deploy_ubuntu.sh stop
#   bash scripts/deploy_ubuntu.sh status
#
# Common overrides:
#   BRANCH=main BACKEND_PORT=8000 FRONTEND_PORT=5173 bash scripts/deploy_ubuntu.sh restart

set -Eeuo pipefail
IFS=$'\n\t'

ACTION="${1:-restart}"
BRANCH="${BRANCH:-main}"
BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-0.0.0.0}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="${ROOT_DIR}/apps/web/frontend"
RUN_DIR="${RUN_DIR:-${ROOT_DIR}/.run}"
LOG_DIR="${LOG_DIR:-${ROOT_DIR}/logs}"

BACKEND_PID="${RUN_DIR}/backend.pid"
FRONTEND_PID="${RUN_DIR}/frontend.pid"
BACKEND_LOG="${LOG_DIR}/backend.log"
FRONTEND_LOG="${LOG_DIR}/frontend.log"

log() {
  printf '\033[1;34m[dev-server]\033[0m %s\n' "$*"
}

die() {
  printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2
  exit 1
}

ensure_dirs() {
  mkdir -p "${RUN_DIR}" "${LOG_DIR}"
}

is_running() {
  local pid_file="$1"
  [[ -f "${pid_file}" ]] && kill -0 "$(cat "${pid_file}")" 2>/dev/null
}

stop_one() {
  local name="$1"
  local pid_file="$2"

  if ! is_running "${pid_file}"; then
    rm -f "${pid_file}"
    log "${name} is not running."
    return 0
  fi

  local pid
  pid="$(cat "${pid_file}")"
  log "Stopping ${name} (pid ${pid})."
  kill -- "-${pid}" 2>/dev/null || kill "${pid}" 2>/dev/null || true

  for _ in {1..20}; do
    if ! kill -0 "${pid}" 2>/dev/null; then
      rm -f "${pid_file}"
      return 0
    fi
    sleep 0.2
  done

  log "${name} did not stop gracefully; killing."
  kill -9 -- "-${pid}" 2>/dev/null || kill -9 "${pid}" 2>/dev/null || true
  rm -f "${pid_file}"
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

start_frontend() {
  if is_running "${FRONTEND_PID}"; then
    log "Frontend already running (pid $(cat "${FRONTEND_PID}"))."
    return 0
  fi

  log "Starting frontend on ${FRONTEND_HOST}:${FRONTEND_PORT}."
  cd "${FRONTEND_DIR}"
  nohup setsid npm run dev -- \
    --host "${FRONTEND_HOST}" \
    --port "${FRONTEND_PORT}" \
    >"${FRONTEND_LOG}" 2>&1 &
  echo $! >"${FRONTEND_PID}"
  sleep 1
  is_running "${FRONTEND_PID}" || die "Frontend failed to start. See ${FRONTEND_LOG}."
}

start_all() {
  ensure_dirs
  start_backend
  start_frontend
  status_all
}

stop_all() {
  stop_one "frontend" "${FRONTEND_PID}"
  stop_one "backend" "${BACKEND_PID}"
}

restart_all() {
  pull_code
  stop_all
  start_all
}

status_one() {
  local name="$1"
  local pid_file="$2"
  local log_file="$3"

  if is_running "${pid_file}"; then
    log "${name}: running (pid $(cat "${pid_file}"), log ${log_file})"
  else
    log "${name}: stopped (log ${log_file})"
  fi
}

status_all() {
  status_one "backend" "${BACKEND_PID}" "${BACKEND_LOG}"
  status_one "frontend" "${FRONTEND_PID}" "${FRONTEND_LOG}"
  log "Backend URL:  http://${BACKEND_HOST}:${BACKEND_PORT}"
  log "Frontend URL: http://${FRONTEND_HOST}:${FRONTEND_PORT}"
}

case "${ACTION}" in
  start)
    start_all
    ;;
  stop)
    stop_all
    ;;
  restart)
    restart_all
    ;;
  status)
    status_all
    ;;
  pull)
    pull_code
    ;;
  *)
    die "Unknown action: ${ACTION}. Use start | stop | restart | status | pull."
    ;;
esac
