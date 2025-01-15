-- 创建数据库
CREATE DATABASE IF NOT EXISTS superset;

-- 创建用户并授予权限
CREATE USER IF NOT EXISTS 'superset'@'%' IDENTIFIED BY 'superset';
GRANT ALL PRIVILEGES ON superset.* TO 'superset'@'%';

-- 刷新权限
FLUSH PRIVILEGES;
