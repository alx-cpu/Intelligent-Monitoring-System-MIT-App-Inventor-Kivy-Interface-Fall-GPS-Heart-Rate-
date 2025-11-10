from kivymd.uix.button import MDFlatButton
import socket
from kivy.uix.scrollview import ScrollView
from kivy.properties import StringProperty
import wave,sys
from kivy.clock import Clock
from kivy_garden.graph import Graph, MeshLinePlot, MeshStemPlot, LinePlot, SmoothLinePlot, ContourPlot
from kivy.uix.boxlayout import BoxLayout
import csv
import neurokit2 as nk
from kivymd.app import MDApp
from kivy_garden.graph import Graph, MeshLinePlot
import threading
from kivy.config import Config
import app_fct
from kivy.core.window import Window
from kivy.uix.image import Image
from kivy.properties import DictProperty
from kivy.uix.widget import Widget
from kivy.uix.gridlayout import GridLayout
from kivy.core.audio import SoundLoader
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
import numpy as np
from kivy.lang import Builder
from kivy_garden.mapview import MapView, MapMarker
from kivy.lang import Builder
from kivy.uix.widget import Widget
from kivymd.uix.widget import MDWidget
from kivymd.app import MDApp
from kivymd.uix.button import MDFlatButton

Config.set('graphics', 'resizable', True) # allow window resizing

lat = 0 # Latitude for GPS
lon = 0 # Longitude for GPS
spo2 = 0
command = '' # command for statistical data plotting (e.g., day, month, year)
age = 0 # User's age
val_self = 0
data = 20
prev_data = {}
all_bpm_value = {}
rows = []

bpm_values = [20]
spo2_values=[0]

def Data_From_Server():
    """Client function for receiving and processing data from the server.
    It connects to a specified host and port, receives BPM, SpO2, and GPS data,
    updates global variables, logs BPM/SpO2 data to a CSV file, and stores BPM values for statistics.
   """
    global all_bpm_value,spo2_values,lat,lon
    fields = ['Day', 'BPM_value','SPO2', 'Month','Year'] # CSV header fields
    HOST = 'raspberrypi.local' # Server hostname
    PORT = 1234 # Server port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: # create a TCP/IP socket
        s.connect((HOST, PORT))  # connect to the server
        while True:
            data_raw = s.recv(1024)                            # receive data from the server
            data_decoded = data_raw.decode("utf-8")                    # decode received data from UTF-8
            data_parts = data_decoded.strip("()").split(", ")

            bpm = float(data_parts[0]) # extract BPM value
            spo2_val = float(data_parts[1]) # extract SpO2 value
            string_type = data_parts[2].strip("'") # extract data type ('gps', 'bpm')
            print('RECV:',data_parts)

            if string_type =='gps':
                lat = bpm # latitude is first value
                lon = spo2_val # longitude is second value
            print('Current GPS:', lat,lon)

            if bpm is not None and string_type == 'bpm':
                bpm_values.append((round(float(bpm), 2))) # add BPM to list
                spo2_values.append((round(float(spo2_val), 2))) # add SpO2 to list
                print(f"Received BPM: {round(float(bpm), 2)}")
                day, month,year,complete_date = app_fct.get_day() # get current date info

                if day not in all_bpm_value:                  # store BPM values for centralization
                    all_bpm_value[day] = []
                all_bpm_value[day].append(round(float(bpm), 2))

                # append new row to a list for CSV
                rows.append([day, (round(float(bpm), 2)),spo2_val, month,year])
                with open('GFG_NEW.csv', 'w') as f: # open CSV file for writing (overwrites existing file)
                    write = csv.writer(f)
                    write.writerow(fields) # write header row
                    write.writerows(rows) # write all data rows

class Line_hor(Widget):
    """Used for graphical representation of horizontal lines."""
    pass

class Line_vert(Widget):
    """Used for graphical representation of vertical lines."""
    pass

class Circle(Widget):
    """Used for graphical representation of circles."""
    pass

