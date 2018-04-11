svr_port=8901
cur_dir=$(pwd)

run_status=$(/usr/sbin/lsof -nP -i TCP:$svr_port |grep python)

if [[ ${#run_status} > 0 ]];
then
    echo 'doubanrobot work still running, '${#run_status}
    exit 0
else
    nohup python doubanrobot.py > /dev/null 2>&1 &
    echo 'doubanrobot work stop('${#run_status}'), start work!'$(date +"%H:%M:%S")
fi

