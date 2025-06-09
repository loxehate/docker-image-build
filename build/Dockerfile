FROM alpine:3.18.11

#定义变量
ARG ANSIBLE_VAR=2.18.4

# 更新包索引并安装 Python 和 pip
RUN apk update && apk add --no-cache python3 py3-pip bash openssh-client openssh-keygen 

# 安装 Ansible
RUN pip install ansible-core==${ANSIBLE_VAR} jmespath mitogen

#安装ansible插件
RUN ansible-galaxy collection install community.general

# 复制ansible配置文件
COPY ./ansible /etc/

# 配置mitogen插件
RUN cat /etc/ansible/ansible.cfg | grep strategy_plugins
# RUN sed -i "s|^#strategy_plugins *=.*|strategy_plugins = $(pip show mitogen | grep Location | awk -F: '{print $2}' | sed 's| *$||')/ansible_mitogen/plugins/strategy|" /etc/ansible/ansible.cfg
# RUN sed -i "s|^#strategy *=.*|strategy = mitogen_linear|" /etc/ansible/ansible.cfg

# 设置工作目录
WORKDIR /etc/ansible

# 运行 Ansible 命令
CMD ["tail","-f","/dev/null"]

