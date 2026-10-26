FROM docker.io/jlesage/baseimage-gui:alpine-3.24-v4

WORKDIR /tmp

ARG ALPINE_MIRROR=""

RUN \
    if [ -n "$ALPINE_MIRROR" ]; then \
        sed -i "s#https://dl-cdn.alpinelinux.org/alpine#${ALPINE_MIRROR%/}#g" /etc/apk/repositories; \
    fi

# libreoffice-impress alone aborts on bootstrap (config-manager
# RuntimeException validating main.xcd without the other app modules'
# registry fragments) — libreoffice-writer is the minimal addition that
# satisfies it, verified against a real .pptx load + UNO drive. Draw,
# Calc, Base, and Math aren't needed and are left out.

# libreoffice-common also provides the Python UNO bindings we need
# (py3.14:uno / pyuno.so) for the in-container control script.
RUN \
    add-pkg \
        libreoffice-impress \
        libreoffice-writer \
        imagemagick \
        ffmpeg \
        xdotool

# Fonts — as broad a set as Alpine packages, to minimize substitution when
# rendering decks authored on real PowerPoint.
RUN \
    add-pkg \
        font-carlito \
        font-croscore \
        font-liberation \
        font-noto-all \
        font-noto-cjk \
        font-noto-cjk-extra \
        font-noto-emoji \
        font-dejavu \
        font-freefont \
        font-opensans && \
    fc-cache -f

# Add files: startapp.sh (the base image execs this once Xvfb/supervision is
# ready) and opt/control_record.py (the in-container recorder — baked into
# the image rather than docker cp'd in per job, since it's the same script
# every time; only the per-job .pptx and plan.json still get copied in at
# runtime). Placed last, after the expensive package/font RUN layers above,
# so editing the script only invalidates this cheap COPY layer and the
# trivial RUN below it, not a full package reinstall.
COPY rootfs/ /

RUN \
    sed -i 's/\r$//' /startapp.sh /opt/control_record.py && \
    chmod 0755 /startapp.sh /opt/control_record.py && \
    set-cont-env APP_NAME "LibreOffice" && \
    true

# UNO listener — only needed for an external client connecting to the
# socket directly. Left commented out since control_record.py drives it via
# `docker exec` against localhost instead, to avoid opening the port by
# default.
# EXPOSE 2002

VOLUME ["/config"]

LABEL \
      org.label-schema.name="docker-libreoffice-impress" \
      org.label-schema.description="LibreOffice Impress under Xvfb, UNO-controllable — records animation-playback video" \
      org.label-schema.schema-version="1.0"
