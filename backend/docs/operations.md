# Operations

Running the HRMS backend in production: probes, dependencies, logging, jobs, and
backup/recovery. Environment and dependency pinning are covered in
[`environment.md`](environment.md).

## Health probes

Three distinct questions. Conflating them is how a rolling deploy takes a service down.

| Probe | Endpoint | Checks | Meaning of failure |
|---|---|---|---|
| **Liveness** | `GET /health` | nothing | *Restart me* |
| **Readiness** | `GET /health/ready` | database, and Redis where mandatory | *Take me out of the pool* |
| **Startup** | (lifespan) | database + Redis | *Refuse to start* (production only) |

**Liveness deliberately touches no dependency.** If it probed Redis, a Redis blip would
fail the probe, the orchestrator would restart every pod, and a degraded system would
become a total outage. Liveness answers only "is this process wedged?".

**Readiness returns `503` when the database is unreachable**, so the load balancer drains
the instance while leaving it running to recover. Outside production it stays *ready* when
only Redis is down — the cache falls back to the database — but reports the degradation:

```json
{"ready": true, "checks": {
  "database": {"status": "ok", "required": true},
  "redis": {"status": "error", "required": false,
            "impact": "cache bypassed; login rate limiting disabled"}}}
```

Kubernetes:

```yaml
livenessProbe:  { httpGet: { path: /health,       port: 8000 }, periodSeconds: 10 }
readinessProbe: { httpGet: { path: /health/ready, port: 8000 }, periodSeconds: 5  }
```

## Redis is mandatory in production

Redis backs the login throttle and the account lockout. When it is unreachable those
controls **fail open** — deliberately, because a Redis blip must not lock every user out
of the product. The consequence is that brute-force protection silently disappears while
the application still looks perfectly healthy.

That is acceptable as a transient degradation and unacceptable as a steady state, so with
`ENVIRONMENT=production` and `RATE_LIMIT_ENABLED=true` the app **refuses to start** without
Redis:

```
DependencyUnavailableError: Refusing to start: redis is unreachable (...) and is
required in production because it backs login rate limiting and the account lockout.
```

Set `RATE_LIMIT_ENABLED=false` to run production without Redis — an explicit, auditable
decision rather than a silent one.

`ENVIRONMENT=production` additionally requires a real `SECRET_KEY`, `JWT_SECRET`,
`ALLOWED_ORIGINS` and `ALLOWED_HOSTS`, rejects `DEBUG=true`, and **disables `/docs`,
`/redoc` and `/openapi.json`** (they enumerate every endpoint and schema for an attacker
and are of no use to a client that already has the contract).

## Logging

Structured JSON on stdout — ship it to any aggregator; no file rotation to manage.
Every request emits:

```json
{"event": "request_completed", "method": "GET", "path": "/api/v1/employees",
 "status_code": 200, "duration_ms": 13.5, "request_id": "c89878c1...",
 "level": "info", "timestamp": "2026-07-11T06:02:10.243953Z", "client": "10.0.0.4"}
```

`request_id` is echoed in the `X-Request-ID` response header and attached to every log
line in that request, so a user-reported failure can be traced end to end from one id.

Alert on these events — each is a real condition, not noise:

| Event | Level | Meaning |
|---|---|---|
| `cache_backend_unavailable` | ERROR | Redis down; serving from the DB (degraded, not broken) |
| `rate_limit_backend_unavailable` | ERROR | **Brute-force protection is off** |
| `startup_dependency_check_failed` | ERROR | Refusing to start / degraded start |
| `integrity_error` | WARNING | A uniqueness/FK race lost at the database |
| `request_failed` | ERROR | Unhandled 5xx |

Secrets are never logged: passwords, tokens and session identifiers are absent from every
log and audit string, and rate-limit keys hash the email rather than storing it.

## Background jobs

`arq` (async-native, Redis-backed) runs the worker:

```bash
make worker                              # local
docker compose up worker                 # containerised
```

Jobs open their **own** database session — never a request-scoped one, which `get_db`
closes the instant the handler returns. Mutating jobs are idempotent because arq retries
on failure.

## Backup & recovery

```bash
./scripts/backup.sh                                    # -> var/backups/hrms-<utc>.dump
./scripts/restore.sh var/backups/hrms-<utc>.dump hrms_restored
```

Backups use `pg_dump --format=custom` (compressed, selectively restorable) and are
**verified on creation** with `pg_restore --list`. A backup you have never read is a
hypothesis, not a backup — this catches truncation the night it happens rather than
during an incident.

Nightly, keeping 14 days:

```cron
0 2 * * *  cd /srv/hrms/backend && ./scripts/backup.sh >> var/logs/backup.log 2>&1
```

`restore.sh` **refuses to restore over the live database**. Restore beside it, verify,
then repoint `DATABASE_URL` — restoring in place is how a recoverable incident becomes an
unrecoverable one.

### Verified recovery drill

Exercised end to end against real PostgreSQL (800 employees, 22,400 attendance rows):

| Step | Result |
|---|---|
| `pg_dump -Fc` | 444 KB archive |
| `pg_restore --list` integrity check | 709 objects readable |
| Simulated data loss (`TRUNCATE ... CASCADE`) | all rows gone |
| Restore into a fresh database | succeeded |
| Row counts | restored **exactly** |
| Schema | alembic head, 131 FKs, 180 indexes intact |
| Monetary values | `sum(to_pay)` = 22,400,000.00 — unchanged |

Re-run the drill after any schema change; a restore path that has not been executed since
the last migration is not a restore path.
