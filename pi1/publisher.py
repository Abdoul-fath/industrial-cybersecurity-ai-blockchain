import json
import time
import os
import sys
import pandas as pd

from paho.mqtt import client as mqtt
from cryptography.hazmat.primitives import serialization


# ============================================================
# CONFIGURATION
# ============================================================

BROKER = "mqtt"
PORT = 1883

TOPIC = "factory/machine1"

CSV_FILE = "/workspace/predictive_maintenance_dataset.csv"

PRIVATE_KEY_FILE = "/workspace/private_key.pem"

SEQUENCE_FILE = "/workspace/sequence.txt"

PUBLICATION_INTERVAL = 1.0

MQTT_QOS = 1

MQTT_RETAIN = False


# ============================================================
# AFFICHAGE
# ============================================================

try:
    sys.stdout.reconfigure(
        line_buffering=True,
        write_through=True
    )
except Exception:
    pass


def log(message):
    print(message, flush=True)


# ============================================================
# VERIFICATION DES FICHIERS
# ============================================================

if not os.path.exists(CSV_FILE):
    raise FileNotFoundError(
        f"Dataset introuvable : {CSV_FILE}"
    )

if not os.path.exists(PRIVATE_KEY_FILE):
    raise FileNotFoundError(
        f"Clé privée introuvable : {PRIVATE_KEY_FILE}"
    )


# ============================================================
# CHARGEMENT DE LA CLE PRIVEE ED25519
# ============================================================

try:

    with open(
        PRIVATE_KEY_FILE,
        "rb"
    ) as f:

        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None
        )

    log("✅ Clé privée Ed25519 chargée.")

except Exception as e:

    log(
        f"❌ Impossible de charger la clé privée : {e}"
    )

    sys.exit(1)


# ============================================================
# CHARGEMENT DU DATASET
# ============================================================

try:

    df = pd.read_csv(
        CSV_FILE
    )

except Exception as e:

    log(
        f"❌ Impossible de charger le dataset : {e}"
    )

    sys.exit(1)


# ============================================================
# VERIFICATION DES COLONNES
# ============================================================

REQUIRED_COLUMNS = [
    "machine_id",
    "vibration",
    "acoustic",
    "temperature",
    "current",
    "IMF_1",
    "IMF_2",
    "IMF_3",
    "timestamp"
]

missing_columns = [
    column
    for column in REQUIRED_COLUMNS
    if column not in df.columns
]

if missing_columns:

    log(
        "❌ Colonnes manquantes dans le dataset : "
        + ", ".join(missing_columns)
    )

    sys.exit(1)


log(
    f"✅ Dataset chargé : {len(df)} mesures."
)


# ============================================================
# CHARGEMENT DE LA SEQUENCE
# ============================================================

sequence = 0

if os.path.exists(SEQUENCE_FILE):

    try:

        with open(
            SEQUENCE_FILE,
            "r"
        ) as f:

            content = f.read().strip()

        if content:

            sequence = int(content)

            if sequence < 0:
                sequence = 0

            log(
                f"✅ Compteur de séquence repris : {sequence}"
            )

        else:

            sequence = 0

            log(
                "⚠️ Fichier de séquence vide. "
                "Démarrage à 0."
            )

    except Exception as e:

        sequence = 0

        log(
            f"⚠️ Fichier de séquence invalide : {e}"
        )

        log(
            "Compteur redémarré à 0."
        )

else:

    log(
        "ℹ️ Aucun fichier de séquence trouvé."
    )

    log(
        "Compteur démarré à 0."
    )


# ============================================================
# SAUVEGARDE DE LA SEQUENCE
# ============================================================

def sauvegarder_sequence(value):

    temporary_file = SEQUENCE_FILE + ".tmp"

    try:

        with open(
            temporary_file,
            "w"
        ) as f:

            f.write(
                str(value)
            )

            f.flush()

            os.fsync(
                f.fileno()
            )

        os.replace(
            temporary_file,
            SEQUENCE_FILE
        )

    except Exception as e:

        log(
            f"⚠️ Impossible de sauvegarder la séquence : {e}"
        )


# ============================================================
# CREATION CLIENT MQTT
# ============================================================

def on_connect(
    client,
    userdata,
    flags,
    rc
):

    if rc == 0:

        log("")
        log("==============================================")
        log("          PI1 - MQTT PUBLISHER")
        log("==============================================")
        log("✅ Connexion MQTT réussie")
        log(f"Broker       : {BROKER}:{PORT}")
        log(f"Topic        : {TOPIC}")
        log(f"QoS          : {MQTT_QOS}")
        log("Signature    : Ed25519")
        log("==============================================")
        log("")

    else:

        log(
            f"❌ Connexion MQTT échouée. Code : {rc}"
        )


def on_disconnect(
    client,
    userdata,
    rc
):

    if rc != 0:

        log(
            "⚠️ MQTT déconnecté. "
            "Reconnexion automatique..."
        )

    else:

        log(
            "MQTT déconnecté proprement."
        )


# ============================================================
# CREATION DU CLIENT MQTT
# ============================================================

try:

    # Compatible Paho MQTT récent
    try:

        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION1,
            client_id="pi1-publisher"
        )

    except AttributeError:

        # Compatibilité ancienne version Paho
        client = mqtt.Client(
            client_id="pi1-publisher"
        )

except Exception as e:

    log(
        f"❌ Erreur création client MQTT : {e}"
    )

    sys.exit(1)


client.on_connect = on_connect

client.on_disconnect = on_disconnect


