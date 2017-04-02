from system.log_support import init_logger
import time
from system.motion_detection import *
import config
import datetime as dts
import numpy as np
from system.camera_support import CameraConnectionSupport

class MotionDetectionTester(CameraConnectionSupport):
    def __init__(self, camConnectionString, logger):
        CameraConnectionSupport.__init__(self, camConnectionString, logger)

        #initializing motion detector
        self.detector = MotionDetectorV3Traced()
        self.detector.resizeBeforeDetect = False
        self.detector.multiFrameDetection = False

        self.inMotionDetectedState = False

        self.__camConnectionDts = None
        self.__canDetectMotion = False

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

            current_frame = imutils.resize(current_frame, width=500, height=500)

            instant = time.time()  #get timestamp of the frame

            ############################################################
            ### calculating width and height of current video stream ###
            ############################################################

            frameWidth = np.size(current_frame, 0)
            frameHeight = np.size(current_frame, 1)

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

            #show current frame
            cv.imshow('frame', current_frame)

            #reading key and breaking loop when Esc or 'q' key pressed
            key = cv.waitKey(1)
            if (key & 0xFF == ord('q')) or (key == 27):
                break

        if self.cap is not None:
            self.cap.release()

        cv.destroyAllWindows()
        self.logger.info("main loop finished")

def main():
    logger = init_logger()
    logger.info("app started")

    processor = MotionDetectionTester(config.cam, logger)
    processor.loop()

    logger.info("app finished")

if __name__ == '__main__':
    main()

