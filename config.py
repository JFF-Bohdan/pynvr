import os
import logging

APP_ROOT = os.path.dirname(os.path.abspath(__file__))

JFF_DELL_LAPTOP_UID = "5f5cd6de-05ff-43f4-89c5-8aaeecaa534c"
DEFAULT_INSTANCE = "03a8624f-c620-4196-abd5-d27444b5d030"

#loading instance UID
if os.path.exists(os.path.join(APP_ROOT, "instance_uid.py")):
    from instance_uid import INSTANCE_UID
else:
    INSTANCE_UID = DEFAULT_INSTANCE

#######################
### camera settings ###
#######################
#Here you can specify connection string to camera
#Examples:
# cam = "rtsp://login:password@ip:port/stream_url" #connection to camera via RTSP with credentials
cam = 0 #use local camera

#####################
### logs settings ###
#####################
#folder where logs will be stored
LOG_FILE_PATH = os.path.normpath(os.path.join(APP_ROOT, './logs/vmd_dvr.log'))

#log level for logging
APP_LOG_LEVEL = logging.DEBUG

#max size for log file in bytes
MAIN_LOG_FILE_MAX_SIZE = 1024*1024*32

#max count for log files
LOG_BACKUPS_COUNT      = 20

#log format
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

#send copy of all log messages to console
LOG_TO_CONSOLE = True

#################################
### motion detection settings ###
#################################
INITIAL_WAIT_INTERVAL_BEFORE_MOTION_DETECTION_SECS = 5
MINIMAL_MOTION_DURATION = 10


##########################
### recording settings ###
##########################
PRE_ALARM_RECORDING_SECONDS = 5
PATH_FOR_VIDEO = "./video"

##################################
### instance specific settings ###
##################################
if INSTANCE_UID == JFF_DELL_LAPTOP_UID:
    #NOTE: Yes! I know that there is password from my dev. camera. It's OK
    cam = "rtsp://admin:fuTtJqR7@192.168.0.64:554/Streaming/channels/2/" #connection to my dev. camera
    MINIMAL_MOTION_DURATION = 5
    # cam = 0
    # INITIAL_WAIT_INTERVAL_BEFORE_MOTION_DETECTION_SECS = 0


