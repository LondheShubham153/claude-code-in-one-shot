#!/usr/bin/env sh
set -e

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  echo "[entrypoint] running alembic upgrade head"
  alembic upgrade head
fi

exec "$@"
