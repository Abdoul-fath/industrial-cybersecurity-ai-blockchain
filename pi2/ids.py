import json
import joblib
import pandas as pd
import hashlib
import requests
import sys

from paho.mqtt import client as mqtt
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from cryptography.hazmat.primitives import serialization


# Affichage immédiat des logs dans Docker
try:
    sys.stdout.reconfigure(
        line_buffering=True,
        write_through=True
    )
except Exception:
    pass


# Configuration MQTT
BROKER = "mqtt"
PORT = 1883
TOPIC = "factory/machine1"
MQTT_QOS = 1


# Configuration Blockchain
BLOCKCHAIN_URL = "http://blockchain:5000"
BLOCKCHAIN_NODE_ID = "raspberrypi1"


# Configuration InfluxDB
INFLUX_URL = "http://influxdb:8086"

TOKEN = (
    "hm6MfBhqG5l1m8RQAhbKxuOlHjylxeUDUGIVqhsNazPVDaQP0em2tKO"
    "XxE993vX_EXv9S4ws-jYyhbt0dzY-1g=="
)

ORG = "PFA"
BUCKET = "factory"


# Fichiers utilisés
PUBLIC_KEY_FILE = "/workspace/public_key.pem"
MODEL_FILE = "/workspace/isolation_forest.pkl"


# Connexion à InfluxDB
print("Connexion InfluxDB...", flush=True)

db = InfluxDBClient(
    url=INFLUX_URL,
    token=TOKEN,
    org=ORG
)

write_api = db.write_api(
    write_options=SYNCHRONOUS
)

print("Connexion InfluxDB configurée.", flush=True)


# Chargement de la clé publique Ed25519
with open(PUBLIC_KEY_FILE, "rb") as f:
    public_key = serialization.load_pem_public_key(
        f.read()
    )

print("Clé publique Ed25519 chargée.", flush=True)


# Chargement du modèle Isolation Forest
print("Chargement du modèle Isolation Forest...", flush=True)

model = joblib.load(MODEL_FILE)

print("Modèle Isolation Forest chargé.", flush=True)


# Dernière séquence reçue pour chaque machine
last_sequences = {}


def verifier_signature(data, signature_hex):
    try:
        message = json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":")
        ).encode("utf-8")

        signature = bytes.fromhex(signature_hex)

        public_key.verify(
            signature,
            message
        )

        return True

    except Exception as e:
        print("Signature invalide :", e, flush=True)
        return False


def generer_alerte(
    signature_valide,
    replay,
    anomalie_ia,
    data
):
    if not signature_valide:
        return {
            "type_evt": "cyberattaque",
            "criticite": 3,
            "criticite_label": "URGENCE",
            "action": "Isoler le noeud et vérifier la clé publique"
        }

    if replay:
        return {
            "type_evt": "attaque_rejeu",
            "criticite": 3,
            "criticite_label": "URGENCE",
            "action": "Rejeter le message et vérifier la source"
        }

    if anomalie_ia:
        return {
            "type_evt": "anomalie_physique",
            "criticite": 2,
            "criticite_label": "CRITIQUE",
            "action": "Planifier une inspection de la machine"
        }

    return None


def enregistrer_alerte(
    data,
    alerte,
    sequence,
    signature_valide,
    replay
):
    try:
        alert_point = (
            Point("alerts")
            .tag("machine", str(data["machine"]))
            .tag("type", alerte["type_evt"])
            .tag(
                "criticite_label",
                alerte["criticite_label"]
            )
            .field(
                "criticite",
                int(alerte["criticite"])
            )
            .field(
                "sequence",
                int(sequence)
            )
            .field(
                "temperature",
                float(data["temperature"])
            )
            .field(
                "vibration",
                float(data["vibration"])
            )
            .field(
                "current",
                float(data["current"])
            )
            .field(
                "signature_valid",
                int(signature_valide)
            )
            .field(
                "replay",
                int(replay)
            )
        )

        write_api.write(
            bucket=BUCKET,
            org=ORG,
            record=alert_point
        )

        print(
            "Alerte enregistrée dans InfluxDB.",
            flush=True
        )

    except Exception as e:
        print(
            "Erreur InfluxDB alerte :",
            e,
            flush=True
        )


