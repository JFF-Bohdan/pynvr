import datetime as dts
from system.shared import LastErrorHolder
import time
import cv2 as cv


class CameraConnectionSupport(LastErrorHolder):
    def __init__(self, camConnectionString, logger):
        LastErrorHolder.__init__(self)
        self.logger = logger

        # date & time when class instance created
        self.started = dts.datetime.utcnow()

        # camera
        self.cap = None

        # frame height
        self.frameHeight = None

        # frame width
        self.frameWidth = None

        # total count of pixels
        self.nb_pixels = None

        self.camConnectionString = camConnectionString

    def utcNow(self):
        return dts.datetime.utcnow()

    def onFrameSizeUpdate(self, frameWidth, frameHeight):
        """
        Will be called when frame size will be updated or initialized

        :param frameWidth: new width
        :param frameHeight: new height
        :return:
        """

        pass

    def _initCamera(self, callSleep = True):
        """
        Initializes camera. If can't establish connection will write error message to log file and sleep for some
        interval.

        :return: True when camera successfully open, otherwise False
        """
        self.cap = cv.VideoCapture(self.camConnectionString)

        if self.cap is None:
            self.setError("can't connect to camera")
            if callSleep:
                time.sleep(5)
            return None

        if not self.cap.isOpened():  # did we get a connection at all ?
            self.setError("can't connect to camera")
            if callSleep:
                time.sleep(5)

            return None

        return self.cap
