#!/bin/bash
#SBATCH --gpus=rtx_4090:1
#SBATCH --mem-per-cpu=8G
#SBATCH --time=1-5
#SBATCH --job-name=data_200_240116-14-25-39
#SBATCH --output=/cluster/work/sorkine/leonhard/mkorosteleva/output/data_200_240116-14-25-39/data_200_240116-14-25-39.out #TODO:depends on output path!

dataset_name=test_texture_5_240710-20-49-07
config=default_sim_props.yaml 
sim_default_bodies=false

# This script is needed to autorestart execution of simulating datapoints for a dataset in case of crashes
# Use something like git bash to run this script on Win
# Note you might want to suppress Maya crash report requests to stop getting annoyin windows
#   * https://knowledge.autodesk.com/support/maya/troubleshooting/caas/sfdcarticles/sfdcarticles/How-to-Disable-or-Enable-Crash-Error-Reports-s.html
#   * https://forums.autodesk.com/t5/installation-licensing/disable-error-reporting/td-p/4071164

# ensure killing is possible
# https://www.linuxjournal.com/article/10815

# sh ./datasim_runner.sh 3>&1 2>&1 > C:\Users\out.txt   (path to output file)

# Use Ctrl-C to stop this script after currently running mini-batch finishes
sigint()
{
   echo "Ctrl-C signal INT received, script ending after returning from datasim execution"
   exit 1
}
trap 'sigint'  INT

# -- Main calls --
ret_code=1
STARTTIME=$(date +%s)

while [ $ret_code != 0 ]  # failed for any reason
do
    if [ "$sim_default_bodies" = "true" ]; then
        python ./datasim.py --data $dataset_name --default_body --config $config
    else
        python ./datasim.py --data $dataset_name --config $config
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