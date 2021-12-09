#!/usr/bin/python3
#

from posix import times_result
import jetson.inference
import jetson.utils
import sqlite3
import logging
import sys
import shutil
import pytz
from datetime import datetime
from time import sleep
from os import listdir
from os.path import isfile, join
from os import remove
import traceback
from collections import defaultdict

logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', filename='/myscripts/objectDetetion.log', filemode='w', level=logging.INFO)

logging.info("Init network and videocource-------")
objectFound = False

net = jetson.inference.detectNet("ssd-mobilenet-v2", threshold=0.5)
logging.info("Init done -------------------------")

# set path for folders where source/ raw videos could be found and where processed should be moved
pathRaw = "/myscripts/rawvideo/"
pathProcessed = "/myscripts/processedvideos/"
pathError = "/myscripts/errorvideos/"
pathNoObj = "/myscripts/noobjvideos/"

#
# Place a sepia filter on given image
#
def sepia(image):
    width = image.width     
    height = image.height

    for py in range(height):
        for px in range(width):

            pixel = img[py,px]
            r = pixel[0]
            g = pixel[1]
            b = pixel[2]
            
            tr = int(0.393 * r + 0.769 * g + 0.189 * b)
            tg = int(0.349 * r + 0.686 * g + 0.168 * b)
            tb = int(0.272 * r + 0.534 * g + 0.131 * b)

            if tr > 255:
                tr = 255

            if tg > 255:
                tg = 255

            if tb > 255:
                tb = 255

            img[py,px] = (tr,tg,tb)
    return image

#
# Check if image is grayscale
#
def isGrayscale(img):
    if (img.channels < 3):
        return True

    width = img.width     
    height = img.height

    stopAfter = height / 2

    for py in range(height):
        # stop after 1/2 of height pixel noting was found to avoid to much processing
        if (py > stopAfter):
            return True
        for px in range(width):
            pixel = img[py,px]
            if pixel[0] != pixel[1] != pixel[2]: 
                return False
    return True

#
# Init database if not exist
#
def initDetectorTable():
    con = sqlite3.connect('/myscripts/detector_db.sqlite3')
    cur = con.cursor()

    chargelog_sql = """
    CREATE TABLE IF NOT EXISTS detector (
    timestamp TEXT NOT NULL,
    classid integer NOT NULL,
    confidence REAL NOT NULL,
    filename TEXT NOT NULL)"""
    try:
        cur.execute(chargelog_sql)
        con.commit()
    except:
        logging.error(traceback.format_exc()) 
    cur.close()
    con.close()


#
#	Delete data older 336 h / 14d
#
def cleanupData():
    logging.debug("Try connecting sqllite...")
    con = sqlite3.connect('/myscripts/detector_db.sqlite3')
    try:
        cur = con.cursor()
        cur.execute("delete from detector where timestamp < datetime('now','-336 hour','localtime')")
        con.commit()
        cur.execute("vacuum")
        con.commit()
    except:
        logging.error(traceback.format_exc()) 
    cur.close()
    con.close() 

#
# Move a given file to errorpath
#
def moveImageToErrorFolderAndLog(img, filename):
    global pathError, pathRaw
    rawPathToFile = pathRaw + filename
    try:
        shutil.move(rawPathToFile, pathError + filename)
        if (img != None):
            logging.error('Image data: ' + str(img.format) + ' channels: ' + str(img.channels) + ' file: ' + filename)
    except:
        logging.error(traceback.format_exc()) 
#
#
#
def logObjectFoundToDBAndMoveFile(filename, classid, confidence):
    global pathProcessed, pathRaw
    rawPathToFile = pathRaw + filename
    
    nameOfFile = ""
    night = ""
    
    if nightMode:
        night = "_night"
    
    newFilename = "cid_" + str(classid) + '_' + str(confidence) + '_' + night + "_" + filename
    processedPathToFile = pathProcessed + newFilename
    shutil.move(rawPathToFile, processedPathToFile)
    
    con = sqlite3.connect('/myscripts/detector_db.sqlite3')
    cur = con.cursor()
    tz = pytz.timezone('Europe/Berlin')
    timestamp = datetime.now(tz)

    sql = "INSERT INTO 'detector' (timestamp,classid,confidence,filename) VALUES ('" + str(timestamp) + "'," + str(classid) + "," + str(confidence) + ",'" +str(newFilename) +"')"
    try:
        cur.execute(sql)
        con.commit()
    except:
        logging.error(traceback.format_exc()) 
    cur.close()
    con.close()

initDetectorTable()

