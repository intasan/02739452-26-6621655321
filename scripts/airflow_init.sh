#!/usr/bin/env bash
set -euo pipefail
: "${AIRFLOW_ADMIN_PASSWORD:?Set AIRFLOW_ADMIN_PASSWORD in .env}"
airflow db migrate
if airflow users list --output json | python -c 'import json,sys; sys.exit(0 if any(u["username"]=="admin" for u in json.load(sys.stdin)) else 1)'; then
  echo 'Airflow admin already exists; credentials unchanged.'
else
  airflow users create --username admin --firstname Exam --lastname Admin --role Admin \
    --email admin@example.invalid --password "$AIRFLOW_ADMIN_PASSWORD"
fi
