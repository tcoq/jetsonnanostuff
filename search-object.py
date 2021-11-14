#!/usr/bin/python3
#

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

logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', filename='/myscripts/objectDetetion.log', filemode='w', level=logging.INFO)

logging.info("Init network and videocource-------")
objectFound = False

net = jetson.inference.detectNet("ssd-mobilenet-v2", threshold=0.5)
logging.info("Init done -------------------------")

# set path for folders where source/ raw videos could be found and where processed should be moved
pathRaw = "/myscripts/rawvideo/"
pathProcessed = "/myscripts/processedvideos/"
pathError = "/myscripts/errorvideos/"

def initDetectorTable():
    con = sqlite3.connect('/myscripts/detector_db.sqlite3')
    cur = con.cursor()

    chargelog_sql = """
    CREATE TABLE IF NOT EXISTS detector (
    timestamp TEXT NOT NULL,
    classid integer NOT NULL,
    confidence REAL NOT NULL,
    videoPath TEXT NOT NULL)"""
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

initDetectorTable()

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
                        confidence = round(detection.Confidence,2)
                        topD = int(detection.Top)
                        leftD = int(detection.Left)
                        rightD = int(detection.Right)
                        widthD = int(detection.Width)

                        # specify areas in video-image to avoid detection (y axis pixel)
                        topNoDetectionZone = 140
                        if (topD < topNoDetectionZone):
                            continue
                        # classids belong to model ssd-mobilenet-v2
                        # 1 = person
                        # 17 = cat
                        # 18 = dog

                        # 49 = knife / occurs on rain
                        # 61 = cake / occurs on wind
                        # this classids produce false positives...
                        if (classid == 49 or classid == 61):
                            continue

                        if (confidence >= 0.78): 
                            # now we found something with n% propability
                            # count times objects where found
                            frameCnt = frameCnt + 1

                            if (frameCnt > 5):
                                # stop analyzing if object was found more than n times to avoid false positives
                                logging.info('Detected classID: ' + str(classid) + ',confidence: ' + str(confidence) + ',coordinates: (top=' + str(topD) + ',left=' + str(leftD) + ',rigth=' + str(rightD) + ',width='  + str(widthD) + ') in imagesize (' + str(img.width) + ', ' + str(img.height) + ') file: ' + fil)
                                processedFilename = pathProcessed + "cid_" + str(classid) + "_cf_" + str(confidence) + "_top_" + str(topD) + "_" + fil
                                shutil.move(filename, processedFilename)
                                
                                con = sqlite3.connect('/myscripts/detector_db.sqlite3')
                                cur = con.cursor()
                                tz = pytz.timezone('Europe/Berlin')
                                timestamp = datetime.now(tz)

                                sql = "INSERT INTO 'detector' (timestamp,classid,confidence,videoPath) VALUES ('" + str(timestamp) + "'," + str(classid) + "," +str(confidence) + ",'" +str(processedFilename) +"')"
                                try:
                                    cur.execute(sql)
                                    con.commit()
                                except:
                                    logging.error(traceback.format_exc()) 
                                cur.close()
                                con.close()
                                
                                objectFound = True
                                break
                        else:
                            # we want consecutive frames
                            frameCnt = 0
                # check if object found or video-stream is at the end or object found
                if (not input.IsStreaming() or objectFound): 
                    # check if file was already moved
                    if (not objectFound): 
                        try:
                            remove(filename) 
                        except:
                            logging.exception("Cannot delete: " + filename + " , unexpected error: ")
                    objectFound = False
                    break
        except:
            logging.exception("Exception reading file: " + filename + " , unexpected error: ")
            shutil.move(filename, pathError + fil)

    # only clean database if new files were generated
    if (len(dirs) > 0):
        # cleanup database if necessary
        cleanupData()
    # wait 10 seconds for new files
    sleep(10)

