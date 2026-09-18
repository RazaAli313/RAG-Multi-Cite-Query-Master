#!/bin/sh
set -e

SECRETS_FILE="/secrets/app.env"

printf 'Waiting for Infisical agent to write secrets...\n'
until [ -f "$SECRETS_FILE" ]; do
  sleep 2
done

printf 'Secrets ready. Starting application...\n'

set -a
. "$SECRETS_FILE"
set +a

exec "$@"
