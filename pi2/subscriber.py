import json
import time
import paho.mqtt.client as mqtt

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

BROKER = "mqtt"
TOPIC = "factory/machine"

TOKEN = "seDYR7YbPm7V6vmJM6rDZYeMzfP8TCliW-sHBF31Wgz9h4YNqJA8Eof5kDG9VclyJ92YznHfIfoLon34zmpZCg=="
ORG = "PFA"
BUCKET = "factory"

client_db = InfluxDBClient(
    url="http://influxdb:8086",
    token=TOKEN,
    org=ORG
)

write_api = client_db.write_api(write_options=SYNCHRONOUS)

last_timestamp = 0

def on_message(client, userdata, msg):

    global last_timestamp

    payload = json.loads(msg.payload.decode())

    print(payload)

    temperature = payload["temperature"]
    vibration = payload["vibration"]
    current = payload["current"]
    timestamp = payload["timestamp"]

    # -------------------------
    # IDS
    # -------------------------

    alerts = []

    if temperature > 80:
        alerts.append("High Temperature")

    if vibration > 5:
        alerts.append("High Vibration")

    if current > 30:
        alerts.append("High Current")

    if timestamp <= last_timestamp:
        alerts.append("Replay Attack")

    last_timestamp = timestamp

    if alerts:
        print("\n🚨 ALERT")
        for a in alerts:
            print(" -", a)

    point = (
        Point("machine")
        .tag("machine", "Machine_01")
        .field("temperature", temperature)
        .field("vibration", vibration)
        .field("current", current)
        .time(time.time_ns(), WritePrecision.NS)
    )

    write_api.write(bucket=BUCKET, org=ORG, record=point)

mqtt_client = mqtt.Client()

mqtt_client.on_message = on_message

mqtt_client.connect(BROKER,1883)

mqtt_client.subscribe(TOPIC)

print("Subscriber + IDS running...")

mqtt_client.loop_forever()