while True:
    img = None
    dirs = listdir(pathRaw)
    
    # This would print all the files and directories
    for fil in dirs:
        
        onePerFile = False
        
        rawPathToFile = pathRaw + fil
        logging.info("Processing now file: " + rawPathToFile)
        
        try:
            input = None
            errorCount = 0
            while True:
                try:
                    # retry 2 times to open file
                    if (errorCount > 2):
                        logging.error("Could not open file: " + rawPathToFile)
                        break
                    input = jetson.utils.videoSource(rawPathToFile)
                    break
                except Exception: 
                    # IO problems can occur in some cases if file e.g. is not ready.... wait a while until IO is ready
                    errorCount += 1
                    sleep(3)
                    continue

            if (input == None):
                moveImageToErrorFolderAndLog(None,fil)
                continue

            frameNumber = 0        
            nightMode = False
            detectionsDict = {}
            confidenceDict = defaultdict(list)
            consecutiveFrameDict = {}

            consecutiveClass = None
            consecutiveDetections = 0
            countOfDetections = -1
            freqentClass = -1

            while True:
                img = input.Capture()
                frameNumber += 1

                if (frameNumber < 2):
                    if (isGrayscale(img)):
                        nightMode = True

                frameThreshold = 5
                if (nightMode):
                    frameThreshold = 2

                detections = net.Detect(img)

                noDetectionInFrame = True 
                # check if there were any detections 
                if (len(detections) > 0):
                    noDetectionInFrame = False
                    for detection in detections:

                        #logging.info(str(detection.ClassID) + " " + str(round(detection.Confidence,2)) + " t:" + str(int(detection.Top)) + " l:" + str(int(detection.Left)) + " r:" + str(int(detection.Right)) + " w:" + str(int(detection.Width)))
                        classid = detection.ClassID
                        confidence = round(detection.Confidence,2)
                        topD = int(detection.Top) # h of box
                        leftD = int(detection.Left) # x coordinate
                        rightD = int(detection.Right) # y coordinate
                        widthD = int(detection.Width) # width of box

                        # specify areas in video-image to avoid detection (y axis pixel)
                        topNoDetectionZone = 200
                        if (rightD < topNoDetectionZone):
                            continue
                        # classids belong to model ssd-mobilenet-v2
                        # 1 person
                        # 2 bicycle
                        # 3 car
                        # 4 motorcycle
                        # 5 airplane
                        # 6 bus
                        # 7 train
                        # 8 truck
                        # 9 boat
                        # 10 traffic light
                        # 11 fire hydrant
                        # 13 stop sign
                        # 14 parking meter
                        # 15 bench
                        # 16 bird
                        # 17 cat
                        # 18 dog
                        # 19 horse
                        # 49 knife 
                        # 61 cake 
                        # this classids produce false positives...
                        if (classid == 15 or classid == 49 or classid == 61):
                            continue
                        
                        # we want to be more sensitive on persons
                        confidenceThreshold = 0.60

                        if (classid == 1 ):
                            confidenceThreshold = 0.65
                        else:
                            confidenceThreshold = 0.72

                        if (nightMode):
                            confidenceThreshold = confidenceThreshold - 0.09

                        if (confidence >= confidenceThreshold): 
                            # now we found something with n% propability
                            # save this detection in dict
                            if classid in detectionsDict:
                                value = detectionsDict[classid]
                                value += 1
                                detectionsDict[classid] = value
                            else:
                                detectionsDict[classid] = 1
                            # put confidence to a nested list in a dict to calc later the average value
                            # (we avoid to also check here consecutive confidence to avoid complexity)
                            confidenceDict[classid].append(confidence)

                    # put detections in consecutiveFrame dict, but not none consecutive
                    tmpDict = {}
                    for key in detectionsDict:
                        if (key in consecutiveFrameDict):
                            value = consecutiveFrameDict[key]
                            value += 1
                            tmpDict[key] = value
                        else:
                            tmpDict[key] = detectionsDict[key]
                    consecutiveFrameDict = tmpDict
                    #logging.info("keys in detectiondict: " + str(detectionsDict.keys()) + " cfd: " + str(consecutiveFrameDict))

                    # check if it is empty
                    if (bool(consecutiveFrameDict) == True):
                        # sort dict to get the highest value of a class at the first position...
                        consecutiveFrameDict_sorted = sorted(consecutiveFrameDict.items(), key=lambda x: x[1], reverse=True)
                        countOfDetections = list(dict(consecutiveFrameDict_sorted).values())[0]
                        freqentClass = next(iter(dict(consecutiveFrameDict_sorted)))

                    if (int(countOfDetections) > frameThreshold):
                        # calc the average confidence
                        sum = 0
                        count = 0
                        for confidence in confidenceDict[freqentClass]: 
                            sum += confidence 
                            count += 1
                        avgConfidence = round(sum / count,2)

                        # stop analyzing if object was found more than n times to avoid false positives
                        logging.info('Detected classID: ' + str(freqentClass) + ' avgConfidence: ' + str(avgConfidence) +' # of consecutive detections: ' + str(countOfDetections)  + ' # of frames: ' + str(frameNumber) + ', isNight= ' + str(nightMode) + ' file: ' + fil)
                        logObjectFoundToDBAndMoveFile(fil,freqentClass,avgConfidence)
                        objectFound = True
            
                if (noDetectionInFrame):
                    # found frame with no detections, consecutiveFrameDict
                    consecutiveFrameDict = {}

                # check if object found or video-stream is at the end or object found
                if (not input.IsStreaming() or objectFound): 
                    # check if file was already moved
                    if (not objectFound): 
                        try:
                            shutil.move(rawPathToFile, pathNoObj + fil)
                            logging.info('No obj found in image: ' + str(img.format) + ' classid: ' + str(freqentClass) + ' # of consecutive detections: ' + str(countOfDetections)  + ' # of frames: ' + str(frameNumber) + ' channels: ' + str(img.channels) + ' isGray:' + str(nightMode) +  ' file: '  + fil)
                        except:
                            logging.exception("Cannot move: " + rawPathToFile + " , unexpected error: ")
                    objectFound = False
                    break
        except:
            logging.exception("Exception reading file: " + rawPathToFile + " , unexpected error: ")
            moveImageToErrorFolderAndLog(img,fil)

    # only clean database if new files were generated
    if (len(dirs) > 0):
        # cleanup database if necessary
        cleanupData()
    # wait 5 seconds for new files
    sleep(5)
