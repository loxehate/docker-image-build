# ===== builder 阶段 =====
FROM alpine:3.18.11 AS builder
ARG ANSIBLE_VAR=2.18.8

RUN apk add --no-cache \
        python3 \
        py3-pip \
        bash \
        openssh-client \
        openssh-keygen \
        build-base \
        libffi-dev \
        openssl-dev \
    && pip install --no-cache-dir \
        ansible-core==${ANSIBLE_VAR} \
        jmespath \
        mitogen \
    && ansible-galaxy collection install community.general

# ===== final 阶段 =====
FROM alpine:3.18.11
COPY --from=builder /usr/lib/python3.*/site-packages /usr/lib/python3.*/site-packages
COPY --from=builder /usr/bin/ansible* /usr/bin/
COPY --from=builder /usr/bin/python3 /usr/bin/
COPY --from=builder /usr/bin/pip3 /usr/bin/
COPY --from=builder /usr/lib/libpython3* /usr/lib/

RUN apk add --no-cache python3 bash openssh-client openssh-keygen

COPY ./ansible/ /etc/ansible/
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

WORKDIR /etc/ansible
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["tail", "-f", "/dev/null"]
