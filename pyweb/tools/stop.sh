svr_port=9902
cur_dir=$(pwd)

run_status=$(/usr/sbin/lsof -nP -i TCP:$svr_port |grep python3)

#work dir
cd $(pwd)/../bin

if [[ ${#run_status} > 0 ]];
then
    echo 'pyweb work is running, kill:'${run_status}
    pkill -f "python3 ../bin/core.py $svr_port"

    #check againt
    ps -ef |grep python3
fi

