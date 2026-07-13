# Deploying to Google Cloud Run

This document is an operations note, not a claim that the current MVP has been deployed. It assumes separate backend and frontend container images and a Google Cloud project with billing, Artifact Registry, Cloud Build, and Cloud Run enabled.

## Important limitations

- Cloud Run's writable filesystem is **ephemeral**. The local artifact directory is suitable for demos, not durable production storage.
- Multi-instance deployments cannot share a local artifact directory. Add a Cloud Storage-backed artifact adapter before relying on generated files across requests or revisions.
- `NVIDIA_API_KEY` is optional and server-only. Use Secret Manager; never put it in the frontend image or a `NEXT_PUBLIC_*` variable.
- NeMo execution requires the compatible `data-designer` package in the backend image and outbound network access.
- Native rendering requires its runtime/system packages in the backend image. Validate the renderer on the same Linux image used in Cloud Run.
- `NEXT_PUBLIC_API_URL` is normally embedded during `next build`. Build the frontend with the final backend URL unless the frontend implements an explicit runtime-config mechanism.

## Prerequisites

```bash
gcloud auth login
gcloud config set project PROJECT_ID
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com
```

Create a Docker repository once:

```bash
gcloud artifacts repositories create nv-synthforge \
  --repository-format=docker \
  --location=REGION \
  --description="NV-SynthForge container images"
```

Use a region supported by all required services. Replace `PROJECT_ID`, `REGION`, and URLs in every example.

## Build and deploy the backend

```bash
gcloud builds submit backend \
  --tag REGION-docker.pkg.dev/PROJECT_ID/nv-synthforge/backend:COMMIT_SHA

gcloud run deploy nv-synthforge-api \
  --image REGION-docker.pkg.dev/PROJECT_ID/nv-synthforge/backend:COMMIT_SHA \
  --region REGION \
  --port 8000 \
  --allow-unauthenticated
```

After deployment, capture the verified service URL:

```bash
BACKEND_URL="$(gcloud run services describe nv-synthforge-api --region REGION --format='value(status.url)')"
printf '%s\n' "$BACKEND_URL"
```

`--allow-unauthenticated` is convenient for a public hackathon demo but is not an authorization design. Remove it or place an authenticated gateway in front of the API for controlled environments.

### Optional NVIDIA secret

Create a secret without placing the value in shell history where possible:

```bash
gcloud secrets create nvidia-api-key --replication-policy=automatic
printf '%s' "$NVIDIA_API_KEY" | gcloud secrets versions add nvidia-api-key --data-file=-
```

Grant the Cloud Run service account secret access, then deploy a revision with:

```bash
gcloud run services update nv-synthforge-api \
  --region REGION \
  --set-secrets NVIDIA_API_KEY=nvidia-api-key:latest
```

For repeatable production releases, pin a secret version rather than `latest` and use a dedicated least-privilege service account.

## Build and deploy the frontend

Because `NEXT_PUBLIC_API_URL` is generally a build-time value, the frontend Dockerfile must explicitly accept and forward it to `next build` (commonly with `ARG` and `ENV`). Verify that support before using this command:

```bash
gcloud builds submit frontend \
  --config frontend/cloudbuild.yaml \
  --substitutions _IMAGE=REGION-docker.pkg.dev/PROJECT_ID/nv-synthforge/frontend:COMMIT_SHA,_NEXT_PUBLIC_API_URL="$BACKEND_URL"
```

The repository may not include that optional `frontend/cloudbuild.yaml`. If it does not, build the image using the frontend Dockerfile's documented build-argument syntax, for example:

```bash
docker build frontend \
  --build-arg NEXT_PUBLIC_API_URL="$BACKEND_URL" \
  -t REGION-docker.pkg.dev/PROJECT_ID/nv-synthforge/frontend:COMMIT_SHA
docker push REGION-docker.pkg.dev/PROJECT_ID/nv-synthforge/frontend:COMMIT_SHA
```

Then deploy:

```bash
gcloud run deploy nv-synthforge-web \
  --image REGION-docker.pkg.dev/PROJECT_ID/nv-synthforge/frontend:COMMIT_SHA \
  --region REGION \
  --port 3000 \
  --allow-unauthenticated
```

If the Dockerfile does not support `NEXT_PUBLIC_API_URL` as a build argument, add and verify that support before deployment; setting it only on `gcloud run deploy` may be too late for browser code.

## CORS and service configuration

Once the frontend URL is known, configure the backend's supported CORS setting to that exact origin. Consult the backend configuration and OpenAPI behavior rather than inventing an environment-variable name. Do not use wildcard origins with credentials.

Recommended Cloud Run settings to evaluate after load testing:

- bounded request timeout appropriate to the largest supported generation job;
- concurrency based on CPU/memory measurements, not a guessed default;
- minimum instances only if cold-start latency justifies the cost;
- maximum instances to bound spend and downstream API pressure;
- CPU and memory sized for generation and any native renderer;
- structured logging without input records, secrets, or generated sensitive-looking content.

## Verification and rollback

1. Request the backend health/root endpoint that exists in the current build and open `/docs`.
2. Load the frontend and confirm browser requests target the Cloud Run backend URL, not `localhost`.
3. Run one small offline invoice generation request.
4. If configured, run a separate small NeMo smoke test and label its provider explicitly.
5. Verify behavior after a new instance starts; do not treat local files as durable.
6. Inspect Cloud Run logs for errors and accidental secret/data exposure.

List revisions and move traffic back if needed:

```bash
gcloud run revisions list --service nv-synthforge-api --region REGION
gcloud run services update-traffic nv-synthforge-api \
  --region REGION \
  --to-revisions PREVIOUS_REVISION=100
```

Repeat the traffic operation for the frontend service when rolling it back.
