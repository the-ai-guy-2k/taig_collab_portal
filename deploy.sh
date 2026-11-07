#!/usr/bin/env bash
# Collab Portal — Droplet deploy. GitHub-first: this script lives in the repo,
# the Droplet pulls the repo and runs it. Plain `docker run` (no compose
# plugin on the Droplet). Idempotent: re-runs keep the Postgres data volume.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  echo "ERROR: .env missing. Copy .env.example to .env and fill in real secrets first." >&2
  exit 1
fi
set -a; . ./.env; set +a

: "${SECRET_KEY:?SECRET_KEY must be set in .env}"
: "${DEFAULT_ADMIN_PASSWORD:?DEFAULT_ADMIN_PASSWORD must be set in .env}"
BASE_URL="${BASE_URL:-https://taigtsp.duckdns.org/collab-portal}"

docker network create collab-portal-net >/dev/null 2>&1 || true
docker volume create collab-portal-data >/dev/null
docker volume create collab-portal-db-data >/dev/null

if ! docker ps --format '{{.Names}}' | grep -qx collab-postgres; then
  docker rm -f collab-postgres >/dev/null 2>&1 || true
  docker run -d --name collab-postgres \
    --network collab-portal-net --restart unless-stopped \
    -v collab-portal-db-data:/var/lib/postgresql/data \
    -e POSTGRES_DB=planka -e POSTGRES_HOST_AUTH_METHOD=trust \
    postgres:16-alpine
  echo "Waiting for Postgres..."
  for _ in $(seq 1 30); do
    docker exec collab-postgres pg_isready -U postgres -d planka >/dev/null 2>&1 && break
    sleep 2
  done
  docker exec collab-postgres pg_isready -U postgres -d planka
fi

docker rm -f collab-portal >/dev/null 2>&1 || true
docker run -d --name collab-portal \
  --network collab-portal-net --restart unless-stopped \
  -p 127.0.0.1:3003:1337 \
  -v collab-portal-data:/app/data \
  -e "BASE_URL=$BASE_URL" \
  -e DATABASE_URL=postgresql://postgres@collab-postgres/planka \
  -e "SECRET_KEY=$SECRET_KEY" \
  -e TRUST_PROXY=true \
  -e "DEFAULT_ADMIN_EMAIL=${DEFAULT_ADMIN_EMAIL:-tee@collab-portal.local}" \
  -e "DEFAULT_ADMIN_PASSWORD=$DEFAULT_ADMIN_PASSWORD" \
  -e "DEFAULT_ADMIN_NAME=${DEFAULT_ADMIN_NAME:-Sanil Tison}" \
  -e "DEFAULT_ADMIN_USERNAME=${DEFAULT_ADMIN_USERNAME:-tee}" \
  ghcr.io/plankanban/planka:2.3.1

echo "Waiting for Planka on http://127.0.0.1:3003/ ..."
for _ in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3003/ || true)
  [ "$code" = "200" ] && break
  sleep 2
done
curl -s -o /dev/null -w 'Planka loopback HTTP %{http_code}\n' http://127.0.0.1:3003/
docker ps --format '{{.Names}} {{.Status}}' | grep -E 'collab-(portal|postgres)' || true
echo "Done. Public URL: $BASE_URL"
