#!/bin/bash
# This script is needed to autorestart execution of simulating datapoints for a dataset 
# in case of crashes and/or using mini-batches
# sh ./datasim_runner.sh 3>&1 2>&1 > C:\Users\out.txt   (path to output file)

dataset_name=my_dataset
config=default_sim_props.yaml 
sim_default_bodies=false
batch_size=100

# -- Main calls --
ret_code=1
STARTTIME=$(date +%s)

while [ $ret_code != 0 ]  # failed for any reason
do
    if [ "$sim_default_bodies" = "true" ]; then
        python ./pattern_data_sim.py --data $dataset_name --default_body --config $config -b $batch_size
    else
        python ./pattern_data_sim.py --data $dataset_name --config $config -b $batch_size
    fi

    ret_code=$?
    if [ $ret_code -eq 0 ]; then
        echo "The execution completed successfully."
    else
        echo "The execution failed with an error (ret_code: $ret_code)."
    fi

    ENDTIME=$(date +%s)
    T=$(($ENDTIME - $STARTTIME))
    echo "It took ${T} seconds to complete this task so far..."
    printf "Pretty format: %02dd %02dh %02dm %02ds\n" "$(($T/86400))" "$(($T/3600%24))" "$(($T/60%60))" "$(($T%60))"
done