def enregistrer_machine(
    data,
    sequence,
    anomalie_ia
):
    try:
        point = (
            Point("machine")
            .tag(
                "machine",
                str(data["machine"])
            )
            .field(
                "vibration",
                float(data["vibration"])
            )
            .field(
                "acoustic",
                float(data["acoustic"])
            )
            .field(
                "temperature",
                float(data["temperature"])
            )
            .field(
                "current",
                float(data["current"])
            )
            .field(
                "IMF_1",
                float(data["IMF_1"])
            )
            .field(
                "IMF_2",
                float(data["IMF_2"])
            )
            .field(
                "IMF_3",
                float(data["IMF_3"])
            )
            .field(
                "prediction",
                int(-1 if anomalie_ia else 1)
            )
            .field(
                "sequence",
                int(sequence)
            )
            .field(
                "signature_valid",
                1
            )
            .field(
                "replay",
                0
            )
        )

        write_api.write(
            bucket=BUCKET,
            org=ORG,
            record=point
        )

        print(
            "Donnée machine enregistrée dans InfluxDB.",
            flush=True
        )

    except Exception as e:
        print(
            "Erreur InfluxDB machine :",
            e,
            flush=True
        )


def enregistrer_blockchain(
    data,
    signature_valide,
    replay,
    anomalie_ia
):
    try:
        data_json = json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":")
        ).encode("utf-8")

        data_hash = hashlib.sha256(
            data_json
        ).hexdigest()

        if not signature_valide:
            event_type = "SIGNATURE_INVALIDE"
            criticite = 3
            verification = "SIGNATURE_INVALIDE"

        elif replay:
            event_type = "ATTAQUE_REJEU"
            criticite = 3
            verification = "REPLAY_DETECTE"

        elif anomalie_ia:
            event_type = "ANOMALIE_IA"
            criticite = 2
            verification = "SIGNATURE_VALIDE"

        else:
            event_type = "DATA"
            criticite = 0
            verification = "SIGNATURE_VALIDE"

        payload = {
            "data_hash": data_hash,
            "node_id": BLOCKCHAIN_NODE_ID,
            "event_type": event_type,
            "criticity": criticite,
            "verification": verification,
            "sequence": int(data["sequence"]),
            "machine": str(data["machine"])
        }

        response = requests.post(
            BLOCKCHAIN_URL + "/add_block",
            json=payload,
            timeout=3
        )

        response.raise_for_status()

        result = response.json()

        if result.get("success"):
            block = result["block"]

            print("Blockchain : bloc enregistré", flush=True)
            print(
                "Index       :",
                block["block_index"],
                flush=True
            )
            print(
                "Machine     :",
                data["machine"],
                flush=True
            )
            print(
                "Sequence    :",
                data["sequence"],
                flush=True
            )
            print(
                "Événement   :",
                event_type,
                flush=True
            )
            print(
                "Hash donnée :",
                data_hash,
                flush=True
            )
            print(
                "Hash bloc   :",
                block["block_hash"],
                flush=True
            )

        else:
            print(
                "Blockchain : échec de l'enregistrement",
                flush=True
            )

    except requests.exceptions.RequestException as e:
        print(
            "Blockchain inaccessible :",
            e,
            flush=True
        )

    except Exception as e:
        print(
            "Erreur Blockchain :",
            e,
            flush=True
        )


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("MQTT connecté.", flush=True)
        print("Broker :", BROKER, flush=True)
        print("Topic  :", TOPIC, flush=True)

        result, mid = client.subscribe(
            TOPIC,
            qos=MQTT_QOS
        )

        if result == mqtt.MQTT_ERR_SUCCESS:
            print(
                "Abonnement au topic :",
                TOPIC,
                "QoS =",
                MQTT_QOS,
                flush=True
            )
        else:
            print(
                "Erreur abonnement MQTT :",
                mqtt.error_string(result),
                flush=True
            )

    else:
        print(
            "Erreur MQTT :",
            rc,
            flush=True
        )


def on_disconnect(client, userdata, rc):
    if rc != 0:
        print(
            "MQTT déconnecté. Tentative de reconnexion...",
            flush=True
        )
    else:
        print(
            "MQTT déconnecté proprement.",
            flush=True
        )


