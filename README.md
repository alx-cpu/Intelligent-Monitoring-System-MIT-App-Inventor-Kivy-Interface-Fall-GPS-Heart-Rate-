# Intelligent Monitoring System – MIT App Inventor / Kivy Interface
This project implements an intelligent monitoring system for remote health supervision, featuring fall detection, pulse measurement, and GPS tracking using a Raspberry Pi.


***Note**: The original kivy interface works only on desktop and is not compatible with mobile devices. A MIT App Inventor version of the application has been developed as an alternative, enabling real-time monitoring and assistance on smartphones.*


## Features
- **Pulse Monitoring**: Acquires data from a pulse sensor to track the user’s heart rate in real time.
- **Fall Detection**: Uses an accelerometer to detect falls and send alerts.
- **GPS Tracking**: Collects location data for remote monitoring and assistance.
- **Portable System** : Runs on a Raspberry Pi 3B using Python, with concurrent processing via threads.
- **Voice Command Support**: Allows basic control of the system through voice commands.
- **Mobile Application Interface**: Includes a MIT App Inventor mobile app to connect and interact with the Raspberry Pi device.
- **Desktop Application Interface**: Includes a Kivy app to connect and interact with the Raspberry Pi device.

## Required Components
- Raspberry Pi 3B 

- Pulse Sensor – GY-MAX 30102 

- Accelerometer – ADXL345

- GPS Module – NEO 6M  

- Microphone 

## Connections
- NEO 6M connections:
<img width="252" height="170" alt="image" src="https://github.com/user-attachments/assets/23387d9f-f7bf-401b-8ad8-6999e3530e07" />


- ADXL345 connections:
<img width="277" height="235" alt="image" src="https://github.com/user-attachments/assets/a121d8aa-9c65-4f08-bcb8-e51b1bb61df4" />

- GY-MAX 30102  connections:
<img width="277" height="235" alt="image" src="https://github.com/user-attachments/assets/9ced80dc-8da7-40da-a885-7513cec8678b" />


## Installation
1. Clone the repository:
```bash
git clone git@github.com:alx-cpu/Intelligent-Monitoring-System-MIT-App-Inventor-Kivy-Interface-Fall-GPS-Heart-Rate-.git
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```
3.Install BPMApp.aia on your phone

## Usage

1. Run the server application from:

```bash
raspberrypi_app_part.py
```
 
2. In the same time open MIT App Inventor app from your device

3. To start measuring the heart rate, say “measure heart rate” and wait for the current value to be displayed in the mobile app interface. 
4. If the heart rate is abnormal, an alert will be triggered and a risk message will appear in the app. 
5. If a fall is detected, the app will automatically open a map with the location enabled and trigger a "Fall detected" alert.

## KivyApp desktop Interface
<img width="762" height="366" alt="image" src="https://github.com/user-attachments/assets/b91a3739-b819-4298-bd18-c203c66427a5" />

## MIT App Inventor mobile app interface
<img width="463" height="433" alt="image" src="https://github.com/user-attachments/assets/f112cc6d-6ff1-4e93-a79f-2818d25519dd" />

## Dependencies
- Python == 3.9.12
- Note: The hrcalc.py and max30102.pymax30102.py modules are existing libraries and were not developed by the author
