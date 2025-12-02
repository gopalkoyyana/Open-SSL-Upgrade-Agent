# OpenSSL Upgrade Report
Run ID: 20251127T163938Z
Timestamp (UTC): 2025-11-27T16:39:41.169268Z

## Summary
- Target version: 3.0.8
- Platform: windows
- Strategy: side-install — no known package manager that provides target version; using side-install

## Artifacts
- backups\20251127T163938Z.tar.gz

## Pre-upgrade snapshots

## Post-upgrade snapshots

## Commands log
See commands log: logs\20251127T163938Z\commands.log

## Verification
- Smoke tests success: None

## Rollback instructions (generic)
1. Stop dependent services (systemctl stop <service> or appropriate command).
2. Restore backup tarball from backup directory into / (or original locations).
3. Run ldconfig if available: `sudo ldconfig`.
4. Start services and run verification.