# Docker runtime verification

**Assessment date:** 2026-11-03  
**Repository commit:** `bbfa15936ecf3b092cf0ef2f99a33ad6c0ecc270`

## Result

Docker runtime verification is **pending**. The assessment environment does
not contain Docker:

```text
docker: command not found
```

No claim is made for Docker Compose startup, health checks, manuscript upload,
document analysis, loopback binding, temporary-file cleanup, or graceful
shutdown.

## Available evidence

Main CI run
[41572673696](https://github.com/ShyamSathish005/ATEval/actions/runs/41572673696)
passed the hosted `docker` image-build job. An image build does not exercise
the Compose lifecycle or application behavior.

## Required verification procedure

On a host with Docker Engine/Desktop and Compose, run from the repository root:

```sh
docker compose -f compose.yaml up --build -d
docker compose -f compose.yaml ps
curl -fsS http://127.0.0.1:8000/api/v1/health
curl -fsS -F 'file=@sample.txt' \
  http://127.0.0.1:8000/api/v1/manuscripts/analyze
docker compose -f compose.yaml down
```

Record the health response, upload/analysis response, bound address, container
exit status, and whether temporary files are removed. Do not mark the release
checklist item complete from the image-build result alone.
