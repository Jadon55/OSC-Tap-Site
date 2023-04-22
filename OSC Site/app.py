# Imports
import time
import numpy as np
import threading
import random
from pythonosc.udp_client import SimpleUDPClient    #pip install python-osc
from flask import Flask, jsonify, render_template, request  #pip install Flask

# OSC
send = False
hasMore = False
    #default values for the lighting board and most common osc commands
target_ip = "10.0.0.196"
target_port = "8000"
in_order = True
start_value = "251"
end_value = "275"
osc_command = "/eos/macro/x/fire"
currentList = []


def createList():
    global currentList
    currentList = []                            # clear list
    count = int(end_value)-int(start_value)+1   # get the number of values that will be in the list
    for i in range(count):                      # loop that adds the values into the list
        currentList.append(i+int(start_value))
    return 0

def getRandom():
    global currentList
    if not currentList:
        createList()
        index = random.randint(0, len(currentList) - 1)
        return str(currentList.pop(index))
    else:
        index = random.randint(0, len(currentList) - 1)
        return str(currentList.pop(index))

def getNext():
    global currentList
    if not currentList:
        createList()
        return str(currentList.pop(0))
    else:
        return str(currentList.pop(0))

def runOSC():
    createList()
    # print(currentList)
    while True:
        if send == True:
            client = SimpleUDPClient(target_ip, target_port)
            if in_order == False:
                client.send_message(osc_command.replace("x", getNext()), 1)
                # print(osc_command.replace("x", getNext()))
            else:
                client.send_message(osc_command.replace("x", getRandom()), 1)
                # print(osc_command.replace("x", getRandom()))
            time.sleep(lastAverage)

t2 = threading.Thread(target=runOSC)

#Flask
app = Flask(__name__)

last_tap_time = None
time_diffs = np.zeros(3)
lastAverage = 1






@app.route('/')
def index():
    global lastAverage
    return render_template('index.html', lastAverage=lastAverage)

@app.route('/getTime', methods=['POST'])
def getTime():
    global lastAverage
    return jsonify({'lastAverage': lastAverage})


@app.route('/tap', methods=['POST'])
def tap():
    global last_tap_time, time_diffs, lastAverage

    current_time = time.time()
    if last_tap_time is not None:
        time_diff = current_time - last_tap_time
        last_tap_time = current_time

        # shift the array to the right and insert the new time difference
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
                # print("Time differences too far apart")
        else:
            print("     Not enough time differences")

    else:
        last_tap_time = current_time

    return jsonify({})

@app.route('/settings')
def settings():
    return render_template('settings.html', target_ip=target_ip, target_port=target_port, in_order=in_order, start_value=start_value, end_value=end_value, osc_command=osc_command)


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

@app.route('/saveOn', methods=['POST'])
def saveOn():
    global send
    send = True
    print("on")
    return jsonify({})

@app.route('/saveOff', methods=['POST'])
def saveOff():
    global send
    send = False
    print("off")
    return jsonify({})


@app.route('/help')
def help():
    return render_template('help.html')


if __name__ == '__main__':
    t2.start()
    app.run(debug=True)
