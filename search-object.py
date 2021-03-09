#!/usr/bin/python3
#

import jetson.inference
import jetson.utils
import logging
import sys
import shutil
from time import sleep
from os import listdir
from os.path import isfile, join
from os import remove

logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', filename='objectDetetion.log', filemode='w', level=logging.INFO)

logging.info("Init network and videocource-------")
objectFound = False

net = jetson.inference.detectNet("ssd-mobilenet-v2", threshold=0.5)
logging.info("Init done -------------------------")

# set path for folders where source/ raw videos could be found and where processed should be moved
pathRaw = "/myscripts/rawvideo/"
pathProcessed = "/myscripts/processedvideos/"

while True:
    dirs = listdir(pathRaw)

    # This would print all the files and directories
    for fil in dirs:
        filename = pathRaw + fil
        logging.info("Processing now file: " + filename)
    
        try:
            frameCnt = 0
            input = jetson.utils.videoSource(filename)
            while True:
                img = input.Capture()
                detections = net.Detect(img)

                # check if there were any detections 
                if (len(detections) > 0):
                    for detection in detections:
                        classid = detection.ClassID
                        confidence = detection.Confidence
                        # ClassID 1 means person, 17 = cat, 18 = dog and belongs to loaded model ssd-mobilenet-v2
                        if (confidence > 0.79): 
                            # now we found something with 79% propability
                            # count times objects where found
                            frameCnt = frameCnt + 1

                            if (frameCnt > 3):
                                # stop analyzing if object was found more than n times to avoid false positives
                                logging.info('Detected classID: ' + str(classid) + ' with confidence: ' + str(confidence) + " in : " + fil)
                                processedFilename = pathProcessed + "cid_" + str(classid) + "_cf_" + str(confidence) + "_" + fil
                                shutil.move(filename, processedFilename)
                                objectFound = True
                                break
                # check if object found or video-stream is at the end or object found
                if (not input.IsStreaming() or objectFound): 
                    # check if file was already moved
                    if (not objectFound): 
                        try:
                            remove(filename) 
                        except:
                            logging.warn("Cannot delete: " + filename + " , unexpected error: " + str(sys.exc_info()[0]))
                    objectFound = False
                    break
        except:
            logging.error("Exception reading file: " + filename + " , unexpected error: " + str(sys.exc_info()[0]))

    # wait 10 seconds for new files
    sleep(10)
logging.info("Shutdown -------")

