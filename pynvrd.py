from system.log_support import init_logger
import time
import cv2 as cv
from system.motion_detection import MotionDetector
import imutils
import config
import datetime as dts
import numpy as np
from system.camera_support import CameraConnectionSupport
import os
from system.shared import makeAbsoluteAppPath, mkdir_p
import signal


def signal_handler(signal, frame):
    print("Quit by Ctrl-C")
    exit(0)


class MotionDrivenRecorder(CameraConnectionSupport):
    def __init__(self, camConnectionString, logger):
        CameraConnectionSupport.__init__(self, camConnectionString, logger)

        # initializing motion detector
        self.detector = MotionDetector()
        self.detector.resizeBeforeDetect = False
        self.detector.multiFrameDetection = False

        self.inMotionDetectedState = False

        self._camConnectionDts = None
        self._canDetectMotion = False
        self.camFps = None

        self.preAlarmRecordingSecondsQty = 0

        self._savedFrames = []

        self._isRecording = False

        # output writer
        self.outputDirectory = None
        self._output = None

        self.subFolderNameGeneratorFunc = None
        self._prevSubFolder = None
        self.scaleFrameTo = None

    def _addPreAlarmFrame(self, frame):
        if self.preAlarmRecordingSecondsQty == 0:
            return

        if self.camFps is None:
            return

        totalQty = int(self.preAlarmRecordingSecondsQty * self.camFps)
        if len(self._savedFrames) < totalQty:
            self._savedFrames.append(frame)
            return

        if len(self._savedFrames) > 0:
            self._savedFrames.pop(0)

        self._savedFrames.append(frame)

    def canDetectMotion(self):
        if self._canDetectMotion:
            return True

        if self._camConnectionDts is None:
            return False

        minDts = self._camConnectionDts + dts.timedelta(seconds=config.INITIAL_WAIT_INTERVAL_BEFORE_MOTION_DETECTION_SECS)

        if minDts > self.utcNow():
            return False

        self._canDetectMotion = True
        return True

    def setError(self, errorText):
        self.logger.error(errorText)
        return CameraConnectionSupport.setError(self, errorText)

    def _writeOutFrame(self, frame):
        assert self._output is not None
        self._output.write(frame)

    def _stopRecording(self):
        if self._output is None:
            return

        self._output.release()
        self._output = None

        self._isRecording = False

    def _getSubFolderName(self, dts):
        if self.subFolderNameGeneratorFunc is None:
            return None

        return self.subFolderNameGeneratorFunc(dts)

    def _startRecording(self):
        if self.outputDirectory is None:
            return self.setError("output directory is not specified")

        if None in [self.frameWidth, self.frameHeight]:
            return self.setError("resolution is't specified")

        fourcc = cv.VideoWriter_fourcc(*config.FOURCC_CODEC)
        videoSize = (self.frameWidth, self.frameHeight)

        # calculation output filename
        now = dts.datetime.utcnow()
        fileName = "video_{}{}".format(now.strftime("%Y%m%dT%H%M%S"), config.OUTPUT_FILES_EXTENSION)

        subFolder = self._getSubFolderName(now)
        if subFolder is not None:
            needCreate = ((self._prevSubFolder is not None) or (subFolder != self._prevSubFolder))

            dirName = os.path.join(self.outputDirectory, subFolder)
            dirName = os.path.normpath(dirName)

            if (needCreate) and (not os.path.exists(dirName)):
                self.logger.info("adding new directory: {}".format(dirName))
                if not mkdir_p(dirName):
                    return self.setError("can't create sub-directory: {}".format(dirName))

            fileName = os.path.join(dirName, fileName)
        else:
            fileName = os.path.join(self.outputDirectory, fileName)

        self._output = cv.VideoWriter(fileName, fourcc, config.OUTPUT_FRAME_RATE, videoSize)

        self._isRecording = True
        return True

    def _flushPreRecordingFrames(self):
        """
        Writes pre-alarm frames to output file
        :return:
        """
        assert self._output is not None

        for frame in self._savedFrames:
            self._output.write(frame)

        self._savedFrames = []
        return True

    def _detect_motion(self, current_frame, instant):
        # detection motion if can do it now
        if not self.canDetectMotion():
            return False

        if not self.detector.motionDetected(current_frame):
            return False

        self.trigger_time = instant  # Update the trigger_time

        if not self.inMotionDetectedState:
            self.logger.info("something moved!")

        self.inMotionDetectedState = True
        return True


    def start(self):  # noqa
        """
        Main loop for motion detection tester
        :return:
        """
        self.logger.info("main loop started")

        emptyFrame = None

        prev_logged_left_seconds = None

        while True:
            # initializing connection to camera
            if self.cap is None:
                if not self._initCamera():
                    continue

                self._camConnectionDts = self.utcNow()

            ret, current_frame = self.cap.read()

            # if can't read current frame - going to the next loop
            if (not ret) or (current_frame is None):  # the connection broke, or the stream came to an end
                continue

            if self.scaleFrameTo is not None:
                current_frame = imutils.resize(current_frame, width=self.scaleFrameTo[0], height=self.scaleFrameTo[1])

            # get timestamp of the frame
            instant = time.time()

            frameHeight = np.size(current_frame, 0)
            frameWidth = np.size(current_frame, 1)

            if self.camFps is None:
                self.camFps = self.cap.get(cv.CAP_PROP_FPS)
                self.logger.info("FPS = {}".format(self.camFps))

            # adding frame to pre-recording buffer 
            if self.preAlarmRecordingSecondsQty > 0:
                self._addPreAlarmFrame(current_frame)

            if emptyFrame is None:
                emptyFrame = np.zeros((frameHeight, frameWidth, 3), np.uint8)

            resolutionChanged = False
            if None in [self.frameWidth, self.frameHeight]:
                self.frameWidth = frameWidth
                self.frameHeight = frameHeight
                self.nb_pixels = self.frameWidth * self.frameHeight

                self.logger.info("self.width = {}".format(self.frameWidth))
                self.logger.info("self.height = {}".format(self.frameHeight))

                resolutionChanged = True
            else:
                resolutionChanged = ((self.frameWidth != frameWidth) or (self.frameHeight != frameHeight))

            if resolutionChanged:
                # TODO: need process when recording now, or will be exception!
                self.onFrameSizeUpdate(frameWidth, frameHeight)

            # detecting motion
            motionDetected = self._detect_motion(current_frame, instant)

            now = self.utcNow()
            # prolongating motion for minimal motion duration
            if (not motionDetected) and (self.detector.motionDetectionDts is not None):
                minDuration = self.detector.motionDetectionDts + dts.timedelta(seconds=config.MINIMAL_MOTION_DURATION)
                if minDuration > now:
                    motionDetected = True

            # clearing motion detection flag when needed
            if not motionDetected:
                self.inMotionDetectedState = False

                if self._isRecording:
                    self.logger.info("stopping recording...")
                    self._stopRecording()

            elif not self._isRecording:
                self.logger.info("starting recording...")
                self._startRecording()
                self._flushPreRecordingFrames()

            # calculating left seconds for motion (for further use in label)
            dx = 0
            if motionDetected:
                dx = now - self.detector.motionDetectionDts
                dx = config.MINIMAL_MOTION_DURATION - dx.seconds

            if prev_logged_left_seconds != dx:
                self.logger.info("left seconds for motion recording: {}".format(dx))
                prev_logged_left_seconds = dx

            # adding label for frame with detected motion
            if motionDetected:
                text = "MOTION DETECTED [{}]".format(dx)
                cv.putText(
                    current_frame,
                    text,
                    (10, 20),
                    cv.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 255),  # b g r
                    2
                )

            if self._isRecording:
                self._writeOutFrame(current_frame)

        # stop recording if now recording
        if self._isRecording:
            self._stopRecording()

        if self.cap is not None:
            self.cap.release()

        cv.destroyAllWindows()
        self.logger.info("main loop finished")


def main():
    logger = init_logger()
    logger.info("app started")

    # creating directory for output files
    videoPath = config.PATH_FOR_VIDEO
    videoPath = makeAbsoluteAppPath(videoPath)
    if not os.path.exists(videoPath):
        logger.info("making directory for output files: {}".format(videoPath))

        if not mkdir_p(videoPath):
            logger.error("can't create directory for output files")
            return -1

    # initializing processor
    processor = MotionDrivenRecorder(config.cam, logger)
    processor.preAlarmRecordingSecondsQty = config.PRE_ALARM_RECORDING_SECONDS
    processor.outputDirectory = videoPath
    processor.subFolderNameGeneratorFunc = config.subFolderNameGeneratorFunc
    processor.scaleFrameTo = config.scaleFrameTo

    processor.start()

    logger.info("app finished")
    return 0


if __name__ == "__main__":
    # initializing Ctrl-C handler
    signal.signal(signal.SIGINT, signal_handler)

    ret = main()
    exit(ret)
