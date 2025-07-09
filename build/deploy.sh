#/usr/bin/env bash

file=./logs/gunicorn.pid
if [ -f "${file}" ];
then
 pid=`cat logs/gunicorn.pid`
 kill -9 ${pid}
 echo "kill pid: $pid"
 rm -rf logs/gunicorn.pid
fi

git fetch

git checkout self_build_zt

#git reset --hard origin develop
git reset --hard
git pull
#git pull origin develop
#git pull --force  origin develop
chmod 744 deploy.sh

pip install -i https://mirrors.aliyun.com/pypi/simple/ -r ./requirements.txt

#export FLASK_ENV=production

# 第一个app指的是app.py文件，第二个指的是flask应用的名字；
gunicorn -c gunicorn.conf.py app:app

while [[ ! -f "${file}" ]]
do
  sleep 5
done

pid=`cat logs/gunicorn.pid`
echo "start flask by pid: $pid"
