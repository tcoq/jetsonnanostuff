# Jetson Nano stuff

Here you find some small software projects for my Jetson Nano. 
(see https://developer.nvidia.com/embedded/learn/get-started-jetson-nano-devkit#intro)

# Search object

## Introduction

search-object.py classifies Video files (e.g. mp4) by using pre-configured https://github.com/dusty-nv/jetson-inference docker image to find objects via pre-trained object detection model SSD-Mobilenet-v2.

## Background

I have got a Reo-Link RLC-422 IP camera with a simple motion detection feature, which I would like to improve with AI object detection features to improve alerting and avoid false positiv alarms. So I bought a Jetson Nano and first tried to process the realtime- H.264 stream of the camera. Doing so I ran into some problems with  CPU utilization and H.264 codec synchronization. So I decided to stop this the path of realtime processing of AI based motion detection very early.
So I tried a new approach to install a FTP Server on Jetson Nano and let REO-Link IP camera store files at the mounted network path from Jetson Nano to run a batch-process on this stored files, to detect objects. 

This batch processing hast got a small delay of a few minutes, which is fine for me.

## Setup

For using my script you need this:

1. Jetson Nano
2. Running https://github.com/dusty-nv/jetson-inference docker image
3. Installed FTP server on Jetson Nano
4. Any IP based camera which allows to store files videos on Jetson installed FTP

## How to run

1. Edit the variables "pathRaw" and "pathProcessed" to a accessable path from jetson-inference docker (i.g. the "data" folder is mountet to the underling host)
2. Set up a cronjob (crontab -e) to copy uploaded video-files into the path behind variable "pathRaw"

Example : */1 * * * * find /path/to/ftp -name '*.mp4' -execdir mv {} /myscripts/rawvideo/ \;

3. Move search-object.py to mounted folder from jetson-inference
4. Start jetson-inference
5. Inside jetson-inference docker run "python3 search-object.py"

Enjoy
