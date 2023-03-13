# Utility class for Raspberry Pi GPIO functions

import time

try:
    import OPi.GPIO as GPIO
    RealRPiGPIOFlag = True
except (ImportError, RuntimeError):
    try:
        import RPi.GPIO as GPIO
        RealRPiGPIOFlag = True
    except (ImportError, RuntimeError):
        import util.FakeRPiGPIO as GPIO
        RealRPiGPIOFlag = False
except:  # need extra exception catch for Travis CI tests
    import util.FakeRPiGPIO as GPIO
    RealRPiGPIOFlag = False
# if RPi.GPIO not available then use FakeRiGPIO from https://github.com/sn4k3/FakeRPi

RHGPIO_S32ID_PIN = 25  # input is tied low on S32_BPill PCB

S32BPillBoardFlag = False

def isRealRPiGPIO():
    return RealRPiGPIOFlag

def isS32BPillBoard():
    return S32BPillBoardFlag

def setS32BPillBoardFlag():
    global S32BPillBoardFlag
    S32BPillBoardFlag = True

def getGPIO():
    return GPIO

# if input tied low then set flag identifying S32_BPill board
if RealRPiGPIOFlag:
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(RHGPIO_S32ID_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        time.sleep(0.05)
        S32BPillBoardFlag = not GPIO.input(RHGPIO_S32ID_PIN)
        GPIO.setup(RHGPIO_S32ID_PIN, GPIO.IN)
    except RuntimeError:
        S32BPillBoardFlag = False
