FROM docker.elastic.co/beats/filebeat:8.17.2
USER root
RUN apt-get update && apt-get install -y systemd && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
USER 1000