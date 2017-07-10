from system.log_support import init_logger

import config
import time
import os
from system.shared import makeAbsoluteAppPath, mkdir_p
import signal
from nvr_classes.motion_driven_recorder import MotionDrivenRecorder
import threading


nvr_thread = None
quit_loop = False


def signal_handler(signal, frame):
    global nvr_thread
    global quit_loop

    quit_loop = True
    nvr_thread.add_stop_request()


class NVRThread(threading.Thread):
    def __init__(self, logger, video_path):
        threading.Thread.__init__(self)
        self._logger = logger
        self._video_path = video_path

        self._processor = None

    def run(self):
        print("nvr thread id = {}".format(threading.current_thread().ident))

        self._processor = MotionDrivenRecorder(config.cam, self._logger)
        self._processor.preAlarmRecordingSecondsQty = config.PRE_ALARM_RECORDING_SECONDS
        self._processor.outputDirectory = self._video_path
        self._processor.subFolderNameGeneratorFunc = config.subFolderNameGeneratorFunc
        self._processor.scaleFrameTo = config.scaleFrameTo

        self._processor.start()

        print("nvr thread id = {}".format(threading.current_thread().ident))
        print "Done"

    def add_stop_request(self):
        self._processor.add_stop_request()



def main():
    logger = init_logger()
    logger.info("app started")
    logger.info("main thread id = {}".format(threading.current_thread().ident))

    # creating directory for output files
    videoPath = config.PATH_FOR_VIDEO
    videoPath = makeAbsoluteAppPath(videoPath)
    if not os.path.exists(videoPath):
        logger.info("making directory for output files: {}".format(videoPath))

        if not mkdir_p(videoPath):
            logger.error("can't create directory for output files")
            return -1

    global nvr_thread
    nvr_thread = NVRThread(logger, videoPath)
    nvr_thread.setDaemon(False)
    nvr_thread.start()

    global quit_loop
    while not quit_loop:
        time.sleep(1)

    logger.info("joining...")
    nvr_thread.join()
    logger.info("app finished")

    return 0


# import uuid
import cv2 as cv

if __name__ == "__main__":
    print("cv.__version__ = {}".format(cv.__version__))

    # initializing Ctrl-C handler
    signal.signal(signal.SIGINT, signal_handler)
    main()
    print("Done")
