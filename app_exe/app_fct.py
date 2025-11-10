import socket
import time
import pandas as pd
import csv
from datetime import datetime
def get_day():
    '''returneaza ziua pentru afisarea statistica'''
    dat = time.asctime()
    print((dat.split()[0]),dat)
    return str(dat.split()[2]),dat.split()[1],str(dat.split()[4]),dat
def extract_csv(csv,command,day):
    df = pd.read_csv(csv)
    print(type(day),day)
    keep_csv = df[df[command] == str(day)]
    keep_csv.to_csv("BPM_"+str(day)+".csv", index=False)

    # current_date = datetime.now()
    # current_day = current_date.day
    # print(current_day)

    # df = pd.read_csv(csv)
    #
    # keep_csv = df[df[command] == day and df[month] == month and df[year] == year]
    # keep_csv.to_csv("BPM_"+str(day)+".csv", index=False)

def Extract_Bpm_For_Signal(file,command):
    bpm_value_day=[]
    day,month,year,dat = get_day()

    if command == day:
        day = command
    elif command == month:
        month = command
    else:
        year = command
    with open(file, newline='') as csvfile:
        csv_reader = csv.reader(csvfile, delimiter=',')
        next(csv_reader)

        for row in csv_reader:
            print(row)
            print(f'COMMAND LOOK:{command}')
            if row != []:
                if year in row:
                    if command != year:
                        if month in row:
                            if command != month:
                                if day in row:
                                    bpm_value_day.append(float(row[1]))
                            else:
                                bpm_value_day.append(float(row[1]))
                    else:
                        bpm_value_day.append(float(row[1]))

    print(f'VALS BPM!!:{bpm_value_day}')

    return bpm_value_day