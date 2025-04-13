# syntax=docker/dockerfile:1

FROM ubuntu:22.04

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends build-essential python3 python3-pip python3-dev \
    libpng-dev libtiff5-dev libjpeg-dev libmp3lame0 libsdl2-2.0 xserver-xorg libglib2.0-0 python-is-python3 fontconfig --no-install-recommends

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN useradd -m appuser

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt to avoid having to copy them into
# into this layer.
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=./include/carla-0.9.15-cp310-cp310-linux_x86_64.whl,target=./include/carla-0.9.15-cp310-cp310-linux_x86_64.whl \
    python -m pip install ./include/carla-0.9.15-cp310-cp310-linux_x86_64.whl

# Switch to the non-privileged user to run the application.
USER appuser

# Copy the source code into the container.
COPY --chown=appuser:appuser . .

# Run the application.
ENTRYPOINT ["python3", "manual_control.py"]