import speech_recognition as sr
from speech_recognition.recognizers import google, whisper
import threading
from max30102 import MAX30102
import hrcalc
import threading
import time
import numpy as np
import sounddevice
from IPython.display import Audio, display
from scipy.io import wavfile
from  ADXL345_fall_detect import ADXL345
from gps import *
import time
import subprocess
import sys
import server_app
import subprocess
import pyttsx3


def run_pigpiod():
  """ This function attempts to execute 'sudo pigpiod' as a subprocess."""
  try:
      # execute 'sudo pigpiod' command
      result = subprocess.run(['sudo', 'pigpiod'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  except subprocess.CalledProcessError as e:
      print(f"Command failed with error code {e.returncode}")
      print(e.output.decode())

# global variables for sensor data and control flags
bpm = 20
spo2 = 0
lat = 0
lon = 0
flag_pulse = 0

class GPS:
    """ Class to handle GPS module data acquisition and transmission to client"""
    def __init__(self):
        """ Initializes the GPS module and starts data transmission """
        self.gpsd = gps(mode=WATCH_ENABLE|WATCH_NEWSTYLE)

    def  send_location(self):
        """ Extracts latitude and longitude coordinates; transmits data to the client via TCP connection.
        Includes text-to-speech feedback."""
        global lat,lon,server,engine,voices
        text = "Location activated"
        engine.setProperty("rate", 170)
        engine.say(text)
        engine.runAndWait()
        while True:
            print('Active')
            report = self.gpsd.next() # get the next GPS
            if report['class'] == 'TPV':            # extract lat and lon values from the report list
              lat = str(getattr(report,'lat',0.0))
              lon = str(getattr(report,'lon',0.0))
              server.send_to_client(lat,lon,'gps')  # send data to client
            time.sleep(3)

class SenzorPuls:
    """ Class to initialize and acquire values from the GY-MAX30102 sensor."""
    def run_sensor(self):
        """ Runs the MAX30102 sensor to continuously acquire infrared (IR) and red light (RED) PPG data.
        It calculates Heart Rate (BPM) and Blood Oxygen Saturation (SpO2), applies filtering,
        handles invalid data, and sends valid readings to a client.
        """
        global bpm,spo2,server,engine,voices
        text = "Measuring pulse"
        engine.setProperty("rate", 170)
        engine.say(text)
        engine.runAndWait()
        sensor = MAX30102()    # pulse sensor class
        ir_data = []           # list to store IR LED values
        red_data = []          # list to store RED LED values
        bpms = []              # list to store BPM values
        f1 = open("valori_irLed.txt", "a") # open file for storing IR LED values for analysis
        f2 = open("valori_redLed.txt", "a") # open file for storing Red LED values for analysis

        while True:
            num_bytes = sensor.get_data_present()    # get number of available samples from FIFO
            if num_bytes > 0:
                while num_bytes > 0:
                    red, ir = sensor.read_fifo() # read one sample
                    num_bytes -= 1
                    ir_data.append(ir)
                    red_data.append(red)
                    f1.write('\n'+str(ir)+',') # write IR data to file
                    f2.write('\n' + str(red) + ',') # write Red data to file
                    bpm_mean = []
                    while len(ir_data) == 100: # collect 100 samples
                        red, ir = sensor.read_fifo()
                        ir_data.append(ir)
                        red_data.append(red)

                        bpm, valid_bpm, spo2, valid_spo2 = hrcalc.calc_hr_and_spo2(ir_data, red_data) # calculate HR and SpO2
                        if valid_bpm == False or spo2<0 : # BPM is invalid or SpO2 is negative
                            print('Invalid data detected, resetting buffers.')
                            ir_data = []
                            red_data =[]

                        if valid_bpm: # BPM valid
                            bpms.append(bpm)
                            while len(bpms) > 4: # moving average of last 4 BPM values
                                bpms.pop(0)
                            bpm = np.mean(bpms) # calculate mean BPM
                            bpm_mean.append(bpm)

                            # check for BPM,SpO2 values
                            if (np.mean(ir_data) < 50000 and np.mean(red_data) < 50000) or spo2<0 or bpm>97 or bpm<60 :
                                print("Finger not detected")
                                bpm = 20 # reset BPM to default
                                spo2 = 99 # reset SpO2 to default
                                ir_data =[] # clear buffers
                                red_data =[]
                            print("BPM: {0}, SpO2: {1}".format(bpm, spo2))

                            # check for critical BPM or SpO2 values to trigger location alert
                            if bpm < 60 or bpm > 100 or spo2<90:
                                print("SENT LOCATION")
                                flag_sent_location = 1
                                if bpm != 20 or spo2 > 0:
                                    flag_sent_location = 0
                                if flag_sent_location == 1:
                                    time.sleep(1)

                            # BPM is within a reasonable range and SpO2 is valid, send to client
                            if bpm > 60 and spo2 > 0:
                                    server.send_to_client(round(bpm,2),round(spo2,2),'bpm') #send to client interface from MITAppInventor bpm value

                            if len(ir_data) > 0:
                                ir_data = ir_data[0:96] #keep first 96 values and add last 4 values lately
                                red_data = red_data[0:96]

                        time.sleep(0.1)

    def start_sensor(self):
        """ create the sensor data acquisition thread """
        global bpm,spo2
        self._thread = threading.Thread(target=self.run_sensor)
        self._thread.stopped = False # flag to control thread execution
        self._thread.start()

    def stop_sensor(self, timeout=2.0):
        """ create the  sensor data acquisition stop thread """
        self._thread.stopped = True
        self.bpm = 0
        self._thread.join(timeout)

acc_val =[] # list to store acceleration values for fall detection
state_fall = 0 # flag to indicate if a fall has been detected


def detect_fall():
    """Function to continuously detect falls using the ADXL345 sensor.
  It reads accelerometer data, processes it for fall detection, and updates a global state variable."""
    global state_fall,acc_val
    adxl = ADXL345(sample_rate=100) # Initialize ADXL345 with 100 Hz sample rate
    while True:
        try:
            state_fall = adxl.read_one(acc_val) # read data and update fall state
            time.sleep(0.02) # delay between readings
        except Exception as e:
                print('Error in fall detection:',e)
                continue

text = '' # stores the last recognized speech text
last_text ='' # stores the text from the previous recognition cycle

def audio_part():
    """ This function listens for voice commands, processes them, and triggers actions
    such as starting pulse measurement or sending GPS location. """
    global bpm,spo2,senzor_gps,state_fall,last_text,text,flag_pulse,server,thread_gps, engine,voices
    flag_sent_location = 0
    r = sr.Recognizer() # initialize Speech Recognizer
    microphone = sr.Microphone() # use default microphone
    heart_rate = SenzorPuls() # initialize heart rate sensor object

    with microphone as source:
        print("Listening...")
        r.adjust_for_ambient_noise(source) # adjust for ambient noise for better recognition
        m = 0
        flag_speak = 0
        while True:
            try:
                if state_fall == True: # if a fall is detected
                    print('FALL!!!SENT LOCATION',lat,lon)
                    m+=1
                    if m ==1: # only announce and send location once per fall event
                        text = "Fall detected. Alert sent."
                        engine.setProperty("rate", 170)
                        engine.say(text)
                        engine.runAndWait()
                       # flag_sent_location = 1
                        thread_gps.start() # start sending GPS location
                if flag_speak == 0:
                    text = "Voice commands activated"
                    engine.setProperty("rate", 170)
                    engine.say(text)
                    engine.runAndWait()
                flag_speak +=1

                audio_data = r.listen(source,timeout = 1,phrase_time_limit=7) # listen for audio input with a timeout and phrase time limit
                text = r.recognize_google(audio_data,language ="en-US") # recognize speech using Google Speech Recognition
                if text == '': # if no new speech is recognized, retain the last one
                    text = last_text
                    print('Same command as before.')
                if 'measure' in text  or 'pulse' in text or 'heart rate' in text: # if keywords 'measure' or 'pulse' are in command
                    last_text = text
                    print("Start pulse measurement")
                    heart_rate.start_sensor() # start the heart rate sensor thread
                    flag_pulse = 1 # set flag for pulse measurement
#                     with lock:
#                         print('SENT',bpm)
#                         server.send_to_client(bpm)
#
                if 'help' in text or 'gps' in text: # if keywords 'help' or 'gps' are in command
                    print('HERE: Activating GPS thread.')
                    thread_gps.start() # start the GPS sending thread
                    flag_sent_location =0 # reset location sent flag

            except sr.UnknownValueError:
                print("Repeat") # speech not understandable
                continue

            except sr.WaitTimeoutError:
                print("Repeat TIMEOUT") # no speech detected within timeout
                continue

            except sr.RequestError as e:
                print("Could not request results;{0}".format(e))
                continue
            except Exception as e:
                print('Error in audio part:',e)
            time.sleep(1)


print('START')
server = None
senzor_gps = GPS() # initialize GPS object
thread_gps = threading.Thread(target = senzor_gps.send_location) # create a thread for sending GPS location
run_pigpiod() # start the pigpiod daemon

engine = pyttsx3.init() # initialize text-to-speech engine
voces = engine.getProperty('voices')
# engine.setProperty('voice', 'romanian') # Set voice to Romanian

def ConnectAll():
    """Connect all components (server, audio, accelerometer) and start their threads."""
    global server,engine,voices
    try:
        text = "Start"
        engine.setProperty("rate", 180)
        engine.say(text)
        engine.runAndWait()
        server = ServerAplicatie.Server() # initialize server object
        server.init_server() # start server and wait for client connection
        text = "Connected"
        engine.setProperty("rate", 180)
        engine.say(text)
        engine.runAndWait()

        thread_audio = threading.Thread(target = audio_part) # create thread for audio processing
        thread_acc = threading.Thread(target = detect_fall) # create thread for fall detection
        thread_audio.start()
        thread_acc.start()

    except Exception as e:
        print('Error in ConnectAll:',e)
        text = "Error, reboot"
        engine.setProperty("rate", 180)
        engine.say(text)
        engine.runAndWait()
ConnectAll()
