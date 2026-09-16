import json
import time
from paho.mqtt import client as mqtt

client = mqtt.Client()

client.connect("mqtt",1883)

while True:

    data = {

        "machine":"CNC-01",

        "temperature":150,

        "vibration":25,

        "current":40,

        "pressure":0,

        "speed":0,

        "timestamp":time.time()

    }

    client.publish("factory/machine1",json.dumps(data))

    print("Fake data envoyée")

    time.sleep(0.3)
