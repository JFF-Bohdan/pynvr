import cv2 as cv
from system.shared import LastErrorHolder
import imutils
import numpy as np
import datetime


class MotionDetectorBase(LastErrorHolder):
    """
    Base class for motion detection support
    """
    def __init__(self):
        LastErrorHolder.__init__(self)
        # previous frame
        self.prevFrame = None

        # DTS (date & time) of moment when last motion was detected
        self.motionDetectionDts = None

        self.resizeBeforeDetect = True

        self.multiFrameDetection = False

    def preprocessInputFrame(self, newFrame):
        if self.resizeBeforeDetect:
            return imutils.resize(newFrame, width=500, height=500)

        return newFrame.copy()

    def checkMotionDetected(self, frame):
        """
        Checks that motion detected.

        :param frame: new frame from camera
        :return: True when motion detected, otherwise False
        """
        return False

    def updateMotionDetectionDts(self):
        self.motionDetectionDts = datetime.datetime.utcnow()


class MotionDetectorV1(MotionDetectorBase):
    def __init__(self):
        MotionDetectorBase.__init__(self)
        self.threshold = 8

    def motionDetected(self, new_frame):
        frame = self.preprocessInputFrame(new_frame)

        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        gray = cv.GaussianBlur(gray, (21, 21), 0)

        if self.prevFrame is None:
            self.prevFrame = gray
            return False

        # compute the absolute difference between the current frame and
        # first frame
        frameDelta = cv.absdiff(gray, self.prevFrame)
        thresh = cv.threshold(frameDelta, 25, 255, cv.THRESH_BINARY)[1]

        # dilate the thresholded image to fill in holes, then find contours
        # on thresholded image
        thresh = cv.dilate(thresh, None, iterations=2)
        (cnts, _, _) = cv.findContours(thresh.copy(), cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

        height = np.size(gray, 0)
        width = np.size(gray, 1)
        nb = height * width

        qty = 0
        for c in cnts:
            a = cv.boundingRect(c)

            (x, y, w, h) = a
            s = w * h

            pcs = (float(s) / float(nb)) * 100

            if pcs < self.threshold:
                continue

            # cv.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            qty += 1
            break

        # cv.imshow("frame", frame)
        self.prevFrame = gray

        ret = (qty > 0)
        if ret:
            self.updateMotionDetectionDts()

        return ret


class MotionDetectorV2(MotionDetectorBase):
    def __init__(self):
        MotionDetectorBase.__init__(self)
        self.threshold = 1

    def motionDetected(self, new_frame):
        frame = self.preprocessInputFrame(new_frame)

        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        gray = cv.GaussianBlur(gray, (21, 21), 0)

        if self.prevFrame is None:
            self.prevFrame = gray
            return False

        frameDiff = cv.absdiff(gray, self.prevFrame)

        # kernel = np.ones((5, 5), np.uint8)

        opening = cv.morphologyEx(frameDiff, cv.MORPH_OPEN, None)  # noqa
        closing = cv.morphologyEx(frameDiff, cv.MORPH_CLOSE, None)  # noqa

        ret1, th1 = cv.threshold(frameDiff, 10, 255, cv.THRESH_BINARY)

        height = np.size(th1, 0)
        width = np.size(th1, 1)

        nb = cv.countNonZero(th1)

        avg = (nb * 100) / (height * width)  # Calculate the average of black pixel in the image

        self.prevFrame = gray

        # cv.DrawContours(currentframe, self.currentcontours, (0, 0, 255), (0, 255, 0), 1, 2, cv.CV_FILLED)
        # cv.imshow("frame", current_frame)

        ret = avg > self.threshold   # If over the ceiling trigger the alarm

        if ret:
            self.updateMotionDetectionDts()

        return ret


class MotionDetectorV3(MotionDetectorBase):
    def __init__(self):
        MotionDetectorBase.__init__(self)

        self.threshold = 1000
        self.prevPrevFrame = None

    def diffImg(self, t0, t1, t2):
        d1 = cv.absdiff(t2, t1)
        d2 = cv.absdiff(t1, t0)
        return cv.bitwise_and(d1, d2)

    def motionDetected(self, new_frame):
        frame = self.preprocessInputFrame(new_frame)

        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        gray = cv.GaussianBlur(gray, (11, 11), 0)

        if self.prevPrevFrame is None:
            self.prevPrevFrame = gray
            return False

        if self.prevFrame is None:
            self.prevFrame = gray
            return False

        cv.normalize(gray, gray, 0, 255, cv.NORM_MINMAX)

        frameDiff = self.diffImg(self.prevPrevFrame, self.prevFrame, gray)
        ret1, th1 = cv.threshold(frameDiff, 10, 255, cv.THRESH_BINARY)

        cv.dilate(th1, None, iterations=15)
        cv.erode(th1, None, iterations=1)

        delta_count = cv.countNonZero(th1)

        cv.imshow("frame_th1", th1)

        self.prevPrevFrame = self.prevFrame
        self.prevFrame = gray

        ret = delta_count > self.threshold

        if ret:
            self.updateMotionDetectionDts()

        return ret


class MotionDetector(MotionDetectorBase):
    def __init__(self):
        MotionDetectorBase.__init__(self)

        self.threshold = 1500
        self.prevPrevFrame = None

    def diffImg(self, t0, t1, t2):
        if not self.multiFrameDetection:
            return cv.absdiff(t2, t1)

        d1 = cv.absdiff(t2, t1)
        d2 = cv.absdiff(t1, t2)
        return cv.bitwise_and(d1, d2)

    def motionDetected(self, new_frame):
        frame = self.preprocessInputFrame(new_frame)

        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        gray = cv.GaussianBlur(gray, (11, 11), 0)

        if (self.multiFrameDetection) and (self.prevPrevFrame is None):
            self.prevPrevFrame = gray
            return False

        if self.prevFrame is None:
            self.prevFrame = gray
            return False

        cv.normalize(gray, gray, 0, 255, cv.NORM_MINMAX)

        frameDiff = self.diffImg(self.prevPrevFrame, self.prevFrame, gray)
        ret1, th1 = cv.threshold(frameDiff, 10, 255, cv.THRESH_BINARY)

        th1 = cv.dilate(th1, None, iterations=8)
        th1 = cv.erode(th1, None, iterations=4)

        delta_count = cv.countNonZero(th1)

        if self.multiFrameDetection:
            self.prevPrevFrame = self.prevFrame

        self.prevFrame = gray
        if delta_count < self.threshold:
            return False

        if self.multiFrameDetection:
            self.prevPrevFrame = self.prevFrame

        self.prevFrame = gray
        self.updateMotionDetectionDts()
        return True


class MotionDetectorV3Traced(MotionDetectorBase):
    def __init__(self):
        MotionDetectorBase.__init__(self)

        self.threshold = 1500
        self.prevPrevFrame = None

        self.produceContoursFrame = False
        self.contoursFrame = None

        self.productDiffFrame1 = False
        self.diffFrame1 = None

        self.productDiffFrame2 = False
        self.diffFrame2 = None

    def diffImg(self, t0, t1, t2):
        if not self.multiFrameDetection:
            return cv.absdiff(t2, t1)

        d1 = cv.absdiff(t2, t1)
        d2 = cv.absdiff(t1, t2)
        return cv.bitwise_and(d1, d2)

    def motionDetected(self, new_frame):
        frame = self.preprocessInputFrame(new_frame)

        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        gray = cv.GaussianBlur(gray, (11, 11), 0)

        if (self.multiFrameDetection) and (self.prevPrevFrame is None):
            self.prevPrevFrame = gray
            return False

        if self.prevFrame is None:
            self.prevFrame = gray
            return False

        cv.normalize(gray, gray, 0, 255, cv.NORM_MINMAX)

        frameDiff = self.diffImg(self.prevPrevFrame, self.prevFrame, gray)
        ret1, th1 = cv.threshold(frameDiff, 10, 255, cv.THRESH_BINARY)

        if self.productDiffFrame1:
            self.diffFrame1 = th1.copy()

        th1 = cv.dilate(th1, None, iterations=8)
        th1 = cv.erode(th1, None, iterations=4)

        if self.productDiffFrame2:
            self.diffFrame2 = th1.copy()

        delta_count = cv.countNonZero(th1)

        if self.multiFrameDetection:
            self.prevPrevFrame = self.prevFrame

        self.prevFrame = gray
        if delta_count < self.threshold:
            return False

        if self.produceContoursFrame:
            self.contoursFrame = frame.copy()

            im2, contours, hierarchy = cv.findContours(th1, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
            for c in contours:
                cv.drawContours(self.contoursFrame, [c], 0, (0, 0, 255), 2)

            # (x, y, w, h) = cv.boundingRect(c)
            # cv.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        if self.multiFrameDetection:
            self.prevPrevFrame = self.prevFrame

        self.prevFrame = gray

        self.updateMotionDetectionDts()
        return True


class MotionDetectorV4(MotionDetectorBase):
    def __init__(self):
        MotionDetectorBase.__init__(self)

        self.threshold = 10
        self.prevPrevFrame = None

    def diffImg(self, t0, t1, t2):
        d1 = cv.absdiff(t2, t1)
        d2 = cv.absdiff(t1, t0)
        return cv.bitwise_and(d1, d2)

    def motionDetected(self, new_frame):
        frame = self.preprocessInputFrame(new_frame)

        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        gray = cv.GaussianBlur(gray, (11, 11), 0)

        if self.prevPrevFrame is None:
            self.prevPrevFrame = gray
            return False

        if self.prevFrame is None:
            self.prevFrame = gray
            return False

        cv.normalize(gray, gray, 0, 255, cv.NORM_MINMAX)

        frameDiff = self.diffImg(self.prevPrevFrame, self.prevFrame, gray)
        ret1, th1 = cv.threshold(frameDiff, 10, 255, cv.THRESH_BINARY)

        cv.dilate(th1, None, iterations=4)
        cv.erode(th1, None, iterations=2)

        totalArea = 0
        im2, contours, hierarchy = cv.findContours(th1, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        for c in contours:
            totalArea += cv.contourArea(c)
            cv.drawContours(frame, [c], 0, (0, 0, 255), 2)

        if totalArea < self.threshold:
            return False

        cv.imshow("frame_th1", frame)

        self.prevPrevFrame = self.prevFrame
        self.prevFrame = gray
        self.updateMotionDetectionDts()

        return True
