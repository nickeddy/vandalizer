# Vandalizer Helm chart

Deploys Vandalizer onto a k3s / Kubernetes cluster. Single chart packaging app
tier (api, celery workers, celery beat, frontend) plus data tier (MongoDB,
Redis, ChromaDB).

## Per-environment values

The chart itself contains only generic defaults. Environment-specific values
(image registry, ingress host, public URLs) are supplied by a per-environment
overlay file that you maintain outside this chart — typically in an ops repo
or on the operator's workstation. Create a `values-<env>.yaml` for each
deployment target.

Every `helm install/upgrade` must pass an overlay with `-f`. Installing
without one will fail fast with a `required` error telling you what's
missing (e.g. `image.registry is required …`). Minimum keys an overlay must
set: `image.registry`, `image.pullSecrets`, `ingress.host`,
`backendEnv.FRONTEND_URL`, and `backendEnv.VANDALIZER_BASE_URL`.

## Prerequisites

- Kubernetes >= 1.24 (tested target: **single-node k3s**)
- Traefik installed and exposing your chosen Ingress host. k3s ships Traefik
  by default, so a stock k3s cluster satisfies this out of the box. The
  chart sets `ingressClassName: traefik` and applies a Traefik `Middleware`
  (buffering) to raise the request-body cap — the Traefik CRDs must be
  present (they are, with the standard k3s install). Request timeouts are
  an **entrypoint-level** Traefik setting (`respondingTimeouts`), not a
  per-Ingress annotation — if long-running API calls time out at the proxy,
  raise them on the Traefik install itself.
- A StorageClass for the shared `uploads` PVC. Default is `local-path`
  (k3s built-in). The PVC is RWO but is mounted by the api pod *and* every
  celery worker pod — this is only safe when all of those pods land on the
  **same node** (guaranteed on a single-node cluster). If you ever expand
  to multi-node, switch to a real RWX class (NFS, Longhorn-RWX, etc.) and
  flip the PVC accessMode back to `ReadWriteMany`.
- A TLS Secret for your Ingress host in the target namespace (default name:
  `vandalizer-tls`). If you use cert-manager, annotate the Ingress instead
  and set `ingress.tls.secretName` to the cert-manager target.
- An image pull Secret in the target namespace for your container registry
  (default name: `harbor-pull-secret`, overridable via
  `.Values.image.pullSecrets`).
- Pre-created backend env Secret (see below).

## Pre-created Secret

The chart expects a Secret named `vandalizer-backend-env` (override via
`.Values.secrets.backendEnvSecret`). Populate it with:

| Key                           | Required | Notes |
| ----------------------------- | -------- | ----- |
| `JWT_SECRET_KEY`              | yes      | `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `CONFIG_ENCRYPTION_KEY`       | yes      | Fernet key. `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `SMTP_USER`                   | if SMTP  | |
| `SMTP_PASSWORD`               | if SMTP  | |
| `RESEND_API_KEY`              | if Resend | |
| `GRAPH_TOKEN_KEY`             | if M365  | Fernet key for encrypting Graph OAuth tokens |
| `GRAPH_CLIENT_STATE_SECRET`   | if M365  | |
| `GRAPH_NOTIFICATION_URL`      | if M365  | |

If the cluster uses sealed-secrets or external-secrets, create the Secret via
that mechanism — this chart only references it by name.

Plain-Secret example:

```bash
kubectl -n <ns> create secret generic vandalizer-backend-env \
  --from-literal=JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(64))')" \
  --from-literal=CONFIG_ENCRYPTION_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" \
  --from-literal=SMTP_USER="" \
  --from-literal=SMTP_PASSWORD=""
```

## Install

End-to-end walkthrough for a fresh install into the `vandalizer` namespace.

```bash
# 1. Namespace
kubectl create namespace vandalizer

# 2. Backend-env Secret (plain example; adapt for sealed/external-secrets)
kubectl -n vandalizer create secret generic vandalizer-backend-env \
  --from-literal=JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(64))')" \
  --from-literal=CONFIG_ENCRYPTION_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"

# 3. Image pull Secret (skip if already present)
kubectl -n vandalizer create secret docker-registry harbor-pull-secret \
  --docker-server=<your-registry-host> \
  --docker-username=<user> \
  --docker-password=<pass>

# 4. TLS Secret for the Ingress host (or use cert-manager)
kubectl -n vandalizer create secret tls vandalizer-tls \
  --cert=<path/to/cert.pem> --key=<path/to/key.pem>

# 5. Install the chart with your environment overlay
helm upgrade --install vandalizer ./deploy/helm/vandalizer \
  -n vandalizer \
  -f <path/to/values-<env>.yaml>
```

## First-time bootstrap

The chart does *not* auto-run migrations or bootstrap jobs. Enable them
explicitly, wait for completion, then flip the flags back off and delete the
completed Jobs.

```bash
# Enable bootstrap + default-team jobs
helm upgrade vandalizer ./deploy/helm/vandalizer -n vandalizer \
  -f <path/to/values-<env>.yaml> \
  --set jobs.bootstrap.enabled=true \
  --set jobs.setupDefaultTeam.enabled=true

# Wait for them to complete
kubectl -n vandalizer wait --for=condition=complete --timeout=10m \
  job/vandalizer-bootstrap job/vandalizer-setup-default-team

# Turn the flags back off and clean up
helm upgrade vandalizer ./deploy/helm/vandalizer -n vandalizer \
  -f <path/to/values-<env>.yaml> \
  --set jobs.bootstrap.enabled=false \
  --set jobs.setupDefaultTeam.enabled=false
kubectl -n vandalizer delete job vandalizer-bootstrap vandalizer-setup-default-team
```

The same enable → wait → disable → delete pattern applies to every one-off job.

Available one-off jobs:

- `jobs.bootstrap`         → runs `python bootstrap_install.py`
- `jobs.migrate`           → runs `python migrate.py`
- `jobs.migrateFiles`      → runs `python migrate_files.py`
- `jobs.setupDefaultTeam`  → runs `python setup_default_team.py`
- `jobs.createAdmin`       → runs `python create_admin.py` (needs `jobs.createAdmin.adminEmail`, `jobs.createAdmin.adminPassword`)

## Known limitations

- **MongoDB is single-replica** — no replica set, no auth. For prod HA, migrate
  to the MongoDB Community Operator and point the chart at an external URI
  via the backend env Secret.
- **ChromaDB 0.6.3 is single-replica** — it isn't HA-capable at this version.
- **Beat singleton** — `celery.beat.replicas` must stay at `1`. Running
  multiple beats schedules every task multiple times.
- **Shared uploads volume** is a known scaling bottleneck and, as configured
  with `local-path`, constrains the whole release to a single node. A
  follow-up migration to S3/MinIO is recommended.
- **Bare `api` Service** — the frontend's `nginx.conf` hardcodes
  `proxy_pass http://api:8001`, so this chart creates a second Service named
  simply `api` in the release namespace. Only one vandalizer release per
  namespace is supported because of that name collision.
- **No init containers waiting for data services** — the api and celery pods
  will crash-loop briefly on cold cluster start until mongo/redis/chromadb
  become Ready. This is idiomatic in k8s.
