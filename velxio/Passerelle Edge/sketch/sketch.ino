// ESP32-2 - Passerelle Edge
// Décodage JSON, contrôle de cohérence, détection de rejeu/trou
// et envoi d'un ACK pour la mesure RTT côté ESP32-1.

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

const char* WIFI_SSID   = "Velxio-GUEST";
const char* MQTT_BROKER = "broker.hivemq.com";
const int   MQTT_PORT   = 1883;

const char* TOPIC     = "factory/machine1";
const char* TOPIC_ACK = "factory/machine1/ack";
const char* CLIENT_ID = "velxio-gateway2";

WiFiClient net;
PubSubClient mqttClient(net);

unsigned long recus = 0;
unsigned long valides = 0;
unsigned long rejetes = 0;
unsigned long trous = 0;
unsigned long manquants = 0;
unsigned long rejeux = 0;

unsigned long connexions = 0;
unsigned long reconnexions = 0;

long dernierSeq = -1;

bool plage(const char* nom, float valeur, float minVal, float maxVal) {
  if (valeur < minVal || valeur > maxVal) {
    Serial.print("ANOMALIE ");
    Serial.print(nom);
    Serial.print(" = ");
    Serial.print(valeur, 3);
    Serial.print(" hors [");
    Serial.print(minVal, 2);
    Serial.print(" .. ");
    Serial.print(maxVal, 2);
    Serial.println("]");
    return false;
  }

  return true;
}

void onMessage(char* topic, byte* payload, unsigned int len) {

  recus++;

  char buf[400];

  unsigned int n =
      (len < sizeof(buf) - 1) ? len : sizeof(buf) - 1;

  memcpy(buf, payload, n);
  buf[n] = '\0';

  Serial.print("RX #");
  Serial.print(recus);
  Serial.print(" len=");
  Serial.println(len);

  // Décodage JSON
  JsonDocument doc;

  DeserializationError err = deserializeJson(doc, buf);

  if (err) {
    rejetes++;
    Serial.print("REJET JSON : ");
    Serial.println(err.c_str());
    return;
  }

  JsonObject data = doc["data"];

  if (data.isNull()) {
    rejetes++;
    Serial.println("REJET : objet data absent");
    return;
  }

  // Vérification des champs obligatoires
  const char* champs[] = {
    "machine",
    "vibration",
    "acoustic",
    "temperature",
    "current",
    "IMF_1",
    "IMF_2",
    "IMF_3",
    "timestamp",
    "sequence"
  };

  for (unsigned int i = 0;
       i < sizeof(champs) / sizeof(champs[0]);
       i++) {

    if (data[champs[i]].isNull()) {
      rejetes++;

      Serial.print("REJET champ manquant : ");
      Serial.println(champs[i]);

      return;
    }
  }

  // Lecture des données
  const char* machine = data["machine"];

  float vibration = data["vibration"];
  float acoustic = data["acoustic"];
  float temperature = data["temperature"];
  float current = data["current"];
  float imf1 = data["IMF_1"];
  float imf2 = data["IMF_2"];
  float imf3 = data["IMF_3"];

  long sequence = data["sequence"];

  Serial.print(machine);
  Serial.print(" seq=");
  Serial.print(sequence);
  Serial.print(" T=");
  Serial.print(temperature, 2);
  Serial.print(" I=");
  Serial.print(current, 2);
  Serial.print(" vib=");
  Serial.println(vibration, 3);

  // Vérification de cohérence physique
  bool coherent = true;

  coherent &= plage("vibration", vibration, 0.00f, 1.00f);
  coherent &= plage("acoustic", acoustic, 0.00f, 1.00f);
  coherent &= plage("temperature", temperature, -40.0f, 125.0f);
  coherent &= plage("current", current, 0.00f, 60.00f);
  coherent &= plage("IMF_1", imf1, -1.00f, 1.00f);
  coherent &= plage("IMF_2", imf2, -1.00f, 1.00f);
  coherent &= plage("IMF_3", imf3, -1.00f, 1.00f);

  // Contrôle de séquence
  if (dernierSeq < 0) {

    Serial.print("sequence initiale : ");
    Serial.println(sequence);

  } else if (sequence <= dernierSeq) {

    rejeux++;

    Serial.print("REJEU/hors ordre : seq=");
    Serial.print(sequence);
    Serial.print(" <= last=");
    Serial.println(dernierSeq);

    return;

  } else if (sequence == dernierSeq + 1) {

    Serial.println("sequence OK");

  } else {

    trous++;

    unsigned long nbManquants =
        (unsigned long)(sequence - dernierSeq - 1);

    manquants += nbManquants;

    Serial.print("TROU : ");
    Serial.print(dernierSeq + 1);
    Serial.print("..");
    Serial.print(sequence - 1);
    Serial.print(" (");
    Serial.print(nbManquants);
    Serial.println(" manquant(s))");
  }

  dernierSeq = sequence;

  // Rejet des données physiquement incohérentes
  if (!coherent) {

    rejetes++;

    Serial.println("INCOHERENT -> rejet");

    return;
  }

  valides++;

  // ACK utilisé par ESP32-1 pour mesurer le RTT
  char ack[32];

  snprintf(
    ack,
    sizeof(ack),
    "ACK %ld",
    sequence
  );

  mqttClient.publish(TOPIC_ACK, ack);
}

void connectMQTT() {

  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setBufferSize(512);
  mqttClient.setKeepAlive(30);
  mqttClient.setCallback(onMessage);

  while (!mqttClient.connected()) {

    Serial.print("MQTT connexion... ");

    if (mqttClient.connect(CLIENT_ID)) {

      connexions++;

      if (connexions > 1) {
        reconnexions++;
      }

      Serial.print("OK, reconnex=");
      Serial.println(reconnexions);

      mqttClient.subscribe(TOPIC, 1);

      Serial.print("Abonne a ");
      Serial.println(TOPIC);

    } else {

      Serial.print("ECHEC rc=");
      Serial.println(mqttClient.state());

      delay(2000);
    }
  }
}

void setup() {

  Serial.begin(115200);
  delay(500);

  Serial.println("ESP32-2 - Passerelle Edge");

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID);

  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
  }

  Serial.println();
  Serial.print("WiFi OK - IP ");
  Serial.println(WiFi.localIP());

  connectMQTT();
}

void loop() {

  if (!mqttClient.connected()) {

    Serial.print("Lien MQTT perdu, rc=");
    Serial.println(mqttClient.state());

    connectMQTT();
  }

  mqttClient.loop();

  // Bilan périodique
  static unsigned long dernierBilan = 0;

  if (millis() - dernierBilan >= 10000) {

    dernierBilan = millis();

    Serial.print("BILAN recus=");
    Serial.print(recus);

    Serial.print(" valides=");
    Serial.print(valides);

    Serial.print(" rejetes=");
    Serial.print(rejetes);

    Serial.print(" trous=");
    Serial.print(trous);

    Serial.print(" manquants=");
    Serial.print(manquants);

    Serial.print(" rejeux=");
    Serial.print(rejeux);

    Serial.print(" reconnex=");
    Serial.println(reconnexions);
  }
}