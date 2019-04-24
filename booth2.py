#!/usr/bin/python3

import os
import PIL.Image
import pygame
from pygame.locals import *
import json
import picamera
import time
import RPi.GPIO as GPIO
import subprocess
import cups

imageFolderName = "Photos"

# get path of this file
dir_path = os.path.dirname(os.path.realpath(__file__))

templatePath = os.path.join(dir_path, imageFolderName, "Template", "template.png")
instaTemplatePath = os.path.join(dir_path, imageFolderName, "Template", "insta.jpg")
logoPath = os.path.join(dir_path, imageFolderName, "Template", "logo-shower.png")
idlePromptPath = os.path.join(dir_path, "images", "idle_prompt.png")

configPath = os.path.join(dir_path, "booth_cfg.json")


PRINT_ENABLED = False
INSTA_ENABLED = False


BUTTON_PIN = 25

PRINT_WIDTH = 1100
PRINT_HEIGHT = 720
PRINT_SUBSIZE = 550, 360

# drewnote: this doesn't make sense
INSTA_WIDTH = 500
INSTA_HEIGHT = 500
INSTA_SUBSIZE = 1000, 654
# should read these from a config file
INSTA_USERNAME = ""
INSTA_PASSWORD = ""
INSTA_CAPTION = ""

print_base_image = PIL.Image.open(templatePath)

if INSTA_ENABLED:
    # get username/password from config file
    with open(configPath, 'r') as f:
        cfg = json.load(f)
        INSTA_USERNAME = cfg["username"]
        INSTA_PASSWORD = cfg["password"]
        INSTA_CAPTION = cfg["caption"]
    
    instaImage = PIL.Image.open(instaTemplatePath)
    
# load the logo
logoImage = PIL.Image.open(logoPath)

# resize logo image now
logoImage = logoImage.resize(PRINT_SUBSIZE)

# setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# init pygame
pygame.init()
# hide mouse cursor
pygame.mouse.set_visible(False)
# get info about display
displayInfo = pygame.display.Info()
# init full screen
screen = pygame.display.set_mode((displayInfo.current_w, displayInfo.current_h), pygame.FULLSCREEN)
# create background object
background = pygame.Surface(screen.get_size())
background = background.convert()

# screen size
screenWidth = displayInfo.current_w
screenHeight = displayInfo.current_h

# init camera
camera = picamera.PiCamera()
camera.resolution = (screenWidth, screenHeight)
camera.rotation = 0
camera.hflip = True
camera.vflip = False
camera.brightness = 50
camera.preview_alpha = 120 # [0 ... 255] with 255 being opaque
camera.preview_fullscreen = True
camera.image_effect = "none"

# photos taken since boot
photosTaken = 0

# photos printed since paper count was reset
photosPrintedSinceReload = 0

# printer can print 16 pictures without a reload
printerCapacity = 16

# print this many pictures per session
copiesPerSession = 2

def displayText(txt, fontSize=100):
    font = pygame.font.Font(None, fontSize)
    text = font.render(txt, 1, (227, 157, 200))
    textPos = text.get_rect()
    textPos.centerx = background.get_rect().centerx
    textPos.centery = background.get_rect().centery
    background.fill(pygame.Color("white"))
    background.blit(text, textPos)
    
    screen.blit(background, (0, 0))
    pygame.display.flip()
    
# check if path exists
# if not, create it
def ensureFolder(path):
    if not os.path.isdir(path):
        os.makedirs(path)
    
def initFilesystem():
    #global imagefolder
    #global Message
 
    #Message = 'Checking filesystem...'
    #UpdateDisplay()
    #Message = ''

    #check image folder existing, create if not exists
    #if not os.path.isdir(imagefolder):    
    #    os.makedirs(imagefolder)    
            
    #imagefolder2 = os.path.join(imagefolder, 'images')
    #if not os.path.isdir(imagefolder2):
    #    os.makedirs(imagefolder2)
        
    displayText("Checking filesystem...")
    ensureFolder(os.path.join(dir_path, imageFolderName))
    ensureFolder(os.path.join(dir_path, imageFolderName, "Template"))
    ensureFolder(os.path.join(dir_path, "images"))

def showImage(path, delay=-1):
    # clear screen
    screen.fill(pygame.Color("white"))
    img = pygame.image.load(path)
    img = img.convert()
    
    # drewnote: holdover from the original script. do we need it?
    #set_dimensions(img.get_width(), img.get_height())
    x = (displayInfo.current_w / 2) - (img.get_width() / 2)
    y = (displayInfo.current_h / 2) - (img.get_height() / 2)
    
    screen.blit(img, (x, y))
    pygame.display.flip()
    
    if delay > -1:
        time.sleep(delay)
        # clear screen?

