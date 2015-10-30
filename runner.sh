#!/bin/bash

# Cut Recorder wrapper script

# stupid hack to make sure we're in the working directory.  autostart file should do this but doesn't.

cd /home/dan/cutrecorder

# wait 15 seconds for system to finish booting

sleep 15s

# load Meter, connect to system input, set size and position of window

jalv.gtk http://gareus.org/oss/lv2/meters#dBTPmono &

sleep 10s
jack_connect system:capture_1 "True-Peak Meter (Mono):in"
jack_connect system:capture_2 "True-Peak Meter (Mono):in"

# Run Cut Recorder in infinite loop

while true; do
	wmctrl -r Iceweasel -e 0,1281,0,1278,1000
	xdotool search --name "Meter" windowsize 78 980 windowmove 1190 24
	jack_connect system:capture_1 "True-Peak Meter (Mono):in"
	jack_connect system:capture_2 "True-Peak Meter (Mono):in"
	./cutrecorder.py
done

