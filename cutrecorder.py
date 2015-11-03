#!/usr/bin/python
#
print "-----------------------------------------------------------------------"
print "cutrecorder 0.6.1      by dan easley. begun in the late spring of 2015."
print "-----------------------------------------------------------------------"
print 
print "a simple interface for recording cuts, written with python, tk, & ecasound"
print
print "usage:"
print "    ./cutrecorder [config file]"
print "    if no config file is specified, program will look for 'cutrecorder.config'"
print

# system requirements:
#
#       jack audio connection kit   (low-level audio system)
#       ecasound                    (intermediary system for recording)
#       python-ecasound             (python library to interact with ecasound)
#       sox                         (for processing)
#       normalize-audio             (sox can normalize, but this is easier)
#
#       below-listed python modules

# import classes and procedures
import sys, os                      # parse command line arguments
import Tkinter as tk                # GUI library
import tkMessageBox                 # popup windows
from functools import partial       # advanced function calling (don't yet understand: using global variables instead (bad?! philosophy?!))
import ConfigParser                 # load configuration file
import time                         # display time in something other than floating point seconds
from pyeca import *                 # load ecasound for recording
import threading                    # run audio procedures in separate thread, so that gui remains responsive during recording
from threading import *             # (this or the previous line likely redundant)
from subprocess import *            # run system commands

# 
# changelog:
# 
#
# 0.6.1 20151103 de
#       fixed possible race condition with start and stop
#
# 0.6   20151101 de
#       implemented logging: environment variable must be set via "export ECASOUND_LOGFILE=~/cutrecorder/cutrecorder.log"
#       fixed intermittent timeout error by preventing race condition between get_current_position and pause/unpause
#           (see "horseholder" flag)
#       changed to stereo recording, with automatic mono-mixdown between recording and processing
#
# 0.5.1 20150814 de
#	    gave up on Cart Chunk - using filename
#
# 0.5   20150806 de
#       implemented saving cutnumber to Cart Chunk (using https://github.com/jmcmellen/cdputils)
#
# 0.4   20150619 de (beta)
#       configuration file: add boolean fields for normalizing, trimming, and stretching
#           sox & normalize-audio
#               1. normalize
#               1. trim head/tail
#               3. timestretch to specified duration
#       Possibly feature-ready for Valley Voice: test with volunteers
#
# 0.3.1 20150612 de
#       implemented stop-and-save button (to end before duration reached yet keep the recording)
#
# 0.3   20150611 de
#       implemented threading, classes (made gui responsive during recording)
#       implemented timer, status display, pause and cancel (w/ autopause and confirmation)
#       configuration file:
#          required global configuration options: configuration_name, directory, temporary_file
#          provided ability to place labels between cuts (by specifying a cut with a desired title, duration of '0', and filename of 'label'.)
#
# 0.2   20150601 de
#       use jack instead of alsa
#       broke audio recording by not understanding windows/classes/something
#       replaced json-formatted CUTSLIST file with proper config file using standard ConfigParser library
#
# 0.1   20150528 de
#       main window: two-column grid
#       reads a list of cuts from a json file and presents them as a group of radio buttons in the left column of the window
#       record button records using alsa (current position written to console) until it reaches duration
#       recording duration set in source
#               
# UI improvements:
#    combine record and pause/unpause buttons, renaming 'unpause' to 'resume'.  (record/pause/resume)
#    grey-out or hide cut selection area when recording is ongoing, or separate processes into separate windows/modes
#
# roadmap:
# 1.0   
#    ui improvements
#    code cleanup
#    error correction:
#        config file: missing file, missing sections, missing options, etc.
#        error correction for failed saves
#        audio subsystem failures (can't find [ecasound|portaudio|whatever])
#        non-realtime processing failures (can't find [sox|normalize-audio])
# 1.x
#    allow for variable channels per cut, specified within configuration file 
#        (currently hard-coded to mono^H^H^H^Hstereo-converted-to-mono)
#        specify both number of channels to record from and number of channels to save to
#    allow for different formats per cut, specified within configuration file
#    launch preferred text editor with configuration file open
#    implement Cart Chunk (perhaps via https://github.com/jmcmellen/cdputils)
# before 2.0
#    split Recorder class out to proper module with sensible threading/object-orientedness/etc.: make it a generically useful wrapper for pyeca
# 2.0
#    true configuration editing within program
#    possible move from pyeca (ecasound ECI) to either
#        pyAudio (portaudio interface) for better cross-platform compatibility
#         or
#        nama (ecasound wrapper) for additional features
#

