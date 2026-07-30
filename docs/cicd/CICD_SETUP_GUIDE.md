# HRMS CI/CD Setup Guide — Jenkins + Docker

> **Stack**: Next.js 16 (Frontend) + FastAPI/Python 3.12 (Backend)
> **Server**: `192.168.1.60` | Jenkins: `:8090` | Frontend: `:10015` | Backend: `:10016`

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Step 1 — Server Setup](#2-step-1--server-setup)
3. [Step 2 — Jenkins Plugin Installation](#3-step-2--jenkins-plugin-installation)
4. [Step 3 — Jenkins Credentials](#4-step-3--jenkins-credentials)
5. [Step 4 — Create Pipeline Jobs](#5-step-4--create-pipeline-jobs)
6. [Step 5 — GitHub Webhook Configuration](#6-step-5--github-webhook-configuration)
7. [Step 6 — First Deployment](#7-step-6--first-deployment)
8. [Docker Reference](#8-docker-reference)
9. [Troubleshooting](#9-troubleshooting)
10. [File Reference](#10-file-reference)

---

## 1. Architecture Overview

```
GitHub (main branch)
       │
       │  push/merge
       ▼
  GitHub Webhook ──────────────────────────────────────────────┐
                                                               │
       ┌───────────────────────────────────────────────────────▼───┐
       │                   Jenkins (:8090)                         │
       │                                                           │
       │  ┌──────────────────────┐  ┌──────────────────────────┐  │
       │  │  hrms-frontend-deploy│  │  hrms-backend-deploy     │  │
       │  │  Pipeline            │  │  Pipeline                │  │
       │  └──────────┬───────────┘  └────────────┬─────────────┘  │
       └─────────────┼────────────────────────────┼───────────────-┘
                     │                            │
                     ▼                            ▼
              docker build                  docker build
              docker run                   docker run
              port 10015                   port 10016
                     │                            │
                     ▼                            ▼
           ┌─────────────────┐        ┌───────────────────┐
           │ hrms-frontend   │        │  hrms-backend     │
           │ (Next.js 16)    │        │  (FastAPI + uv)   │
           │ port: 10015     │        │  port: 10016      │
           └─────────────────┘        └───────────────────┘
```

---

## 2. Step 1 — Server Setup

### 2.1 Connect to Server

```bash
ssh itcode@192.168.1.60
# Password: Itcode@123
```

### 2.2 Run the Setup Script

The `scripts/server-setup.sh` script handles everything automatically:

```bash
# Copy the script to the server
scp scripts/server-setup.sh itcode@192.168.1.60:~/

# Connect and run it
ssh itcode@192.168.1.60
sudo bash ~/server-setup.sh
```

**The script will:**
- ✅ Verify Docker is installed and running
- ✅ Verify Jenkins is accessible on port 8090
- ✅ Add `jenkins` user to the `docker` group
- ✅ Create `/etc/hrms/` directory
- ✅ Create `/etc/hrms/backend.env` placeholder
- ✅ Open firewall ports 10015, 10016
- ✅ Create `hrms-network` Docker network

### 2.3 Edit the Backend Environment File

```bash
sudo nano /etc/hrms/backend.env
```

Update these critical values:

| Variable | Value |
|----------|-------|
| `SECRET_KEY` | Run: `openssl rand -hex 32` |
| `JWT_SECRET` | Run: `openssl rand -hex 32` |
| `DATABASE_URL` | Your PostgreSQL connection string |
| `REDIS_URL` | Your Redis connection string |
| `ALLOWED_ORIGINS` | `http://192.168.1.60:10015` |

### 2.4 Restart Jenkins

```bash
# After server-setup.sh adds jenkins to docker group, restart Jenkins
sudo systemctl restart jenkins
sleep 10
# Verify Jenkins is back up
curl -s -o /dev/null -w "Jenkins HTTP: %{http_code}\n" http://localhost:8090/
```

---

## 3. Step 2 — Jenkins Plugin Installation

### 3.1 Quick Method — Script Console

1. Open: `http://192.168.1.60:8090/`
2. Login: `itcode` / `Itcode@123`
3. Go to: **Manage Jenkins → Script Console**
4. Paste the content of `scripts/jenkins-init.groovy`
5. Click **Run**

> This installs all required plugins automatically.

### 3.2 Manual Method — Plugin Manager

Go to **Manage Jenkins → Plugins → Available plugins** and install:

| Plugin | Purpose |
|--------|---------|
| `Git Plugin` | Git SCM integration |
| `GitHub Integration Plugin` | Webhook trigger support |
| `GitHub Branch Source Plugin` | GitHub pipeline source |
| `Pipeline` (workflow-aggregator) | Declarative pipeline support |
| `Pipeline Stage View` | Visual stage display |
| `Credentials Binding Plugin` | `withCredentials{}` block support |
| `Docker Pipeline Plugin` | Docker commands in pipelines |
| `Timestamper` | Timestamps in console |
| `Workspace Cleanup Plugin` | `cleanWs()` support |
| `Blue Ocean` | Modern pipeline UI (optional) |

After installing, **restart Jenkins**.

---

## 4. Step 3 — Jenkins Credentials

Navigate to: **Manage Jenkins → Credentials → System → Global credentials → Add Credentials**

### Credential 1: GitHub Access

| Field | Value |
|-------|-------|
| Kind | Username with password |
| Username | Your GitHub username |
| Password | Your GitHub Personal Access Token (PAT) |
| ID | `github-credentials` |
| Description | GitHub Access Credentials |

> **Create a PAT**: GitHub → Settings → Developer Settings → Personal Access Tokens → Tokens (classic) → Generate new token. Required scope: `repo`

### Credential 2: Frontend API URL

| Field | Value |
|-------|-------|
| Kind | Secret text |
| Secret | `http://192.168.1.60:10016` |
| ID | `NEXT_PUBLIC_API_URL` |
| Description | Frontend API URL for Next.js build |

### Credential 3: Backend Environment File

| Field | Value |
|-------|-------|
| Kind | Secret file |
| File | Upload `/etc/hrms/backend.env` from your server |
| ID | `hrms-backend-env` |
| Description | Backend production environment variables |

> **How to get the file**: `scp itcode@192.168.1.60:/etc/hrms/backend.env ~/backend.env` then upload it here.

---

## 5. Step 4 — Create Pipeline Jobs

### 5.1 Frontend Pipeline Job

1. Jenkins Dashboard → **New Item**
2. Name: `hrms-frontend-deploy`
3. Type: **Pipeline** → OK
4. Configure:

**General:**
- ✅ Check "GitHub project"
- Project URL: `https://github.com/ITCODEHELP/Human-Resource-Management-System---Frontend-/`
- ✅ Check "Discard old builds" → Max: `10`

**Build Triggers:**
- ✅ Check "GitHub hook trigger for GITScm polling"
- ✅ Check "Poll SCM" → Schedule: `H/5 * * * *` (fallback)

**Pipeline:**
- Definition: **Pipeline script from SCM**
- SCM: **Git**
- Repository URL: `https://github.com/ITCODEHELP/Human-Resource-Management-System---Frontend-.git`
- Credentials: `github-credentials`
- Branch: `*/main`
- Script Path: `Jenkinsfile`

5. Click **Save**

### 5.2 Backend Pipeline Job

1. Jenkins Dashboard → **New Item**
2. Name: `hrms-backend-deploy`
3. Type: **Pipeline** → OK
4. Configure:

**General:**
- ✅ Check "GitHub project"
- Project URL: `https://github.com/ITCODEHELP/Human-Resource-Management-System--Backend-/`
- ✅ Check "Discard old builds" → Max: `10`

**Build Triggers:**
- ✅ Check "GitHub hook trigger for GITScm polling"
- ✅ Check "Poll SCM" → Schedule: `H/5 * * * *` (fallback)

**Pipeline:**
- Definition: **Pipeline script from SCM**
- SCM: **Git**
- Repository URL: `https://github.com/ITCODEHELP/Human-Resource-Management-System--Backend-.git`
- Credentials: `github-credentials`
- Branch: `*/main`
- Script Path: `Jenkinsfile`

5. Click **Save**

---

## 6. Step 5 — GitHub Webhook Configuration

> [!WARNING]
> GitHub webhooks require your Jenkins server to be **publicly accessible from the internet**.
> If `192.168.1.60` is a private LAN IP, webhooks **will NOT work** — use Poll SCM fallback instead.
> To expose Jenkins publicly: use ngrok, Cloudflare Tunnel, or a public reverse proxy.

### 6.1 Frontend Repository Webhook

1. Open: `https://github.com/ITCODEHELP/Human-Resource-Management-System---Frontend-/settings/hooks`
2. Click **Add webhook**
3. Configure:

| Field | Value |
|-------|-------|
| Payload URL | `http://192.168.1.60:8090/github-webhook/` |
| Content type | `application/json` |
| Secret | *(leave blank or set a shared secret)* |
| Events | ✅ Just the push event |
| Active | ✅ |

4. Click **Add webhook**
5. Verify: green checkmark appears after GitHub pings the URL

### 6.2 Backend Repository Webhook

Repeat the above for:
- `https://github.com/ITCODEHELP/Human-Resource-Management-System--Backend-/settings/hooks`
- Same Payload URL: `http://192.168.1.60:8090/github-webhook/`

---

## 7. Step 6 — First Deployment

### 7.1 Trigger Manually (First Time)

1. Open Jenkins: `http://192.168.1.60:8090/`
2. Click `hrms-frontend-deploy` → **Build Now**
3. Watch Console Output
4. Once successful, open: `http://192.168.1.60:10015`

Repeat for `hrms-backend-deploy` → verify: `http://192.168.1.60:10016/health`

### 7.2 Test Automatic Trigger

Push a small change to the `main` branch of either repo:

```bash
# Example: push a trivial change to trigger CI
git commit --allow-empty -m "chore: trigger CI pipeline"
git push origin main
```

Jenkins should automatically start the build within seconds (webhook) or 5 minutes (Poll SCM).

---

## 8. Docker Reference

### Useful Docker Commands (on server 192.168.1.60)

```bash
# ─── View running containers ──────────────────────────────────────────────────
docker ps

# ─── View container logs ─────────────────────────────────────────────────────
docker logs hrms-frontend --tail 100 -f
docker logs hrms-backend  --tail 100 -f

# ─── Container shell access ───────────────────────────────────────────────────
docker exec -it hrms-frontend sh
docker exec -it hrms-backend  bash

# ─── Manually stop/start ─────────────────────────────────────────────────────
docker stop hrms-frontend && docker start hrms-frontend
docker stop hrms-backend  && docker start hrms-backend

# ─── Inspect container ───────────────────────────────────────────────────────
docker inspect hrms-frontend
docker inspect hrms-backend

# ─── Manual build & run (frontend) ───────────────────────────────────────────
cd /path/to/frontend
docker build \
    --build-arg NEXT_PUBLIC_API_URL=http://192.168.1.60:10016 \
    -t hrms-frontend:latest .
docker run -d --name hrms-frontend --restart unless-stopped \
    -p 10015:3000 hrms-frontend:latest

# ─── Manual build & run (backend) ────────────────────────────────────────────
cd /path/to/backend
docker build --target runtime -t hrms-backend:latest .
docker run -d --name hrms-backend --restart unless-stopped \
    -p 10016:8000 --env-file /etc/hrms/backend.env hrms-backend:latest

# ─── Run DB migrations manually ───────────────────────────────────────────────
docker exec hrms-backend alembic upgrade head

# ─── Remove all dangling images ──────────────────────────────────────────────
docker image prune -f

# ─── Full cleanup (CAUTION: removes all stopped containers & unused images) ──
docker system prune -f
```

### Container Summary

| Container | Image | Host Port | Container Port | Restart Policy |
|-----------|-------|-----------|----------------|----------------|
| `hrms-frontend` | `hrms-frontend:latest` | 10015 | 3000 | `unless-stopped` |
| `hrms-backend` | `hrms-backend:latest` | 10016 | 8000 | `unless-stopped` |

---

## 9. Troubleshooting

### ❌ Jenkins cannot run `docker` commands

**Symptom**: `Permission denied while trying to connect to the Docker daemon socket`

**Fix**:
```bash
# Add jenkins to docker group
sudo usermod -aG docker jenkins
# Restart Jenkins
sudo systemctl restart jenkins
```

### ❌ Frontend health check fails

**Symptom**: `curl: (7) Failed to connect to localhost port 10015`

**Checks**:
```bash
# Is the container running?
docker ps --filter name=hrms-frontend

# Check container logs
docker logs hrms-frontend --tail 50

# Is the port bound?
ss -tlnp | grep 10015
```

**Common causes**:
- `next.config.ts` is missing `output: "standalone"` — build won't produce `server.js`
- `NEXT_PUBLIC_API_URL` build arg not passed → app can't reach backend → renders error page

### ❌ Backend health check fails

**Symptom**: `/health` returns 500 or connection refused

**Checks**:
```bash
docker logs hrms-backend --tail 100
```

**Common causes**:
- `DATABASE_URL` in `/etc/hrms/backend.env` points to unreachable host
- PostgreSQL not running — `pg_isready -h <host>`
- Missing env variables — verify file was uploaded to Jenkins credentials

### ❌ Alembic migration fails

**Symptom**: `alembic upgrade head` fails with `connection refused`

**Fix**: Ensure PostgreSQL is running and `DATABASE_URL` is correct in `/etc/hrms/backend.env`

### ❌ GitHub webhook not triggering Jenkins

**Symptom**: Pushes to GitHub don't trigger Jenkins builds

**Checks**:
1. GitHub → repo settings → Webhooks → check delivery status (green = success, red = failed)
2. If red: Jenkins URL `192.168.1.60` is likely not publicly accessible
3. **Solution**: Use Poll SCM (`H/5 * * * *`) — Jenkins will check GitHub every 5 minutes

### ❌ Docker build fails with dependency errors

**Symptom**: `pip install --require-hashes` fails (backend)

**Fix**: Regenerate `requirements.txt` from the lockfile:
```bash
# In the backend directory
uv export --no-dev --format requirements-txt > requirements.txt
git add requirements.txt && git commit -m "chore: update requirements.txt"
```

---

## 10. File Reference

```
PAYROLL/
├── frontend/
│   ├── Dockerfile          ← Multi-stage Next.js production build
│   ├── .dockerignore       ← Excludes dev files from build context
│   ├── next.config.ts      ← Modified: added output: 'standalone'
│   └── Jenkinsfile         ← Frontend CI/CD pipeline
│
├── backend/
│   ├── Dockerfile          ← Existing multi-stage Python build (unchanged)
│   ├── .dockerignore       ← Existing (unchanged)
│   └── Jenkinsfile         ← Backend CI/CD pipeline (NEW)
│
└── scripts/
    ├── server-setup.sh     ← Server verification & setup (run on 192.168.1.60)
    └── jenkins-init.groovy ← Jenkins plugin install & credential creation
```

### Endpoint Summary

| Endpoint | URL |
|----------|-----|
| Jenkins | `http://192.168.1.60:8090/` |
| Frontend | `http://192.168.1.60:10015/` |
| Backend API | `http://192.168.1.60:10016/` |
| Backend Health | `http://192.168.1.60:10016/health` |
| Backend Docs | `http://192.168.1.60:10016/docs` |
| Backend ReDoc | `http://192.168.1.60:10016/redoc` |
