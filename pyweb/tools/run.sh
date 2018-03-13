svr_port=9902
cur_dir=$(pwd)

run_status=$(/usr/sbin/lsof -nP -i TCP:$svr_port |grep python3)

#work dir
cd $(pwd)/../bin

if [[ ${#run_status} > 0 ]];
then
    echo 'pyweb work still running, '${run_status}
    exit 0
else
    nohup python3 ../bin/core.py ${svr_port} > /dev/null 2>&1 &
    echo 'pyweb work stop('${#run_status}'), start work! '$(date +"%Y-%m-%d %H:%M:%S")
fi