# capture photo with 3/2/1 countdown, return filename
def capturePhoto():

    global photosTaken
    
    background.fill(pygame.Color("black"))
    screen.blit(background, (0, 0))
    pygame.display.flip()
    camera.start_preview()
    
    
    # countdown: 3... 2... 1... Pose!
    for i in range(3, -1, -1):
        if i == 0:
            displayText("Pose!", 255)
        else:
            displayText(str(i), 255)
        time.sleep(1)
        
    ts = time.time()
    filename = os.path.join(dir_path, imageFolderName, "{}_{}.jpg".format(photosTaken, ts))
    camera.capture(filename, resize=(PRINT_WIDTH, PRINT_HEIGHT))
    camera.stop_preview()
    
    photosTaken += 1
    
    return filename
    

def takePictures():
    
    photoNames = []
    photos = []
    
    # Load the background template
    bgimage = PIL.Image.open(templatePath)
    
    # take 3 pictures
    for picNum in range(3):
        displayText("{}/3".format(picNum))
        photoNames.append(capturePhoto())
        showImage(photoNames[picNum])
        time.sleep(5)

    displayText("Please wait...")

    # this may take a hot second, so do this after we take all our pictures so people can relax
    for picNum in range(3):
        photos.append(PIL.Image.open(photoNames[picNum]))
        photos[picNum] = photos[picNum].resize(PRINT_SUBSIZE)
    
    # resize for insta first since those are actually larger
    if INSTA_ENABLED:
        for picNum in range(3):
            photos[picNum] = photos[picNum].resize(INSTA_SUBSIZE)
            instaImage.paste(photos[picNum], (0, 140))
            instaImage.save("instaTemp{}.jpg".format(picNum))
            
        # launch instagram uploader
        subprocess.Popen("{} {} {} {} {} &".format(os.path.join(dir_path, "rapid_post.sh"), INSTA_USERNAME, INSTA_PASSWORD, "instaTemp", "\"" + INSTA_CAPTION + "\""), close_fds=True, shell=True)
    
        
    bgimage.paste(logoImage, (55, 30))
    bgimage.paste(photos[0], (625, 30))
    bgimage.paste(photos[1], (625, 410))
    bgimage.paste(photos[2], (55, 410))
    
    ts = time.time()
    finalImageName = os.path.join(dir_path, imageFolderName, "final_{}_{}.jpg".format(photosTaken, ts))
    
    # save photo
    # tired: save to micro sd
    # wired: save to usb
    bgimage.save(finalImageName)
    
    bgimage.save("tempPrint.jpg")
    
    # show to users
    #showPicture("tempPrint.jpg", 3)
    showImage("tempPrint.jpg", 3)

def printPhoto():
    global PRINT_ENABLED
    global photosPrintedSinceReload
    if PRINT_ENABLED:
        if os.path.isfile("tempPrint.jpg"):
            # open connection to cups
            conn = cups.Connection()
            
            # get printers
            printers = conn.getPrinters()
            
            # get first printer, probably correct
            printerName = list(printers)[0]
            
            displayText("Printing...")
            
            printQueueLength = len(conn.getJobs())
            
            # if more than one job is in the print queue,
            # the prints obviously aren't working correctly
            if printQueueLength > 1:
                displayText("Printing error 042 - attendant needed")
                time.sleep(2)
            else:
                conn.printFile(printerName, "tempPrint.jpg", "Photobooth", {"copies": "{}".format(copiesPerSession)})
                photosPrintedSinceReload += copiesPerSession
                
            displayText("")
            
    else:
        displayText("Printing disabled")
        time.sleep(2)
        displayText("")

def main():
    # make sure folders exist
    initFilesystem()
    
    # show idle prompt
    showImage(idlePromptPath)
    
    exitRequest = False
    
    # input loop
    while True:
        if exitRequest:
            break
    
        # gpio pressed
        if not GPIO.input(BUTTON_PIN):
            takePictures()
            printPhoto()
            
            # show idle prompt
            showImage(idlePromptPath)
        else:
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                
                    # escape button pressed
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        exitRequest = True
                        break
                    
                    # down arrow pressed
                    if event.key == pygame.K_DOWN:
                        takePictures()
                        
                        # show idle prompt
                        showImage(idlePromptPath)
                        break
                        
        time.sleep(0.2)
    
    # tidy up GPIO
    GPIO.cleanup()
    
    
main()

