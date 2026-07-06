# Tailored Resume Generator — Docker image
#
# Bundles Python 3.12 + a pinned Tectonic static binary so `resume-gen` needs
# no local TeX/Python install (PRD.md §10, TECH_SPEC.md §7).

FROM python:3.12-slim

ARG TECTONIC_VERSION=0.16.9
ARG TECTONIC_SHA256=60b13a0826ae7ad9ce34b4a2df06bff2cfcfa6dda8a915477c0cbb84e1a4a902

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL -o /tmp/tectonic.tar.gz \
      "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%40${TECTONIC_VERSION}/tectonic-${TECTONIC_VERSION}-x86_64-unknown-linux-musl.tar.gz" \
    && echo "${TECTONIC_SHA256}  /tmp/tectonic.tar.gz" | sha256sum -c - \
    && tar -xzf /tmp/tectonic.tar.gz -C /usr/local/bin \
    && chmod +x /usr/local/bin/tectonic \
    && rm /tmp/tectonic.tar.gz

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/ ./scripts/
COPY templates/ ./templates/
COPY schema/ ./schema/

RUN useradd -m appuser
USER appuser

# Warm Tectonic's bundle cache into the image. Without this, `docker run --rm`
# starts every render with an empty ~/.cache/Tectonic and re-downloads the whole
# LaTeX support bundle (LM fonts, class, hyperref, lastpage, …) over the network
# — ~100s per render, paid again on each overflow-loop retry. Compiling a
# throwaway doc that pulls the same packages resume.tex.j2 uses bakes that cache
# (~40MB) into the image, so runtime compiles are ~2s. Run as appuser so the
# cache lands in the same HOME the entrypoint uses.
RUN printf '%s\n' \
      '\documentclass[10pt,letterpaper]{article}' \
      '\usepackage[margin=0.4in]{geometry}' \
      '\usepackage[T1]{fontenc}' \
      '\usepackage{lmodern}\usepackage{titlesec}\usepackage{enumitem}' \
      '\usepackage{xcolor}\usepackage{hyperref}\usepackage{lastpage}' \
      '\begin{document}warm\end{document}' > /tmp/warm.tex \
    && tectonic --outdir /tmp /tmp/warm.tex \
    && rm -f /tmp/warm.*

WORKDIR /work

ENTRYPOINT ["python3", "/app/scripts/generate_resume.py"]
