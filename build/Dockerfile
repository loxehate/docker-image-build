# ===== builder 阶段 =====
FROM alpine:3.18.11 AS builder
ARG ANSIBLE_VAR=2.18.4

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

# 安装运行所需的最小依赖
RUN apk add --no-cache python3 bash openssh-client openssh-keygen

# 从 builder 拷贝 Python 和 Ansible 所有运行文件
COPY --from=builder /usr/lib/python3.*/site-packages /usr/lib/python3.11/site-packages
COPY --from=builder /usr/bin/ansible* /usr/bin/
COPY --from=builder /usr/bin/python3 /usr/bin/
COPY --from=builder /usr/bin/pip3 /usr/bin/
COPY --from=builder /usr/lib/libpython3* /usr/lib/

# 复制 ansible 配置
COPY ./ansible/ /etc/ansible/
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

WORKDIR /etc/ansible
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["tail", "-f", "/dev/null"]
