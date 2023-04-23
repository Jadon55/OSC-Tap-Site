# Imports
import time
import numpy as np
import threading
import random
from pythonosc.udp_client import SimpleUDPClient
from flask import Flask, jsonify, render_template, request

#default values for the lighting board and most common osc commands
send = False
target_ip = "10.0.0.196"
target_port = "8000"
in_order = True
start_value = "251"
end_value = "275"
osc_command = "/eos/macro/x/fire"
currentList = []

# makes a list of values (in order) to be used in the osc command, list is called "currentList"
def createList():
    global currentList
    currentList = []                            # clear list
    count = int(end_value)-int(start_value)+1   # get the number of values that will be in the list
    for i in range(count):                      # loop that adds the values into the list
        currentList.append(i+int(start_value))
    return 0

# returns a random element from the "currentList" list, and removes it from the list. If the list is empty, it calles createList()
def getRandom():
    global currentList
    if not currentList: # list is empty
        createList()    # makes list again
        index = random.randint(0, len(currentList) - 1)
        return str(currentList.pop(index))
    else:               # list has at least 1 item
        index = random.randint(0, len(currentList) - 1)
        return str(currentList.pop(index))

# returns the next element from the "currentList" list, and removes it from the list. If the list is empty, it calles createList()
def getNext():
    global currentList
    if not currentList: # list is empty
        createList()    # makes list again
        return str(currentList.pop(0))
    else:               # list has at least 1 item
        return str(currentList.pop(0))

# primary function that runs the OSC loop in a thread
def runOSC():
    createList()    #creaes listt
    while True:
        if send == True:    #only sends commands if the button on the home page says "on"
            client = SimpleUDPClient(target_ip, int(target_port))   # makes a client for the OSC commands to be sent to using the port and ip
            if in_order == False:
                client.send_message(osc_command.replace("x", getNext()), 1)
            else:
                client.send_message(osc_command.replace("x", getRandom()), 1)
            time.sleep(lastAverage) # sleeps for the average time between taps

# creates the thread that will call runOSC() in it
t2 = threading.Thread(target=runOSC)

# Creates Flask
app = Flask(__name__)

last_tap_time = None
time_diffs = np.zeros(3)
lastAverage = 1





# home page
@app.route('/')
def index():
    global lastAverage
    return render_template('index.html', lastAverage=lastAverage)

# function called by index.html that returns the most recent recorded average time between taps, used for setting the flash rate of the button
@app.route('/getTime', methods=['POST'])
def getTime():
    global lastAverage
    return jsonify({'lastAverage': lastAverage})

# function called by index.html when the "tap" button is pressed. Function is responsible for calculating the time between taps
@app.route('/tap', methods=['POST'])
def tap():
    global last_tap_time, time_diffs, lastAverage

    current_time = time.time()
    if last_tap_time is not None:
        time_diff = current_time - last_tap_time
        last_tap_time = current_time

        # shift the array to the right and insert the new time difference, and removes the "oldest" time from the array
        time_diffs[0:2] = time_diffs[1:3]
        time_diffs[2] = time_diff

        # calculate the average of the last three time differences
        filtered_diffs = time_diffs[time_diffs != 0]  # exclude zero values
        if len(filtered_diffs) == 3:
            diff_ratio = np.max(filtered_diffs) / np.min(filtered_diffs)
            if diff_ratio <= 1.2:
                avg_diff = np.mean(filtered_diffs)
                hours, rem = divmod(avg_diff, 3600)
                minutes, seconds = divmod(rem, 60)
                milliseconds = round((avg_diff - int(avg_diff)) * 1000)
                lastAverage = seconds
                print("     Average time difference: "+ str(lastAverage))
            else:
                print("     Last Average: "+ str(lastAverage))
        else:
            print("     Not enough time differences")

    else:
        last_tap_time = current_time

    return jsonify({})

# settings page
@app.route('/settings')
def settings():
    return render_template('settings.html', target_ip=target_ip, target_port=target_port, in_order=in_order, start_value=start_value, end_value=end_value, osc_command=osc_command)

# function called by settings.html to save the values in the form to python
@app.route('/save-settings', methods=['POST'])
def save_settings():
    global target_ip, target_port, in_order, start_value, end_value, osc_command
    target_ip = request.form.get('targetIp')
    target_port = request.form.get('targetPort')
    in_order = request.form.get('inOrder') == 'on'
    start_value = request.form.get('startValue')
    end_value = request.form.get('endValue')
    osc_command = request.form.get('oscCommand')
    createList()
    return 'OK', 200

# funcion called by settings.html to enable the OSC commands to be sent
@app.route('/saveOn', methods=['POST'])
def saveOn():
    global send
    send = True
    print("on")
    return jsonify({})

# funcion called by settings.html to stop the OSC commands from being sent
@app.route('/saveOff', methods=['POST'])
def saveOff():
    global send
    send = False
    print("off")
    return jsonify({})


# Help page
@app.route('/help')
def help():
    return render_template('help.html')



# Main Function
if __name__ == '__main__':
    t2.start()  # start the thread that runs the OSC loop
    app.run(host="0.0.0.0", port=5000, debug=True) # start the flask web app
