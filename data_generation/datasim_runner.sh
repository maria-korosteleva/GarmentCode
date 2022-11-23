#!/bin/bash
# This script is needed to autorestart execution of simulating datapoints for a dataset in case of Maya\Qualoth hangs or crashes
# Use something like git bash to run this script on Win
# Note you might want to suppress Maya crash report requests to stop getting annoyin windows
#   * https://knowledge.autodesk.com/support/maya/troubleshooting/caas/sfdcarticles/sfdcarticles/How-to-Disable-or-Enable-Crash-Error-Reports-s.html
#   * https://forums.autodesk.com/t5/installation-licensing/disable-error-reporting/td-p/4071164 

# ensure killing is possible
# https://www.linuxjournal.com/article/10815

# Running with output to file (see https://askubuntu.com/questions/38126/how-to-redirect-output-to-screen-as-well-as-a-file)
#   ./datasim_runner.sh 2>&1  | tee -a <filename>

# Use Ctrl-C to stop this script after currently running mini-batch finishes
sigint()
{
   echo "Ctrl-C signal INT received, script ending after returning from datasim execution"
   exit 1
}
trap 'sigint'  INT

# -- Main calls --
num_samples=30   # number of reloads and re-sim vs. speed to detect Maya\Qualoth hang
per_sample_delay=$((7*60))  # give about 7 min per sample before detecting Maya to hang
dataset=data_5_pants_straight_sides_221122-19-44-29
config=T_body_green_intersect_tolerance.json
ret_code=1
STARTTIME=$(date +%s)
while [ $ret_code != 0 ]  # failed for any reason
do
    # https://unix.stackexchange.com/questions/405337/bash-if-command-doesnt-finish-in-x-time
    # set timeout to catch hangs && forse kill if not soft terminating
    # NOTE: update the location of mayapy.exe HERE!
    timeout -k 30 $((num_samples * per_sample_delay)) /c/Program\ Files/Autodesk/Maya2023/bin/mayapy.exe "./datasim.py" --data $dataset --minibatch $num_samples  --config $config
    ret_code=$?
    echo $ret_code   # if it's 124, the execution was finished by timeout

    # clear tmp files created by Qualoth -- they can be left after crashes && fill out all the free disk space
    find /tmp -regextype sed -regex "/tmp/tmp[0-9]*\.[0-9]*" -delete
    echo "Cleaned Qualoth cache!"

    ENDTIME=$(date +%s)
    T=$(($ENDTIME - $STARTTIME))
    echo "It took ${T} seconds to complete this task So far..."
    printf "Pretty format: %02dd %02dh %02dm %02ds\n" "$(($T/86400))" "$(($T/3600%24))" "$(($T/60%60))" "$(($T%60))"
done