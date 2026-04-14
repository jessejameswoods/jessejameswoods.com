#!/usr/bin/env bash
# Wrapper: cd into repo, source env, run main.py, ping healthchecks.io on start/success/fail.
set -u
APP_DIR=/opt/travel-seo-pulse
LOG_DIR=/var/log/travel-seo-pulse
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
LOG_FILE=${LOG_DIR}/run-${STAMP}.log

set -a
source /etc/travel-seo-pulse.env
set +a

if [ -n "${HEALTHCHECK_URL:-}" ]; then
  curl -fsS -m 10 "${HEALTHCHECK_URL}/start" >/dev/null 2>&1 || true
fi

set -o pipefail
(
  set -e
  cd ${APP_DIR}/travel-seo-pulse
  source ${APP_DIR}/.venv/bin/activate
  git -C ${APP_DIR} fetch --depth 1 origin main >/dev/null 2>&1 || true
  git -C ${APP_DIR} reset --hard origin/main >/dev/null 2>&1 || true
  ${APP_DIR}/.venv/bin/python main.py
) 2>&1 | tee "${LOG_FILE}"
RC=${PIPESTATUS[0]}

if [ ${RC} -ne 0 ]; then
  if [ -n "${HEALTHCHECK_URL:-}" ]; then
    tail -n 40 "${LOG_FILE}" | curl -fsS -m 10 --data-binary @- "${HEALTHCHECK_URL}/fail" >/dev/null 2>&1 || true
  fi
  exit ${RC}
fi

if [ -n "${HEALTHCHECK_URL:-}" ]; then
  curl -fsS -m 10 --retry 3 "${HEALTHCHECK_URL}" >/dev/null 2>&1 || true
fi
