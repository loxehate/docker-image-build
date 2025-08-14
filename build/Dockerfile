FROM alpine:3.18.11

#定义变量
ARG ANSIBLE_VAR=2.18.8

# 更新包索引并安装 Python 和 pip
# 安装 Ansible
#安装ansible插件
RUN apk update && apk add --no-cache python3 py3-pip bash openssh-client openssh-keygen && pip install ansible-core==${ANSIBLE_VAR} jmespath mitogen && ansible-galaxy collection install community.general

# 复制ansible配置文件
COPY ./ansible/ /etc/ansible/

# 复制并设置入口脚本
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# 设置工作目录
WORKDIR /etc/ansible

# 设置入口脚本并保持容器运行
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
# 运行 Ansible 命令
CMD ["tail","-f","/dev/null"]