# ============================================================
# CONFIGURATION MQTT
# ============================================================

client.reconnect_delay_set(
    min_delay=1,
    max_delay=30
)


# ============================================================
# CONNEXION MQTT AVEC RETRY
# ============================================================

def connecter_mqtt():

    while True:

        try:

            log(
                f"🔄 Connexion au broker MQTT "
                f"{BROKER}:{PORT}..."
            )

            client.connect(
                BROKER,
                PORT,
                keepalive=60
            )

            return True

        except Exception as e:

            log(
                f"❌ Broker MQTT inaccessible : {e}"
            )

            log(
                "Nouvelle tentative dans 5 secondes..."
            )

            time.sleep(5)


# ============================================================
# CONSTRUCTION DU MESSAGE
# ============================================================

def construire_message(
    row,
    current_sequence
):

    data = {

        "machine": str(
            row["machine_id"]
        ),

        "vibration": float(
            row["vibration"]
        ),

        "acoustic": float(
            row["acoustic"]
        ),

        "temperature": float(
            row["temperature"]
        ),

        "current": float(
            row["current"]
        ),

        "IMF_1": float(
            row["IMF_1"]
        ),

        "IMF_2": float(
            row["IMF_2"]
        ),

        "IMF_3": float(
            row["IMF_3"]
        ),

        "timestamp": str(
            row["timestamp"]
        ),

        "sequence": int(
            current_sequence
        )
    }

    # --------------------------------------------------------
    # REPRESENTATION CANONIQUE
    # --------------------------------------------------------

    message = json.dumps(
        data,
        sort_keys=True,
        separators=(
            ",",
            ":"
        ),
        ensure_ascii=False
    ).encode(
        "utf-8"
    )

    # --------------------------------------------------------
    # SIGNATURE ED25519
    # --------------------------------------------------------

    signature = private_key.sign(
        message
    )

    signature_hex = signature.hex()

    # --------------------------------------------------------
    # MESSAGE MQTT
    # --------------------------------------------------------

    mqtt_message = {

        "data": data,

        "signature": signature_hex
    }

    payload = json.dumps(
        mqtt_message,
        separators=(
            ",",
            ":"
        ),
        ensure_ascii=False
    )

    return data, signature_hex, payload


# ============================================================
# PUBLICATION
# ============================================================

def publier(
    data,
    signature_hex,
    payload
):

    try:

        result = client.publish(
            TOPIC,
            payload,
            qos=MQTT_QOS,
            retain=MQTT_RETAIN
        )

        if result.rc != mqtt.MQTT_ERR_SUCCESS:

            log(
                "❌ Erreur MQTT publication : "
                + mqtt.error_string(
                    result.rc
                )
            )

            return False

        result.wait_for_publish()

        if not result.is_published():

            log(
                "⚠️ Message MQTT non confirmé."
            )

            return False

        log("")
        log("----------------------------------------------")
        log("📤 MESSAGE SIGNÉ ET PUBLIÉ")
        log("----------------------------------------------")
        log(
            f"Machine      : {data['machine']}"
        )
        log(
            f"Sequence     : {data['sequence']}"
        )
        log(
            f"Timestamp    : {data['timestamp']}"
        )
        log(
            f"Vibration    : {data['vibration']}"
        )
        log(
            f"Acoustic     : {data['acoustic']}"
        )
        log(
            f"Temperature  : {data['temperature']}"
        )
        log(
            f"Current      : {data['current']}"
        )
        log(
            f"Signature    : {signature_hex[:32]}..."
        )
        log("----------------------------------------------")

        return True

    except Exception as e:

        log(
            f"❌ Erreur publication MQTT : {e}"
        )

        return False


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

def main():

    global sequence

    log("")
    log("==============================================")
    log("          PI1 - PUBLISHER INDUSTRIEL")
    log("==============================================")
    log("Dataset       : OK")
    log("Ed25519       : ACTIVE")
    log("MQTT QoS      : 1")
    log("Publication   : 1 seconde")
    log("Mode          : CONTINU")
    log("==============================================")
    log("")

    connecter_mqtt()

    client.loop_start()

    log(
        "🚀 Publication temps réel démarrée."
    )

    try:

        while True:

            for _, row in df.iterrows():

                current_sequence = sequence

                try:

                    data, signature_hex, payload = construire_message(
                        row,
                        current_sequence
                    )

                    success = publier(
                        data,
                        signature_hex,
                        payload
                    )

                    if success:

                        sequence += 1

                        sauvegarder_sequence(
                            sequence
                        )

                    else:

                        log(
                            "⚠️ Publication échouée. "
                            "La séquence n'est pas incrémentée."
                        )

                except (ValueError, TypeError) as e:

                    log(
                        f"❌ Valeur invalide dans le dataset : {e}"
                    )

                except Exception as e:

                    log(
                        f"❌ Erreur traitement mesure : {e}"
                    )

                time.sleep(
                    PUBLICATION_INTERVAL
                )

            log("")
            log("==============================================")
            log("✅ FIN DU DATASET")
            log("Redémarrage depuis la première mesure.")
            log("==============================================")
            log("")

    except KeyboardInterrupt:

        log("")
        log(
            "🛑 Publication arrêtée par l'utilisateur."
        )

    finally:

        try:
            client.loop_stop()
        except Exception:
            pass

        try:
            client.disconnect()
        except Exception:
            pass

        log(
            "✅ Connexion MQTT fermée."
        )


# ============================================================
# EXECUTION
# ============================================================

if __name__ == "__main__":

    main()
