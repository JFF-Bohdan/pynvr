# pynvr
Python NVR (Network Video Recorder) based on OpenCV.

## General information

**pynvr** can interract with cameras using OpenCV (supports many types of connection including connection to USB cameras and network cameras using RTSP, for example)

Captured video stream must be analysed for motion and then saved to files according to specific rules.

When motion detected (or rule triggered) not only video **after** start must be saved but some frames **before** (pre-alarm/pre-event frames) must be saved to output file.

## Motion detection explanation

According to this image:
![Motion](./img/md3.png)

You can see four slides: 

1. upper-left corner - source image;
2. upper-right corner - processing **first processing stage**;
3. down-left corner - processing **second processing stage**;
4. down-right corner - source image with traces of all movements;

Explanation:

1. at first source image scaled down to 500px;
2. on **first processing stage** image converted to gray-scale and then blured using gaussian blur, then algorithm generates difference between current and previous frames;
3. on **second processing stage** difference images goes through dilate() with 8 iterations and then through erode() with 4 iterations;
4. next we need calculate non-zero (white) pixels count and decide if movement detected;
5. next we looking for motion contours and add them to original frame.

Script `motion_detection_test_with_contours.py` demonstrates internal mechanic of motion detection and merges images of all stages into one video stream, see details below.


## Configuration

### General information

You can find many configuration parameters in `config.py` file. You can tune them specially for your requirements.

`config.py` contains default configuration. You can override default settings using machine-specific configuration.


### Overriding configuration according to your requirements

You can specify machine specific configuration in file `machine_specific_configuration.py` which can be created in root directory.

As you can see in `config.py`:

```Python
#loading machine specific configuration
if os.path.exists(os.path.join(APP_ROOT, "machine_specific_configuration.py")):
    from machine_specific_configuration import *
```

it contains conditional include of file `machine_specific_configuration.py`. All information will be included from this file in case this file exists.

**Example**:

overriding `INITIAL_WAIT_INTERVAL_BEFORE_MOTION_DETECTION_SECS` parameter

file `config.py`:
```Python
INITIAL_WAIT_INTERVAL_BEFORE_MOTION_DETECTION_SECS = 5
```

file `machine_specific_configuration.py`:
```Python
INITIAL_WAIT_INTERVAL_BEFORE_MOTION_DETECTION_SECS = 20
```

In this case `INITIAL_WAIT_INTERVAL_BEFORE_MOTION_DETECTION_SECS` will be **20**

### Available parameters

#### Camera connection string

**`cam`** - camera connection string parameter.

Examples:
* `"0"` - connection to **default** camera, for example laptop built-in camera;
* `"rtsp://admin:fuTtJqR7@192.168.0.64:554/Streaming/channels/2/"` - RTSP connection to camera with credentials. In this exampe we connecting to my `Hikvision DS-2CD1321-I` camera secondary stream. Yes, I know that there is my password, it's OK.

### Logs setup

**`LOG_FILE_PATH`** - path to log files (string);

**`APP_LOG_LEVEL`** - debug logging level (enum from `logging`);


**`MAIN_LOG_FILE_MAX_SIZE`** - max size in bytes of log file before rolling over (int);

**`LOG_BACKUPS_COUNT`** - max count of backup log files (int);

**`LOG_FORMAT`** - logging format (string), for details see documentation for `loggig` module;

**`LOG_TO_CONSOLE`** - do we need send copy of logs to console (bool);

### Motion detection

**`INITIAL_WAIT_INTERVAL_BEFORE_MOTION_DETECTION_SECS`** - intial wait interval after connection to camera established. We need wait for some time, maybe camera need adjust parameters.

**`MINIMAL_MOTION_DURATION`** - minimal motion-event (video) duration when motion triggered, each any motions in this interval will prolongate motion-event (video).

### Pre-alarm/pre-event video

**`PRE_ALARM_RECORDING_SECONDS`** - how many seconds of video must be added to result video before alarm/trigger-event. 

Example:
```
{pre-event}-------{event-start}------{event-end}
```

### Video archive
**`PATH_FOR_VIDEO`** - path to video-archive, can be relative (string);

**`subFolderNameGeneratorFunc`** - function which can generate sub-folder to video-archive. Signature `subFolderNameGeneratorFunc(dts)` where `dts` is current timestamp in UTC (pointer to function or `None`).

Example, sub-folders generator can be:

```Python
def subFolderNameForDtsGeneratorFunc(dts):
    return "{:04}/{:02}/{:02}".format(dts.year, dts.month, dts.day)
```

In this case video-archive will be something like this:

```
video 
  |-2017-04-02
     |-video_2017-04-02T132017.avi
     |-video_2017-04-02T132017.avi
  |-2017-04-03
     |-video_2017-04-03T132017.avi
     |-video_2017-04-03T132017.avi
```

### Video settings
**`scaleFrameTo`** - scale initial frames to this size tuple of width and height, for example `scaleFrameTo = (500, 500)`


## Available scripts

`motion_detection_test_with_contours.py` - motion detection example with internal mechanic explanation;

`motion_detection_test.py` - motion detection example, without debug information;

`motion_driven_recorder.py` - video recorder example.

####  `motion_detection_test_with_contours.py`

Motion detection example with a lot of debug information: all internal mechanic available in merged output file.


#### `motion_detection_test.py`

Motion detection without debug frames.

#### `motion_driven_recorder.py`

Detects motion and then saves video files (with pre-alarm frames included) to output files.