class LineApp(MDApp):
    """ KivyMD application for displaying graphical elements (lines, circles).
     Builds the root widget for the LineApp, which is a GridLayout containing Line_vert, Line_hor, and Circle widgets.
     :return: The root GridLayout widget with graphical elements. """
    def build(self):
        """Adds graphical elements to the interface."""
        root = GridLayout(cols=3, padding=50, spacing=100)
        root.add_widget(Line_vert())
        root.add_widget(Line_hor())
        root.add_widget(Circle())
        return root

class Screen_2(Screen):
  """screen for displaying BPM data (second screen in the application)."""
  pass

class Screen_GPS(Screen):
  """screen for displaying GPS map with location markers."""
  pass

class Screen_3(Screen):
    pass

class Screen_4(Screen):
    """ Screen for displaying all data statistics and providing options to download data reports."""
    pass


class ECGApp(MDApp):
    """ KivyMD application for displaying ECG data.Builds the ECGMonitor widget, which visually represents an ECG signal.
    :return: An instance of the ECGMonitor widget.
    """
    def build(self):
        return ECGMonitor

class ECGMonitor(BoxLayout):
    """ Kivy widget for displaying an ECG-like signal based on BPM."""
    def __init__(self, **kwargs):
        """Constructs the ECG graph. Initializes the ECGMonitor, sets up graph and plot widgets,
        and schedules periodic updates for the ECG signal based on BPM data.
        """
        self.clock_variable = None
        super(ECGMonitor, self).__init__(**kwargs)
        self.flag_update = 1
        self.bpm_values = bpm_values # reference to global BPM values list
        self.spo2_values = spo2_values # reference to global SpO2 values list
        self.bpm = 20 # current BPM value (initialized)
        self.spo2 = spo2_values[-1] # current SpO2 value (last in list)
        self.all_bpm = all_bpm_value # reference to all BPM values dictionary
        self.age = '0' # user's age
        self.flag_button = 0 # flag for button state

        self.normal_bpm_values = { # Valid BPM intervals based on age groups
            '0': [],
            '1': ['100', '180'],
            '2': ['98', '140'],
            '5': ['80', '120'],
            '7': ['75', '118'],
            '100': ['60', '100'],
        }

        # initialize the graph widget
        self.graph = Graph(xlabel='Time (s)', ylabel='ECG Signal', x_ticks_minor=2,
                               x_ticks_major=0.8, y_ticks_major=0.8, y_grid_label=False,
                               x_grid_label=False, padding=2, x_grid=False, y_grid=False,
                               xmin=0, xmax=9, ymin=-5, ymax=7, draw_border=False,
                               tick_color='234 / 255, 241 / 255, 247 / 255, 1.0')

        # initialize the line plot for ECG signal
        self.plot = LinePlot(line_width=1.5, color=[65 / 255, 102 / 255, 132 / 255, 1])
        self.graph.add_plot(self.plot)
        self.add_widget(self.graph)
        self.ecg_signal = np.array([]) # array to store ECG signal data
        self.time_offset = 0
        # schedule the UpdateECG function to run periodically
        self.clock_variable = Clock.schedule_interval(self.UpdateECG, 3)

    def UpdateECG(self, dt):
        """Updates the ECG graph based on new BPM values.
        :param dt: The time elapsed since the last update (delta time).
        """
        self.bpm = self.bpm_values[-1] # get the most recent BPM value
        self.spo2 = self.spo2_values[-1] # get the most recent SpO2 value

        print(f'HEART RATE:{self.bpm}\nSPO2;{self.spo2}')
        # simulate an ECG signal based on the current BPM
        ecg = nk.ecg_simulate(duration=4, sampling_rate=5, method="daubechies",
                              heart_rate=self.bpm)

        self.ecg_signal = np.concatenate((self.ecg_signal, ecg)) # append new simulated ECG to the existing signal

        # update plot points with new ECG data and corresponding time values
        self.plot.points = list(zip(np.linspace(0, len(self.ecg_signal) / 10, len(self.ecg_signal)),
                                    self.ecg_signal))

        # adjust graph x-axis limits to scroll the plot
        self.graph.xmax += 1
        self.graph.xmin += 1
        self.graph.ymax = 10
        self.graph.size_hint_y = 0.5
        self.time_offset += 10

        self1 = val_self
        if self1 != 0:
            Main.UpdateLabel(self1) # update labels in the main app

