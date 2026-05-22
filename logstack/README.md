# GlitchTip — Kubernetes Deployment Guide

## Files in this package

| File | Purpose |
|------|---------|
| `values.yaml` | Main Helm chart configuration |
| `namespace-and-secrets.yaml` | Namespace + K8s Secret for sensitive values |
| `minio-init-job.yaml` | One-time Job to create the MinIO bucket |

---

## Prerequisites

```bash
# 1. Add required Helm repos
helm repo add glitchtip https://gitlab.com/api/v4/projects/16325141/packages/helm/stable
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# 2. Confirm cert-manager ClusterIssuer name
kubectl get clusterissuer
# Update cert-manager.io/cluster-issuer annotation in values.yaml to match
```

---

## Deployment steps

```bash
# Install the CloudNativePG operator
helm repo add cnpg https://cloudnative-pg.github.io/charts
helm repo update
helm install cnpg cnpg/cloudnative-pg --namespace cnpg-system --create-namespace

# Wait for it to be ready
kubectl rollout status deployment/cnpg-cloudnative-pg -n cnpg-system

# Get the Postgres URI (and add it to secrets.yaml)
kubectl get secret glitchtip-pg-app -n glitchtip -o jsonpath='{.data.uri}' | ForEach-Object { [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($_)) }

# 2. Install the chart
helm install glitchtip glitchtip/glitchtip --namespace glitchtip --create-namespace --values values.yaml --values secrets.yaml

# 3. (Optional) Run MinIO bucket init job if bucket wasn't auto-created
kubectl apply -f minio-init-job.yaml -n glitchtip

# 4. Run Django migrations (first install only)
kubectl exec -n glitchtip deploy/glitchtip-web -- python manage.py migrate

# 5. Create a superuser
kubectl exec -it -n glitchtip deploy/glitchtip-web -- python manage.py createsuperuser
```

---

## Upgrading

```bash
helm upgrade glitchtip glitchtip/glitchtip --namespace glitchtip --values values.yaml
```

---

## Checklist before go-live

- [ ] Replace ALL `<PLACEHOLDER>` values in `values.yaml` and `namespace-and-secrets.yaml`
- [ ] Pin `glitchtip.image.tag` to a specific version (not `latest`)
- [ ] Set `ENABLE_USER_REGISTRATION: "false"` unless you want open signups
- [ ] Verify your `cert-manager.io/cluster-issuer` annotation matches your ClusterIssuer
- [ ] Update `GLITCHTIP_DOMAIN` and ingress host to your real domain
- [ ] Configure `EMAIL_URL` so password resets and alerts work
- [ ] Consider replacing the raw K8s Secret with Sealed Secrets or External Secrets Operator
- [ ] Set `storageClass` on PVCs if your cluster doesn't have a default StorageClass

---

## Connecting your app (Sentry SDK)

GlitchTip is Sentry SDK-compatible. Just point your DSN at your GlitchTip instance:

```dart
// Flutter / Dart example
await SentryFlutter.init(
  (options) {
    options.dsn = 'https://<KEY>@glitchtip.yourdomain.com/<PROJECT_ID>';
    options.environment = 'production'; // or staging, dev, etc.
  },
  appRunner: () => runApp(MyApp()),
);
```

Find your DSN under **Project Settings → Client Keys** in the GlitchTip UI.

---

## Resource summary (baseline)

| Component | CPU request | Memory request | Storage |
|-----------|-------------|----------------|---------|
| Web (×2)  | 400m total  | 512Mi total    | —       |
| Worker    | 100m        | 128Mi          | —       |
| PostgreSQL| 100m        | 128Mi          | 10Gi    |
| Redis     | 50m         | 64Mi           | 2Gi     |
| MinIO     | 100m        | 128Mi          | 20Gi    |
| **Total** | **~750m**   | **~960Mi**     | **32Gi**|
