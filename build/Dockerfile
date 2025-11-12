FROM fluentd:v1.19.0-debian-1.0
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl build-essential libgeoip-dev autoconf automake libtool libffi-dev \
    && curl -L -o /fluentd/GeoLite2-City.mmdb https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb\
    && fluent-gem install fluent-plugin-elasticsearch fluent-plugin-geoip fluent-plugin-rewrite-tag-filter \
    && apt-get autoclean \
    && gem sources --clear-all \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* /var/tmp/* /usr/lib/ruby/gems/*/cache/*.gem