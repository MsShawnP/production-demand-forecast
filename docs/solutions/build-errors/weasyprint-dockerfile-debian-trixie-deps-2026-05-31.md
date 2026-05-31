---
title: WeasyPrint Dockerfile dependencies for Fly.io on Debian Trixie
date: 2026-05-31
category: docs/solutions/build-errors/
module: deployment
problem_type: build_error
component: tooling
severity: high
symptoms:
  - "apt-get install fails with: E: Unable to locate package libgdk-pixbuf2.0-0"
  - WeasyPrint import fails in Fly.io container after Docker image builds successfully
  - PDF export produces blank or broken output with no explicit error
root_cause: config_error
resolution_type: environment_setup
tags:
  - weasyprint
  - dockerfile
  - fly-io
  - debian-trixie
  - pdf
  - gdk-pixbuf
  - pango
---

# WeasyPrint Dockerfile dependencies for Fly.io on Debian Trixie

## Problem

When deploying a Python app to Fly.io using `python:3.13-slim` (Debian Trixie), WeasyPrint fails
to generate PDFs due to two system library issues: the `libgdk-pixbuf2.0-0` package name no longer
exists in Trixie, and `libpangocairo-1.0-0` was absent from the initial Dockerfile even though
WeasyPrint requires it for text rendering.

## Symptoms

- `E: Unable to locate package libgdk-pixbuf2.0-0` during `apt-get install` in the Docker build
- After fixing the gdk-pixbuf name: Docker build succeeds but WeasyPrint produces blank or broken
  PDFs with no explicit Python error
- WeasyPrint works locally on an older Debian/Ubuntu but fails in the deployed container

## What Didn't Work

- Initial Dockerfile used `libgdk-pixbuf2.0-0` — the Bullseye/Buster package name copied from a
  sibling project built on an older base image. That package no longer exists in Trixie, causing
  apt to fail. (session history)
- After renaming `libgdk-pixbuf2.0-0` → `libgdk-pixbuf-xlib-2.0-0`, the image built successfully
  but PDF export still produced blank output. A second deploy was required after adding
  `libpangocairo-1.0-0` — two separate deploys to land all WeasyPrint dependencies. (session history)
- Because WeasyPrint is non-functional on Windows (requires native GTK libs), no local test of PDF
  export was possible before deployment. The Fly.io container was the first real test environment.
  (session history)

## Solution

```dockerfile
FROM python:3.13-slim

# WeasyPrint system dependencies (pango, cairo, gdk-pixbuf, cffi)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-xlib-2.0-0 \
    libffi-dev \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*
```

Complete package list for WeasyPrint on Debian Trixie: `libpango-1.0-0`, `libpangoft2-1.0-0`,
`libpangocairo-1.0-0`, `libcairo2`, `libgdk-pixbuf-xlib-2.0-0`, `libffi-dev`, `fonts-liberation`.

## Why This Works

`python:3.13-slim` runs Debian Trixie (Debian 13). Trixie split GDK-Pixbuf: the `libgdk-pixbuf2.0-0`
package from Bullseye became `libgdk-pixbuf-xlib-2.0-0` — the Xlib-linked variant that WeasyPrint
requires for its Cairo integration.

`libpangocairo-1.0-0` provides the PangoCairo backend WeasyPrint uses to lay out and render text
in the HTML-to-PDF pipeline. Without it, WeasyPrint silently produces PDFs with no text content.

`fonts-liberation` provides metrically-compatible substitutes for Times New Roman, Arial, and
Courier New. Without these, text referencing common web fonts renders at wrong metrics or not at all.

## Prevention

- When upgrading the Python base image (e.g., `python:3.12-slim` → `python:3.13-slim`), check
  whether the Debian codename changed. If it did, verify package names inside the new image:
  ```bash
  docker run --rm python:3.13-slim apt-cache search gdk-pixbuf
  ```
- Test PDF generation inside Docker before deploying:
  ```bash
  docker build -t test . && docker run --rm test python -c \
    "from weasyprint import HTML; HTML(string='<p>test</p>').write_pdf('/tmp/test.pdf'); print('ok')"
  ```
- Treat a silent blank-PDF result from WeasyPrint the same as an explicit error — it almost always
  means a missing system library, not an application bug.
- Pin `libgdk-pixbuf-xlib-2.0-0` (not `libgdk-pixbuf2.0-0`) in all Dockerfiles targeting
  Debian Trixie or later.

## Related Issues

- Fly.io deploy commits: `89350af` (libgdk-pixbuf rename), `aa16bce` (add libpangocairo)
- WeasyPrint system dependency documentation:
  https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#debian-ubuntu
