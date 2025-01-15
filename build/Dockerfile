FROM alpine:3.17.3

# 更新包索引并安装 Python 和 pip
RUN apk update && apk add --no-cache python3 py3-pip bash openssh-client openssh-keygen 

# 安装 Ansible
RUN pip install ansible-core==2.17.7 jmespath

#安装ansible插件
RUN ansible-galaxy collection install community.general

# 复制ansible配置文件
COPY ./ansible /etc/

# 设置工作目录
WORKDIR /etc/ansible

# 运行 Ansible 命令
CMD ["tail","-f","/dev/null"]

