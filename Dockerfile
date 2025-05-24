FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      # OpenGL & sound
      libgl1-mesa-glx \
      libpulse0 \
      # Basic glib
      libglib2.0-0 \
      # XCB (core + extras)
      libxcb1 \
      libxcb-xinerama0 \
      libxcb-icccm4 \
      libxcb-image0 \
      libxcb-keysyms1 \
      libxcb-render0 \
      libxcb-render-util0 \
      libxcb-shape0 \
      libxcb-shm0 \
      libxcb-sync1 \
      libxcb-xfixes0 \
      libxcb-xkb1 \
      # Additional X11 support
      libx11-6 \
      libx11-xcb1 \
      libxkbcommon0 \
      libxkbcommon-x11-0 \
      libfontconfig1 \
      libfreetype6 \
      libxi6 \
      libxrender1 \
      patch \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "-m", "app.main"]
