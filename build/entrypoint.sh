#!/bin/bash

MITOGEN_PATH=$(pip show mitogen | grep Location | awk -F: '{print $2}' | sed 's| *$||')

echo "========== Ansible Mitogen Configuration =========="
echo "Using Mitogen strategy: mitogen_linear,mitogen_free,mitogen_host_pinned"
echo "strategy = mitogen_linear"
echo "strategy_plugins = ${MITOGEN_PATH}/ansible_mitogen/plugins/strategy"
echo "==================================================="

# 继续执行传入命令
exec "$@"