def on_message(client, userdata, msg):
    global last_sequences

    try:
        print("", flush=True)
        print(
            "==============================================",
            flush=True
        )
        print("MESSAGE MQTT REÇU", flush=True)
        print("Topic :", msg.topic, flush=True)
        print("QoS   :", msg.qos, flush=True)
        print(
            "==============================================",
            flush=True
        )

        message = json.loads(
            msg.payload.decode("utf-8")
        )

        data = message["data"]
        signature = message["signature"]

        machine = str(data["machine"])
        sequence = int(data["sequence"])

        print(
            "Machine   :",
            machine,
            flush=True
        )
        print(
            "Sequence  :",
            sequence,
            flush=True
        )
        print(
            "Timestamp :",
            data["timestamp"],
            flush=True
        )

        # Vérification cryptographique
        signature_valide = verifier_signature(
            data,
            signature
        )

        if signature_valide:
            print(
                "Signature : VALIDE",
                flush=True
            )
        else:
            print(
                "Signature : INVALIDE",
                flush=True
            )

        # Vérification de l'ordre des messages
        derniere_sequence = last_sequences.get(
            machine,
            -1
        )

        replay = sequence <= derniere_sequence

        if replay:
            print(
                "REPLAY ATTACK détectée",
                flush=True
            )
        else:
            print(
                "Séquence : VALIDE",
                flush=True
            )

        anomalie_ia = False

        if not signature_valide:
            print(
                "Donnée rejetée : signature invalide",
                flush=True
            )

        elif replay:
            print(
                "Donnée rejetée : attaque par rejeu",
                flush=True
            )

        else:
            last_sequences[machine] = sequence

            # Variables utilisées par le modèle
            X = pd.DataFrame(
                [[
                    data["vibration"],
                    data["acoustic"],
                    data["temperature"],
                    data["current"],
                    data["IMF_1"],
                    data["IMF_2"],
                    data["IMF_3"]
                ]],
                columns=[
                    "vibration",
                    "acoustic",
                    "temperature",
                    "current",
                    "IMF_1",
                    "IMF_2",
                    "IMF_3"
                ]
            )

            # Détection d'anomalie avec Isolation Forest
            prediction = model.predict(X)[0]

            if prediction == 1:
                anomalie_ia = False
                print(
                    "État IA : NORMAL",
                    flush=True
                )
            else:
                anomalie_ia = True
                print(
                    "ALERTE IA : anomalie détectée",
                    flush=True
                )

            enregistrer_machine(
                data,
                sequence,
                anomalie_ia
            )

        alerte = generer_alerte(
            signature_valide,
            replay,
            anomalie_ia,
            data
        )

        if alerte:
            print("", flush=True)
            print(
                "========== DIAGNOSTIC ==========",
                flush=True
            )
            print(
                "Type      :",
                alerte["type_evt"],
                flush=True
            )
            print(
                "Criticité :",
                alerte["criticite_label"],
                flush=True
            )
            print(
                "Action    :",
                alerte["action"],
                flush=True
            )
            print(
                "================================",
                flush=True
            )

            enregistrer_alerte(
                data,
                alerte,
                sequence,
                signature_valide,
                replay
            )

        else:
            print(
                "Diagnostic : FONCTIONNEMENT NORMAL",
                flush=True
            )

        print(
            "Enregistrement Blockchain...",
            flush=True
        )

        enregistrer_blockchain(
            data,
            signature_valide,
            replay,
            anomalie_ia
        )

        print(
            "Traitement du message terminé.",
            flush=True
        )
        print(
            "==============================================",
            flush=True
        )

    except json.JSONDecodeError as e:
        print(
            "Message JSON invalide :",
            e,
            flush=True
        )

    except KeyError as e:
        print(
            "Champ manquant dans le message :",
            e,
            flush=True
        )

    except Exception as e:
        print(
            "Erreur traitement message :",
            e,
            flush=True
        )


mqttClient = mqtt.Client()

mqttClient.on_connect = on_connect
mqttClient.on_disconnect = on_disconnect
mqttClient.on_message = on_message


print("", flush=True)
print(
    "==============================================",
    flush=True
)
print(
    "             PI2 - EDGE IDS",
    flush=True
)
print(
    "==============================================",
    flush=True
)
print(
    "Signature Ed25519 : ACTIVE",
    flush=True
)
print(
    "Anti-rejeu        : ACTIVE",
    flush=True
)
print(
    "Isolation Forest  : ACTIVE",
    flush=True
)
print(
    "InfluxDB          : ACTIVE",
    flush=True
)
print(
    "Blockchain        : ACTIVE",
    flush=True
)
print(
    "MQTT QoS          :",
    MQTT_QOS,
    flush=True
)
print(
    "Topic             :",
    TOPIC,
    flush=True
)
print(
    "==============================================",
    flush=True
)


try:
    print(
        "Connexion au broker MQTT...",
        flush=True
    )

    mqttClient.connect(
        BROKER,
        PORT,
        keepalive=60
    )

    print(
        "Boucle MQTT démarrée.",
        flush=True
    )

    mqttClient.loop_forever()

except KeyboardInterrupt:
    print(
        "Arrêt du PI2 demandé.",
        flush=True
    )

except Exception as e:
    print(
        "Erreur MQTT :",
        e,
        flush=True
    )

finally:
    try:
        mqttClient.disconnect()
    except Exception:
        pass

    try:
        db.close()
    except Exception:
        pass

    print(
        "PI2 arrêté.",
        flush=True
    )