class Plot_all(BoxLayout):
    """ Widget for plotting all recorded BPM values based on a command."""
    def __init__(self,**kwargs):
        """ Initializes the Plot_all widget, setting up the graph for statistical plotting and
        scheduling periodic updates to display BPM data based on a selected command.
        :param kwargs: Keyword arguments passed to the BoxLayout constructor. """
        global command
        super(Plot_all, self).__init__(**kwargs)

        # initialize the graph for statistics plotting
        self.graph_sts = Graph(xlabel='Time', ylabel='BPM', x_ticks_minor=2,
                               x_ticks_major=0.8,y_ticks_minor = 1, y_ticks_major=1.2,
                               y_grid_label=True,
                               x_grid_label=False, padding=5, x_grid=False, y_grid=True,
                               xmin=0, xmax=20, ymin=0, ymax=15, draw_border=False,
                               border_color='65/255, 102/255, 132/255, 1',tick_color=(0.78, 0.85, 0.91),
                               label_options={'color': (0.78, 0.85, 0.91),
                                               'bold': True}
                               )
        # initialize the line plot for the statistical graph
        self.plot_graph = MeshLinePlot(color=[65 / 255, 102 / 255, 132 / 255, 1])
        self.graph_sts.add_plot(self.plot_graph)
        self.graph_sts.size_hint = (1, 1)
        self.add_widget(self.graph_sts)
        self.clock_variable = Clock.schedule_interval(self.update, 4) # Schedule graph update every 4 seconds

    def update(self,dt):
        """
        Updates the graph by plotting the selected command's data.
        :param dt: Delta time for the update.
        """
        global command
        print(f'COMMAND:{command}')
        if command != '': # if a command is set (day, month, or year)
            self.plot_graph.points = [] # clear existing plot points
            # extract BPM data from CSV based on the command
            self.signal1 = app_fct.Extract_Bpm_For_Signal('GFG_NEW.csv', str(command))
            # adjust x-axis max based on the number of data points
            self.graph_sts.xmax = len(self.signal1)
            # update plot points (scaling y-values by /10 for display)
            self.plot_graph.points = [(x, self.signal1[x]/10) for x in range(len(self.signal1))]
            print(self.plot_graph.points)

