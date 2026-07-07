# web/Dockerfile — containerizes the local resume web app ("local container now").
#
# Nothing personal is baked in: the app code AND master.yaml are bind-mounted at
# run time (see web/docker-compose.yml), so this image stays generic and your
# data never enters it. Deleting web/ reverts everything.
FROM python:3.12-slim

# The web server itself is pure-stdlib Python, but at run time it shells out to:
#   • the `docker` CLI — to run the existing PDF renderer against the HOST daemon
#     (via a mounted socket), instead of Docker-in-Docker;
#   • your mounted `claude` binary — a dynamically-linked glibc executable that
#     needs a standard C/C++ runtime and CA certificates for TLS to Anthropic.
# docker-cli is the CLIENT only (the daemon runs on the host, reached via the
# mounted socket). The Debian "docker.io" package ships only the daemon here.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      docker-cli ca-certificates libstdc++6 libgcc-s1 \
 && rm -rf /var/lib/apt/lists/*

# No COPY: the project (including web/app.py) is bind-mounted at the same absolute
# path it lives at on the host, and compose sets working_dir there.
CMD ["python3", "web/app.py"]