# define Recorder class, using pyeca (python-ecasound bridge, hardcoded below for JACK on linux.  google ecasound-iam for rosettastone)

class Recorder(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.running = False
        self.horseholder = False
        self.e = ECA_CONTROL_INTERFACE(0)
        self.e.command("int-set-log-history-length 1024")
        self.e.command("int-log-history")
        self.e.command("cs-add rec_chainsetup")
        self.e.command("c-add 1st_chain")
        self.e.command('cs-set-audio-format 16,2,44100')
        self.e.command("cs-option -G:jack,cutrecorder,notransport")
        self.e.command("ai-add jack,system")
        print "Recording System Initialized."

    def start_recorder(self):
        if self.running == False:
            fileconnector = "ao-add " + temporary_file
            self.e.command(fileconnector)
            self.e.command("cs-connect")
            self.e.command("start")
            print "Recording Started; saving to ", cut_filepath
            status_text.set('RECORDING')
            pause_button_label.set('pause')
            self.running = True
            self.start()
        else:
            pass

    def stop_recorder(self):
        self.horseholder = True
        time.sleep(0.5)
        self.e.command("stop")
        self.e.command("cs-disconnect")
        self.running = False
        status_text.set('STOPPED.')
        print cut_normalize, cut_trim, cut_stretch
        print "Converting from stereo to mono."
        status_text.set('Making file monaural.')
        call(["cp", temporary_file, "temp-mono.wav"])
        call("sox temp-mono.wav " + temporary_file + " channels 1", shell = True)
        if cut_normalize == "True":
            status_text.set('Normalizing file.')
            print "Normalizing file."
            call("normalize-audio " + temporary_file, shell = True)
        if cut_trim == "True":
            status_text.set('Trimming file.')
            print "Trimming file."
            call(["cp", temporary_file, "temp-trim.wav"])
            call("sox temp-trim.wav " + temporary_file + " silence 1 0.1 -50d reverse silence 1 0.1 -60d reverse", shell = True)
            call("rm temp-trim.wav", shell = True)
        if cut_stretch == "True":
            status_text.set('Stretching file.')
            print "Stretching file."
            call(["cp", temporary_file, "temp-stretch.wav"])
            # get current duration
            find_duration = Popen("soxi -D temp-stretch.wav", shell = True, stdout=PIPE)
            actual_duration = float(find_duration.communicate()[0])
            # calculate factor
            factor = actual_duration / cut_duration
            # apply factor
            call("sox temp-stretch.wav " + temporary_file + " tempo -s " + str(factor), shell = True)
            call("rm temp-stretch.wav", shell = True)
        status_text.set('Copying to final destination.')
        call(["cp", temporary_file, cut_filepath])
        status_text.set('Deleting temporary file.')
        call(["rm", temporary_file])
        status_text.set('Recording Saved.')
        print "Recording Finished; ", cut_filepath, "saved."
        tkMessageBox.showinfo("Recording Saved", "Recording Finished and Saved.")
        os._exit(1)

    def cancel_recorder(self):
        if self.e.command("engine-status") == "running":
            self.pause_recorder()
        response = tkMessageBox.askquestion("Cancel Recording", "Are you sure you want to cancel the recording? (It's currently paused.)", icon='warning')
        if response == 'yes':
            self.e.command("cs-disconnect")
            status_text.set('cancelling')
            call(["rm", temporary_file])
            print "Recording Cancelled."
            os._exit(1)
        else:
            return

    def pause_recorder(self):
        self.horseholder = True
        time.sleep(0.5)
        if self.e.command("engine-status") == "stopped":
            self.e.command("start")
            time.sleep(0.3)
            self.horseholder = False
            status_text.set('Recording.')
            pause_button_label.set('pause')
            print "Recording Unpaused."
        else:
            self.e.command("stop")
            time.sleep(0.3)
            self.horseholder = False
            status_text.set('Paused.')
            pause_button_label.set('unpause')
            print "Recording Paused."

    def run(self):
        while self.running:
            time.sleep(0.5)
            if self.horseholder != True:
                self.e.command("cs-get-position")
                current_position = self.e.last_float()
                calculated_time = cut_duration - current_position
                formatted_time = '  %02d:%02d  ' % (calculated_time / 60, calculated_time % 60)
                displayed_time.set(formatted_time)
                if current_position >= cut_duration:
                    self.running = False
        self.stop_recorder()
        return

# define Application class
#----------------------------------------------------------------------
class App:

    # This code executes on application startup
    #----------------------------------------------------------------------
    def __init__(self):

        # main window
        root = tk.Tk()      # root is the GUI object.  it must be specified before the variables, as some displayed variables use Tk's StringVar function

        #----------------------------------------------------------------------
        # SET VARIABLES
        #----------------------------------------------------------------------

        # GLOBALS!

        # general variables
        global displayed_time
        displayed_time = tk.StringVar()
        displayed_time.set('  00:00  ')

        global status_text
        status_text = tk.StringVar()
        status_text.set('Select your recording.')

        global record_button_label
        record_button_label = tk.StringVar()
        record_button_label.set('record')

        global pause_button_label
        pause_button_label = tk.StringVar()
        pause_button_label.set('pause')

        global stop_button_label
        stop_button_label = tk.StringVar()
        stop_button_label.set('stop and save')

        global cancel_button_label
        cancel_button_label = tk.StringVar()
        cancel_button_label.set('cancel')

        # working cut variables
        global temporary_file
        temporary_file = "./holymackerel.wav"

        global cut_directory
        cut_directory = "./"

        global cut_filename
        cut_filename = tk.StringVar()
        cut_filename = "foobar.wav"

        global cut_number
        cut_number = "000001"

        global cut_filepath
        cut_filepath = cut_directory + cut_filename

        global cut_duration
        cut_duration = 60.0

        global calculated_time
        calculated_time = 60.0

        global cut_title
        cut_title = "The Origin of Consciousness in the Breakdown of the Bicameral Mind"

        global cut_normalize
        global cut_trim
        global cut_stretch
        cut_normalize = False
        cut_trim = False
        cut_stretch = False

        # parse command line arguments
        if len(sys.argv) > 1:
            configuration_file = sys.argv[1]
        else:
            configuration_file = "cutrecorder.config"


        #----------------------------------------------------------------------
        # IMPORT SETTINGS FROM CONFIGURATION FILE
        #----------------------------------------------------------------------

        print "Importing Settings from", configuration_file

        # read file
        config = ConfigParser.ConfigParser()
        config
        config.read(configuration_file)

        # method for getting stuff
        def configsectionmap(section):
            dict1 = {}
            options = config.options(section)
            for option in options:
                try:
                    dict1[option] = config.get(section, option)
                    if dict1[option] == -1:
                        DebugPrint("skip: %s" % option)
                except:
                    print("exception on %s!" % option)
            return dict1

        # get general settings
        root.title (configsectionmap("Settings")['configuration_name'])
        temporary_file = configsectionmap("Settings")['temporary_file']
        cut_directory = configsectionmap("Settings")['destination']
        print "Cuts will be saved in", cut_directory
        print

        # (individual cut / label information is grabbed by GUI selection button code)


        #----------------------------------------------------------------------
        # SET GUI ELEMENTS
        #----------------------------------------------------------------------

        root.geometry("1200x1000+0+0")
        root.configure(background="black")

        # list frame (left half of window)
        #----------------------------------------------------------------------
        listframe = tk.Frame(root)

        tk.Grid.rowconfigure(root, 0, weight=1)
        tk.Grid.columnconfigure(root, 0, weight=1)
        tk.Grid.rowconfigure(root, 1, weight=1)
        tk.Grid.columnconfigure(root, 1, weight=1)

        listframe.grid(row=0, column=0, sticky='')

        # populate cut selection buttons
        #----------------------------------------------------------------------
        filename = tk.StringVar()
        filename.set("foobar.wav") # initialize

        r = 0
        for cut in config.sections():
            if cut != "Settings":
                holder = ""
                title = configsectionmap(cut)['title']
                filename = configsectionmap(cut)['filename']
                if filename != "label":
                    number = configsectionmap(cut)['cutnumber']
                    duration = float(configsectionmap(cut)['duration'])
                    formatted_duration = '%02d:%02d' % (duration / 60, duration % 60)
                    normalize = configsectionmap(cut)['normalize']
                    trim = configsectionmap(cut)['trim']
                    stretch = configsectionmap(cut)['stretch']
                    button_text = title + "    [ length: " + formatted_duration + " ] "
                    print "Loaded", title, "of", duration, "seconds, to be saved as", filename
                    select_button = tk.Radiobutton(listframe, text=button_text, variable=holder, value=filename, indicatoron=0, width="70", command=partial(self.set_cut_filepath, filename, number, duration, title, normalize, trim, stretch), font=('times', 12, 'bold'), foreground='black', background='white', activebackground='goldenrod', selectcolor='tomato')
                    select_button.grid(row=r, column=0, ipadx=5, ipady=5, padx=5, pady=5, sticky='nsew')
                else:
                    label_text = title
                    print "Loaded label."
                    label = tk.Label(listframe, font=('times', 12, 'bold'), text=label_text)
                    label.grid(row=r, column=0, ipadx=5, ipady=5, padx=7, pady=5, sticky='nsew')
                r = r + 1

        # reset filename so user is forced to select a cut
        filename = "foobar.wav"

        # control frame (right half of window)
        #----------------------------------------------------------------------

        controlframe = tk.Frame(root)
        controlframe.grid(row=0, column=1, sticky='')

        clock = tk.Label(controlframe, textvariable = displayed_time, font=('times', 64, 'bold'), foreground='goldenrod', background='black')
        clock.grid(columnspan=2, row=0, column=0, ipadx=30, ipady=30, padx=10, pady=10, sticky='nsew')

        status = tk.Label(controlframe, textvariable = status_text, font=('times', 24, 'bold'), foreground='black', background='goldenrod')
        status.grid(columnspan=2, row=1, column=0, ipadx=30, ipady=30, padx=10, pady=10, sticky='nsew')

        record_button = tk.Button(controlframe, textvariable = record_button_label, font=('times', 32, 'bold'), foreground='red', background='white', width="15", command=partial(self.start_recording))
        record_button.grid(row=2, column=0, ipadx=10, ipady=10, padx=5, pady=12, sticky='nsew')

        pause_button = tk.Button(controlframe, textvariable = pause_button_label, font=('times', 32, 'bold'), foreground='green', background='white', width="15", command=partial(self.pause_recording))
        pause_button.grid(row=3, column=0, ipadx=10, ipady=10, padx=5, pady=12, sticky='nsew')

        stop_button = tk.Button(controlframe, textvariable = stop_button_label, font=('times', 32, 'bold'), foreground='blue', background='white', width="15", command=partial(self.stop_recording))
        stop_button.grid(row=4, column=0, ipadx=10, ipady=10, padx=5, pady=12, sticky='nsew')

        cancel_button = tk.Button(controlframe, textvariable = cancel_button_label, font=('times', 32, 'bold'), foreground='goldenrod', background='white', width="15", command=partial(self.cancel_recording))
        cancel_button.grid(row=5, column=0, ipadx=10, ipady=10, padx=5, pady=12, sticky='nsew')

        print "GUI Loaded"
	print

        #----------------------------------------------------------------------
        # Begin Main GUI Loop
        #----------------------------------------------------------------------

        root.mainloop()

    #----------------------------------------------------------------------
    # SELECT CUT
    #
    # When a selection button is pushed, it calls this code to put the selected cut's filename in the variable.
    #----------------------------------------------------------------------
    def set_cut_filepath(self, filename, number, duration, title, normalize, trim, stretch):
        global cut_directory
        global cut_filename
        global cut_number
        global cut_filepath
        global cut_duration
        global cut_title
        global cut_normalize
        global cut_trim
        global cut_stretch
        if filename != "label":
            cut_filename = filename
            cut_number = number
            cut_filepath = cut_directory + cut_number + "_" + cut_filename
            print cut_filepath
            cut_duration = duration
            cut_title = title
            cut_normalize = normalize
            cut_trim = trim
            cut_stretch = stretch
            status_text.set('Ready to record.')
            print "User selected", cut_title
        else:
            return

    #----------------------------------------------------------------------
    # START RECORDING
    #----------------------------------------------------------------------
    def start_recording(self):
        # Check if a file has been selected; if not, alert user; otherwise, call the start_recorder function of deck
        global cut_filename
        if cut_filename == "foobar.wav":
            print "Not recording, as user has not selected a cut."
            tkMessageBox.showinfo("Whoops!", "Please select a cut to record before pressing 'Record'.")
        else:
            deck.start_recorder()

    def pause_recording(self):
        deck.pause_recorder()

    def stop_recording(self):
        deck.running = False

    def cancel_recording(self):
        deck.cancel_recorder()


# Instantiate!
#----------------------------------------------------------------------

deck = Recorder()
Main = App()

