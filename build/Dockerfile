#使用nvm管理node.js版本
FROM jenkins/jenkins:2.462.2-lts-jdk11

USER root

COPY nvm.sh /etc/profile.d/

ADD nvm-0.40.1.tar.gz /usr/local/

RUN chmod -R 777 /tmp \
    && apt update \
    && apt install python3 ansible rsync -y \
    && mkdir /etc/ansible \
    && . /etc/profile.d/nvm.sh \
    && nvm install v10.20.1 \
    && nvm install v12.22.12 \
    && nvm install v14.21.3 \
    && nvm install v16.20.1 \
    && nvm install v18.16.0 \
    && apt clean all \
    && rm -rf /var/lib/apt \
    && nvm use v10.20.1 \
    && npm install -g npm-cli-login --unsafe-perm \
    && nvm use v12.22.12 \
    && npm install -g npm-cli-login --unsafe-perm \
    && nvm use v14.21.3 \
    && npm install -g npm-cli-login --unsafe-perm \
    && nvm use v16.20.1 \
    && npm install -g npm-cli-login --unsafe-perm \
    && nvm use v18.16.0 \
    && npm install -g npm-cli-login --unsafe-perm \
    && nvm alias default v10.20.1
