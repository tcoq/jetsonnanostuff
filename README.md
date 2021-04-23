# Jetson Nano stuff

Here you find some small software projects for my Jetson Nano. 
(see https://developer.nvidia.com/embedded/learn/get-started-jetson-nano-devkit#intro)

# Search object

## Introduction

search-object.py classifies Video files (e.g. mp4) by using pre-configured jetson docker image (https://github.com/dusty-nv/jetson-inference) to find objects via pre-trained object detection model SSD-Mobilenet-v2.

## Background

I have got a Reo-Link RLC-422 IP camera with a simple (poor) motion detection feature, which I'd like to improve with AI object detection feature. This should improve camera motion alerting and avoid false positiv alarms. 

First I tried to process the H.264 stream of the IP camera with Jetson Nano in realtime. Doing so, I ran into some problems with CPU utilization. So I decided to stop this development-path of AI based realtime motion detection very early.

So I tried a new batch-approach and installed a FTP Server on Jetson Nano and let REO-Link IP camera store files at the mounted network path from Jetson Nano.

Processing files in batched is very easy, stable and improved the useless alarming feature of my IP camera. The script has got a small delay of a few minutes, but this is really ok for my prpose.

## Setup

For using my script you need this:

1. Jetson Nano
2. Running https://github.com/dusty-nv/jetson-inference docker image
3. Installed FTP server on Jetson Nano
4. Any IP based camera which allows to store video-files on Jetson installed FTP

## How to run

1. Edit the variables "pathRaw" and "pathProcessed" to an accessable path from jetson-inference docker (i.g. the "data" folder is mounted to the underling host)
2. Set up a cronjob (crontab -e) to copy uploaded video-files to the path behind variable "pathRaw"

Example : */1 * * * * find /path/to/ftp -name '*.mp4' -execdir mv {} /myscripts/rawvideo/ \;

3. Move search-object.py to mounted folder from jetson-inference
4. Start jetson-inference
5. Inside jetson-inference docker run and type "python3 search-object.py"

# Hints
I figured out that sometimes jetson docker still not working anymore. (I think there could be a memory leak) Due to the fact of high effort to analyze I fixed the problem with restarting every night in system cron like this way:

@reboot         root    sleep 20 && sh /*yourpath*/objDetStart.sh > /tmp/cronjob.log 2>&1

Startscript "objDetStart.sh" is also now available. Please also got to jetson-inference/docker/run.sh and remove "-it" flag from "sudo docker run..." at the bottom of script, (last command) to allow docker to start during reboot automatically.

Enjoy
