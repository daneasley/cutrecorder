#!/bin/bash

# Cut Recorder wrapper script

# stupid hack to make sure we're in the working directory.  autostart file should do this but doesn't.
    cd ~/cutrecorder

# wait 15 seconds for system to finish booting
    echo Waiting 15 seconds.
    sleep 15s

# load Meter,wait a bit for that to happen, connect it to system inputs, set size and position of window
    echo Starting Meter System.
    jalv.gtk http://gareus.org/oss/lv2/meters#dBTPmono &
    sleep 10s
    jack_connect system:capture_1 "True-Peak Meter (Mono):in"
    jack_connect system:capture_2 "True-Peak Meter (Mono):in"

# Logging
    echo Configuring Logging System.
    # delete log file
        rm logfile.txt
    # set log file variable                                             ***********************************
        export ECASOUND_LOGFILE=~/cutrecorder/cutrecorder.log
    # run following code in separate (minimized) terminal window                fix these!!!
        #watch -n 1 -d tail --lines 40 ~/cutrecorder.log                ***********************************

# Run Cut Recorder in infinite loop (performing kludgy cleanup on other applications' window size/locations each iteration)
    echo Beginning recorder loop.
    while true; do
        # move/resize Web Browser window to all of second monitor
        wmctrl -r Iceweasel -e 0,1281,0,1278,1000
        # make sure meter is in right spot and size
        xdotool search --name "Meter" windowsize 78 980 windowmove 1190 24
        # make sure both inputs are connected to meter
        jack_connect system:capture_1 "True-Peak Meter (Mono):in"
        jack_connect system:capture_2 "True-Peak Meter (Mono):in"
        # run cutrecorder with different configuration file based on day
        case "$(date +%a)" in 
            Mon) 
                ./cutrecorder.py monday.config
                ;;
            Tue|Wed|Thu|Fri)
                ./cutrecorder.py tuesdaythroughfriday.config
                ;;
            Sat|Sun) 
                ./cutrecorder.py weekend.config
                ;;
        esac
        sleep 2s
    done

echo Terminating.

