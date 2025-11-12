FROM fluentd:v1.19.0-debian-1.0
USER root
ADD GeoLite2-City.mmdb /fluentd/GeoLite2-City.mmdb
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libgeoip-dev autoconf automake libtool libffi-dev \
    && fluent-gem install fluent-plugin-elasticsearch fluent-plugin-geoip fluent-plugin-rewrite-tag-filter \
    && apt-get autoclean \
    && gem sources --clear-all \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* /var/tmp/* /usr/lib/ruby/gems/*/cache/*.gem