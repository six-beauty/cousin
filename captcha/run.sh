svr_port=9903
cur_dir=$(pwd)

run_status=$(/usr/sbin/lsof -nP -i TCP:$svr_port |grep python)

if [[ ${#run_status} > 0 ]];
then
    echo 'captcha work still running, '${#run_status}
    exit 0
else
    nohup python3 captcha.py > /dev/null 2>&1 &
    echo 'captcha work stop('${#run_status}'), start work!'$(date +"%H:%M:%S")
fi

