#!/usr/bin/env bash
# Sauvegarde PostgreSQL (dump compressé + rétention). À planifier via cron/systemd.
#
# Usage :
#   DATABASE_URL=postgresql://user:pass@host:5432/db BACKUP_DIR=/var/backups/myhanout \
#     RETENTION_DAYS=14 ./scripts/backup_pg.sh
#
# Restauration :
#   gunzip -c <fichier>.sql.gz | psql "$DATABASE_URL"
#
# Test de restore recommandé (mensuel) : restaurer le dernier dump sur une base jetable
# et lancer `alembic upgrade head` + un SELECT de contrôle (cf. docs/DEPLOY.md).
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL requis (postgresql://...)}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/myhanout}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

mkdir -p "$BACKUP_DIR"
stamp="$(date +%Y%m%d-%H%M%S)"
out="$BACKUP_DIR/myhanout-$stamp.sql.gz"

echo "→ Dump vers $out"
# --no-owner/--no-privileges : restaurable sur une autre instance sans rejouer les rôles.
pg_dump --no-owner --no-privileges "$DATABASE_URL" | gzip -9 > "$out"

echo "→ Rétention : suppression des dumps de plus de ${RETENTION_DAYS} jours"
find "$BACKUP_DIR" -name 'myhanout-*.sql.gz' -mtime "+${RETENTION_DAYS}" -delete

echo "✓ Sauvegarde terminée : $out"
