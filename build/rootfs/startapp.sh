#!/bin/sh

set -e # Exit immediately if a command exits with a non-zero status.
set -u # Treat unset variables as an error.

mkdir -p /config/log/libreoffice

cd /config

# Deliberately NOT --headless: headless mode skips the GUI/X display
# entirely, which is exactly the rendering path we need for animation
# playback. Running under the base image's Xvfb instead gives us a real
# (virtual) display to render into, plus a free noVNC view for debugging.
#
# --accept opens a UNO listener so the process can be driven programmatically
# (see /opt/control_record.py, baked into this same image — source at
# docker-libreoffice-impress/rootfs/opt/control_record.py). Binding 0.0.0.0
# keeps the door open for external-client control (strategy A) later; for
# now it's driven via `docker exec` against localhost, which works the same
# either way.
exec soffice \
    --norestore \
    --nologo \
    --nodefault \
    -env:UserInstallation=file:///config/libreoffice-profile \
    --accept="socket,host=0.0.0.0,port=2002;urp;" \
    >> /config/log/libreoffice/output.log 2>> /config/log/libreoffice/error.log

# vim:ft=sh:ts=4:sw=4:et:sts=4