class Main(MDApp):
    """ Main KivyMD application class for building the user interface."""
    data = DictProperty() # define a dictionary Kivy property
    def __init__(self, **kwargs):
        """ Initializes the Main application, sets up initial state variables and defines normal BPM ranges based on age groups.
        :param kwargs: Keyword arguments passed to the MDApp constructor."""
        global lat,lon
        super(Main, self).__init__(**kwargs)
        self.day,self.month,self.year,date = app_fct.get_day() # get current date information
        self.flag_update = 1
        self.bpm_values = bpm_values # reference to global BPM values list
        self.bpm = bpm_values[-1] # current BPM (last in list)
        self.spo2_values = spo2_values # reference to global SpO2 values list
        self.spo2 = spo2_values[-1] # current SpO2 (last in list)
        self.all_bpm = all_bpm_value # reference to all BPM values dictionary
        self.age = '0' # user's age
        self.flag_button = 0 # flag for button state

        self.normal_bpm_values = { # Normal BPM ranges by age group
            '0': [],
            '1': ['100', '180'],
            '2': ['98', '140'],
            '5': ['80', '120'],
            '7': ['75', '118'],
            '100': ['60', '100'],
        }

    def back(self, root):
        """Function for the back button to return to the main screen.
        :param root: The root widget (ScreenManager).
       """
        root.current = "main_screen"

    def take_age(self):
        """Retrieves the age from the main screen.
        :return: The entered age.
       """
        self.age = self.root.ids.age.text
        if str(self.root.ids.age.text) == '':
            self.reload() # reload main screen if age is empty
            self.root.current = 'main_screen'
            self.root.ids.age.hint_text = 'Please insert first your age...'
        return self.age

    def reload(self):
        """ Returns to the main screen if the age field is not filled.
       """
        if self.flag_button == 1:
            self.age = '0'
            self.root.current = 'main_screen'

    def action(self):
        """Function for the button to connect to the server."""
        global val_self
        self.flag_button = 1
        val_self = self # store reference to self for updating from other threads

        # initialize threads for server data reception and location sending.
        ThreadClient = threading.Thread(target=Data_From_Server)
        ThreadLocation = threading.Thread(target=self.SendLocation)

        ThreadClient.start()  # start client thread
        ThreadLocation.start() # start location thread

    def alert(self,root):
        """Activates the display of real-time location upon pressing the button.
        :param root: ID of the screen manager.
       """
        self.gps()   # display map

    def SendLocation(self):
        """Displays the location on the map received from the server on request.
        The first coordinates might be (0,0), so it waits for valid coordinates.
       """
        global lat, lon
        self.i = 0
        while self.i<2:
            if lat !=0:
                self.root.current = 'main_screen'
                self.root.ids.alert_button.opacity = '1' # Show 'Fallen detect' alert message
                self.i+=1

    def gps(self,*args):
        """Returns real-time location in case of an emergency."""
        global lat,lon
        self.root.current = "gps_screen" # Access GPS screen
        self.root.ids.mapview.lat = lat     # Set map latitude
        self.root.ids.mapview.lon = lon # Set map longitude
        self.root.ids.marker.lat = lat # Set marker latitude
        self.root.ids.marker.lon = lon # Set marker longitude

    def sts(self, *args):
        """Function to display labels for data downloads."""
        self.root.current = "all_screen" # Navigate to 'all_screen'
        print(f'ROOT:{self.root.current}')
        # update labels with current date for download options
        self.root.ids.txt_download_day.text = 'BPM'+'/'+self.day+'/'+self.month+'/'+ self.year
        self.root.ids.txt_download_year.text = 'BPM' + '/'+ self.year
        self.root.ids.txt_download_month.text = 'BPM' + '/' + self.month +'/' + self.year

    def callback(self, *args):
        """Function to display screen 2."""
        self.root.current = "second_screen" # Navigate to 'second_screen'
        LineApp().build() # Build LineApp (might be a redundant call if it's part of the main app)
        self.UpdateLabel() # Update labels with BPM/SpO2 data

    def InterpretBPM(self):
        """Function to verify normal BPM parameters based on age."""
        prev_item = self.normal_bpm_values['0']
        self.bpm = self.bpm_values[-1]
        self.spo2 = self.spo2_values[-1] # select current SpO2 value

        if self.age != '' and self.bpm != 20:
            for item in self.normal_bpm_values:
                if int(self.age) < int(item) and int(self.age) >= int(prev_item):
                    # set text for normal BPM ranges
                    self.root.ids.txt2.text = self.normal_bpm_values[item][0]
                    self.root.ids.txt3.text = self.normal_bpm_values[item][1]
                    # set text for current BPM and SpO2 values
                    self.root.ids.txt_bpm.text = str(int(self.bpm))
                    self.root.ids.txt_spo2.text = str(int(self.spo2)) + '%'
                    # if BPM or SpO2 is outside the normal range, change text color to red
                    if (self.bpm >= int(self.normal_bpm_values[item][1]) or self.bpm <= int(
                            self.normal_bpm_values[item][0])) or self.spo2 < 90:
                        self.root.ids.txt_bpm.color = (1, 0, 0) # set BPM text color to red
                        self.root.ids.txt_spo2.color = (1, 0, 0) # set SpO2 text color to red
                prev_item = item # update previous item for the next iteration

    def UpdateLabel(self):
        """Function to retrieve age and update UI labels"""
        if self.flag_update == 1:
                ECGApp().build() # build ECGApp
                self.age = self.take_age() # get user's age
                print('Age:', self.age)
                for idx in bpm_values:
                    self.root.ids.txt1.text = self.age # display age on UI
                    self.InterpretBPM() # interpret BPM based on age and update display

    def DownloadDay(self):
        """Downloads BPM values in CSV format for the current day."""
        app_fct.extract_csv('GFG_NEW.csv', 'Day', self.day)

    def DownloadMonth(self):
        """Downloads BPM values in CSV format for the current month."""
        app_fct.extract_csv('GFG_NEW.csv', 'Month',self.month)

    def DownloadYear(self):
        """Downloads BPM values in CSV format for the current year."""
        app_fct.extract_csv('GFG_NEW.csv', 'Year', self.year)

    def day_st(self):
        """Retrieves command to display graph of current day's BPM values."""
        global command
        command = self.day

    def month_st(self):
        """Retrieves command to display graph of current month's BPM values."""
        global command
        print('month selected')
        command =self.month

    def year_st(self):
        """Retrieves command to display graph of current year's BPM values."""
        global command
        command = self.year
        print(command)


    def build(self):
        """Function to construct the interface.
        :return: The constructed interface.
       """
        self.dim = 1
        self.img = Image(source='resources/app_background.jpg') # load background image

        screen = Screen() # create a base screen
        screen.add_widget(self.img) # add image to the screen as background

        width = int(340) # set window width
        height = int(600) # set window height
        Window.size = (width, height)
        Window.clearcolor = (1, 0, 0, 1)
        self.theme_cls.primary_palette = "BlueGray"

        # define the UI layout and widgets.
        self.kv = Builder.load_string(
            """
<MDFloatingActionButtonSpeedDial>: # Main screen Floating Action Button Speed Dial widget
    id: fab
ScreenManager:
    id: screen_manager
    Screen: # Main screen definition
        id: sc
        name: 'main_screen'
        canvas.before:
            Rectangle:
                pos: self.pos
                size: self.size
                source: 'resources/app_background.jpg' # Background image for main screen
        MDRectangleFlatIconButton: # Alert message button for fall detection
            id: alert_button
            icon: 'alert'
            text: "Fallen detect.Click here to see location in real time"
            theme_text_color: "Custom"
            pos_hint: {'center_x':0.5, 'center_y': 0.97}
            text_color: "black"
            md_bg_color: "red"
            line_color: "red"
            opacity : '0' # Initially hidden
            on_press:
                app.alert(root) # Call alert function on press
        MDRectangleFlatIconButton: # Button to connect to the server
            icon: "signal-distance-variant"
            text: 'CONNECT TO SERVER'
            style: "Outlined"
            theme_text_color: "Custom"
            text_color: "blue"
            pos_hint: {'center_x': 0.45, 'center_y': 0.25}
            on_press:
                app.action() # Call action function on press
            adaptive_height: True
            adaptive_size: True
            adaptive_width: True
        MDFloatingActionButtonSpeedDial: # Floating action button with multiple options
            data : {'BPM': ['heart-outline',"on_press",  app.callback], # BPM option, icon, and callback
                    "All": ["chart-line","on_press", app.sts], # All data option, icon, and callback
                    'GPS':["map-marker","on_press",app.gps]} # GPS option, icon, and callback
            id: fab
            callback:  app.callback # Default callback if no option is chosen
            style: "tonal"
            hint_animation: True
            root_button_anim: True
        MDTextField: # Text field for age input
            id: age
            size_hint_x: None
            width: "240dp"
            pos_hint: {"center_x": .5, "center_y": 0.35}
            hint_text:'Enter your age...'
            text_color: "blue"
            on_text: app.take_age() # Call take_age function on text input
    Screen_2: # Second screen for displaying BPM/SpO2 and ECG graph
        name: 'second_screen'
        id: screen2
        canvas.before:
            Color:
                rgba: (234 / 255, 241 / 255, 247 / 255, 1.0) # Background color
            Rectangle:
                pos: self.pos
                size: self.size
        canvas: # Drawing elements for design (circles and lines)
            Color:
                rgba: 0.79, 0.88, 0.96, 1
            Line:
                width: 70
                circle:
                    (self.center_x, self.center_y+200, 70, 0, 360)
            Color:
                rgba: 0.831, 0.925, 1.0, 1.0
            Line:
                width: 20
                circle:
                    (self.center_x, self.center_y+200, 90, 0, 360)
            Color:
                rgba: 0.831, 0.925, 1.0, 1.0
            Line:
                width: 8
                circle:
                    (self.center_x, self.center_y+200, 110, 0, 360)
            Color:
                rgba: 0.89, 0.95, 1, 1
            Line:
                width: 15
                circle:
                    (self.center_x, self.center_y+200, 130, 0, 360)
        MDLabel: # Label for BPM value
            id:txt_bpm
            text: "--"
            color: 65/255, 102/255, 132/255, 1
            font_style: 'H5'
            pos_hint: {'center_x': 0.95, 'center_y': 0.76}
        MDLabel: # Label for SpO2 value
            id:txt_spo2
            text: "--"
            color: 65/255, 102/255, 132/255, 1
            font_style: 'Subtitle2'
            pos_hint: {'center_x': 1, 'center_y': 0.72}
        MDLabel:
            id:t_bpm
            color:  65/255, 102/255, 132/255, 1
            text: "BPM"
            font_style: 'Subtitle1'
            pos_hint: {'center_x': 1.05, 'center_y': 0.77}
        MDLabel:
            id:txt1
            text: "-"
            font_style: 'H6'
            pos_hint: {'center_x': 0.62, 'center_y': 0.50}
        MDLabel:
            id:txt2
            text: "-"
            font_style: 'H6'
            pos_hint: {'center_x': 0.93, 'center_y': 0.50}
        MDLabel:
            id:t_bpm
            color:  65/255, 102/255, 132/255, 1
            text: "BPM"
            font_style: 'Subtitle2'
            pos_hint: {'center_x': 1, 'center_y': 0.49}
        MDLabel:
            id:t1_bpm
            color:  65/255, 102/255, 132/255, 1
            text: "BPM"
            font_style: 'Subtitle2'
            pos_hint: {'center_x': 1.40, 'center_y': 0.49}
        MDLabel:
            id:txt3
            text: "-"
            font_style: 'H6'
            pos_hint: {'center_x': 1.3, 'center_y': 0.50}
        MDRaisedButton: # Back button to main screen
            text: 'back'
            pos_hint: {'center_x': 0.1, 'center_y': 0.1}
            on_press:
                app.back(root)
        BoxLayout: # Container for the BPM ECG graph
            id: graph_container
            orientation: 'vertical'
            pos_hint: {'center_x': 0.5, 'center_y': 0.5}
            size_hint_y: None
            height: 720
            ECGMonitor: # ECG Monitor widget
                id: plot
                pos_hint: {'center_x': 0.5, 'center_y': 1.2}
        MDLabel: # Label for age display
            text: "Age"
            id: txt
            pos_hint: {'center_x': 0.6, 'center_y': 0.55}
            Line_vert: # Vertical line for design
                canvas.before:
                    Color:
                        rgba: 65/255, 102/255, 132/255, 1
                    Line:
                        points: self.parent.width*0.09, self.parent.height*0.537,self.parent.width *0.2,self.parent.height * 0.537
        MDLabel: # Label for minimum BPM
            text: "Minimum"
            id: txt_min
            pos_hint: {'center_x': 0.85, 'center_y': 0.55}
            Line_vert: # Vertical line for design
                canvas.before:
                    Color:
                        rgba: 65/255, 102/255, 132/255, 1
                    Line:
                        points: self.parent.width*0.33, self.parent.height*0.537,self.parent.width *0.58,self.parent.height * 0.537
            Line_hor: # Horizontal line for design
                canvas.before:
                    Color:
                        rgba: 65/255, 102/255, 132/255, 1
                    Line:
                        points: self.parent.width*0.64, self.parent.height*0.55,self.parent.width *0.64,self.parent.height * 0.48
        MDLabel:
            text: "Maximum"
            id: txt_max
            pos_hint: {'center_x': 1.2, 'center_y': 0.55}
            Line_vert: # Vertical line for design
                canvas.before:
                    Color:
                        rgba: 65/255, 102/255, 132/255, 1
                    Line:
                        points: self.parent.width*0.68, self.parent.height*0.537,self.parent.width *0.96,self.parent.height * 0.537
            Line_hor: # Horizontal line for design
                canvas.before:
                    Color:
                        rgba: 65/255, 102/255, 132/255, 1
                    Line:
                        points: self.parent.width*0.25, self.parent.height*0.55,self.parent.width *0.25,self.parent.height * 0.4
    Screen_GPS: # Screen for displaying the map with GPS location
        name:'gps_screen'
        MapView: # Map view element
            id: mapview
            lat: 47 # Default latitude
            lon: 27 # Default longitude
            zoom: 9 # Default zoom level
            MapMarker: # Map marker for specific location
                id: marker
                lat: 47
                lon: 27
        MDRaisedButton: # Back button
            text: 'back'
            pos_hint: {'center_x': 0.1, 'center_y': 0.1}
            on_press:
                app.back(root)
    Screen_4: # Screen for displaying data statistics and download options
        name: 'all_screen'
        id: screen4
        canvas.before:
            Color:
                rgba: (234 / 255, 241 / 255, 247 / 255, 1.0) # Background color
            Rectangle:
                pos: self.pos
                size: self.size
        MDRectangleFlatIconButton: # Button to download daily BPM report
            icon : 'download'
            id: txt_download_day
            text: "BPM/3/5/2024" # Example text, will be updated dynamically
            md_bg_color: (250/255, 252/255, 254/255, 0.8)
            size_hint: 4,.02
            pos_hint: {'center_x': 0.49, 'center_y': 0.4}
            background_color: (250/255, 252/255, 254/255, 0.8)
            on_press: app.DownloadDay() # Call DownloadDay function on press
        MDRectangleFlatIconButton: # Button to download monthly BPM report
            icon : 'download'
            id : txt_download_month
            text: "BPM/3/2024"
            size_hint: 4,.02
            pos_hint: {'center_x': 0.48, 'center_y': 0.34}
            on_press: app.DownloadMonth() # Call DownloadMonth function on press
        MDRectangleFlatIconButton: # Button to download yearly BPM report
            md_bg_color: (250/255, 252/255, 254/255, 0.8)
            icon : 'download'
            id :  txt_download_year
            size_hint: 4,.02
            text: "BPM/2024"
            pos_hint: {'center_x': 0.47, 'center_y': 0.28}
            on_press: app.DownloadYear() # Call DownloadYear function on press
        MDRaisedButton: # Back button
            text: 'back'
            pos_hint: {'center_x': 0.1, 'center_y': 0.1}
            on_press:
                app.back(root)
        MDFlatButton: # Button to show daily BPM graph
            text: 'day'
            pos_hint: {'center_x': 0.2, 'center_y': 0.50}
            on_press:
                app.day_st() # Set command for daily statistics
        MDFlatButton: # Button to show monthly BPM graph
            text: 'month'
            pos_hint: {'center_x': 0.5, 'center_y': 0.50}
            on_press:
                app.month_st() # Set command for monthly statistics
        MDFlatButton: # Button to show yearly BPM graph
            text: 'year'
            pos_hint: {'center_x': 0.8, 'center_y': 0.50}
            on_press:
                app.year_st() # Set command for yearly statistics
        BoxLayout: # Container for the statistical report graph
            id: graph_sts
            orientation: 'vertical'
            pos_hint: {'center_x': 0.5, 'center_y': 0.76}
            size_hint_y: None
            height: 300
            width : 180
            canvas:
                Color:
                    rgba: 250/255, 252/255, 254/255, 0.8
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [(30, 30), (30, 30), (20, 20), (20, 20)]
            Plot_all: # Plot_all widget to display the graph
                id: plot_graph
                pos_hint: {'center_x': 0.5, 'center_y': 0.76}
"""
        )
        return self.kv

Main().run()
