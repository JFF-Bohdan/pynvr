from system.log_support import init_logger
import time
from system.motion_detection import *
import config
import datetime as dts
import numpy as np
from system.camera_support import CameraConnectionSupport
import os


class MotionDrivenRecorder(CameraConnectionSupport):
    def __init__(self, camConnectionString, logger):
        CameraConnectionSupport.__init__(self, camConnectionString, logger)

        #initializing motion detector
        self.detector = MotionDetector()
        self.detector.resizeBeforeDetect = False
        self.detector.multiFrameDetection = False

        self.inMotionDetectedState = False

        self.__camConnectionDts = None
        self.__canDetectMotion = False
        self.camFps = None

        self.preAlarmRecordingSecondsQty = 0

        self.__savedFrames = []

        self.__isRecording = False

        #output writer
        self.outputDirectory = None
        self.__output = None

    def __addPreAlarmFrame(self, frame):
        if self.preAlarmRecordingSecondsQty == 0:
            return

        if self.camFps is None:
            return

        totalQty = int(self.preAlarmRecordingSecondsQty * self.camFps)
        if len(self.__savedFrames) < totalQty:
            self.__savedFrames.append(frame)
            return

        self.__savedFrames.pop(0)
        self.__savedFrames.append(frame)

    def canDetectMotion(self):
        if self.__canDetectMotion:
            return True

        if self.__camConnectionDts is None:
            return False

        minDts = self.__camConnectionDts + dts.timedelta(seconds=config.INITIAL_WAIT_INTERVAL_BEFORE_MOTION_DETECTION_SECS)

        if minDts > self.utcNow():
            return False

        self.__canDetectMotion = True
        return True

    def setError(self, errorText):
        self.logger.error(errorText)
        return CameraConnectionSupport.setError(self, errorText)

    def _writeOutFrame(self, frame):
        assert self.__output is not None
        self.__output.write(frame)

    def _stopRecording(self):
        if self.__output is None:
            return

        self.__output.release()
        self.__output = None

        self.__isRecording = False

    def _startRecording(self):
        if self.outputDirectory is None:
            return self.setError("output directory is not specified")

        if None in [self.frameWidth, self.frameHeight]:
            return self.setError("resolution is't specified")

        # fourcc = cv.VideoWriter_fourcc(*'XVID')
        fourcc = cv.VideoWriter_fourcc('D','I','V','X') # MPEG-4 = MPEG-1

        videoSize = (self.frameWidth, self.frameHeight)

        #calculation output filename
        now = dts.datetime.utcnow()
        fileName = "video_{}.avi".format(now.strftime("%Y%m%dT%H%M%S"))
        fileName = os.path.join(self.outputDirectory, fileName)
        self.__output = cv.VideoWriter(fileName, fourcc, 20.0, videoSize)

        self.__isRecording = True
        return True

    def _flushPreRecordingFrames(self):
        """
        Writes pre-alarm frames to output file
        :return:
        """
        assert self.__output is not None

        for frame in self.__savedFrames:
            self.__output.write(frame)

        self.__savedFrames = []
        return True

    def loop(self):
        """
        Main loop for motion detection tester
        :return:
        """
        self.logger.info("main loop started")

        emptyFrame = None
        while True:
            #initializing connection to camera
            if self.cap is None:
                if not self._initCamera():
                    continue

                self.__camConnectionDts = self.utcNow()

            #reading frames from camera
            ret, current_frame = self.cap.read()

            #if can't read current frame - going to the next loop
            if (ret == False) or (current_frame is None): # the connection broke, or the stream came to an end
                continue

            current_frame = imutils.resize(current_frame, width=500)

            instant = time.time()  #get timestamp of the frame

            ############################################################
            ### calculating width and height of current video stream ###
            ############################################################

            frameHeight = np.size(current_frame, 0)
            frameWidth = np.size(current_frame, 1)

            if self.camFps is None:
                self.camFps = self.cap.get(cv.CAP_PROP_FPS)
                self.logger.info("FPS = {}".format(self.camFps))

            ############################################
            ### adding frame to pre-recording buffer ###
            ############################################
            if self.preAlarmRecordingSecondsQty > 0:
                self.__addPreAlarmFrame(current_frame)

            if emptyFrame is None:
                emptyFrame = np.zeros((frameHeight, frameWidth,3 ), np.uint8)

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
                #TODO: need process when recording now, or will be exception!
                self.onFrameSizeUpdate(frameWidth, frameHeight)

            ########################
            ### detecting motion ###
            ########################
            motionDetected = False

            #detection motion if can do it now
            if self.canDetectMotion():
                if self.detector.motionDetected(current_frame):
                    self.trigger_time = instant  # Update the trigger_time

                    if not self.inMotionDetectedState:
                        self.logger.info("something moved!")

                    motionDetected = True
                    self.inMotionDetectedState = True

            now = self.utcNow()
            #prolongating motion for minimal motion duration
            if (not motionDetected) and (self.detector.motionDetectionDts is not None):
                minDuration = self.detector.motionDetectionDts + dts.timedelta(seconds=config.MINIMAL_MOTION_DURATION)
                if minDuration > now:
                    motionDetected = True

            #clearing motion detection flag when needed
            if not motionDetected:
                self.inMotionDetectedState = False

                if self.__isRecording:
                    self._stopRecording()
            elif not self.__isRecording:
                self._startRecording()
                self._flushPreRecordingFrames()


            #calculating left seconds for motion (for further use in label)
            dx = 0
            if motionDetected:
                dx = now - self.detector.motionDetectionDts
                dx = config.MINIMAL_MOTION_DURATION - dx.seconds
            ############################################################
            ############################################################
            ############################################################
            #adding label for frame with detected motion
            if motionDetected:
                text = "MOTION DETECTED [{}]".format(dx)
                cv.putText(
                    current_frame,
                    text,
                    (10, 20),
                    cv.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 255), #b g r
                    2
                )

            if self.__isRecording:
                self._writeOutFrame(current_frame)

            #show current frame
            cv.imshow('frame', current_frame)

            #reading key and breaking loop when Esc or 'q' key pressed
            key = cv.waitKey(1)
            if (key & 0xFF == ord('q')) or (key == 27):
                break

        #stop recording if now recording
        if self.__isRecording:
            self._stopRecording()

        if self.cap is not None:
            self.cap.release()

        cv.destroyAllWindows()
        self.logger.info("main loop finished")

from system.shared import makeAbsoluteAppPath, mkdir_p

def main():
    logger = init_logger()
    logger.info("app started")

    ###########################################
    ### creating directory for output files ###
    ###########################################
    videoPath = config.PATH_FOR_VIDEO
    videoPath = makeAbsoluteAppPath(videoPath)
    if not os.path.exists(videoPath):
        logger.info("making directory for output files: {}".format(videoPath))

        if not mkdir_p(videoPath):
            logger.error("can't create directory for output files")
            return -1

    ##############################
    ### initializing processor ###
    ##############################
    processor = MotionDrivenRecorder(config.cam, logger)
    processor.preAlarmRecordingSecondsQty = config.PRE_ALARM_RECORDING_SECONDS
    processor.outputDirectory = videoPath

    processor.loop()

    logger.info("app finished")
    return 0

if __name__ == '__main__':
    ret = main()
    exit(ret)

