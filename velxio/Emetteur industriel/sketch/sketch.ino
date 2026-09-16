// ESP32-1 - Emetteur industriel M01
// Publication MQTT, generation de donnees, injection de fautes
// et mesure RTT via accuse de reception.

#define FAULT_MODE 0
// 0 = nominal
// 1 = rejeu
// 2 = donnees falsifiees
// 3 = trou de sequence

#include <WiFi.h>
#include <PubSubClient.h>

const char* WIFI_SSID   = "Velxio-GUEST";
const char* MQTT_BROKER = "broker.hivemq.com";
const int   MQTT_PORT   = 1883;

const char* TOPIC     = "factory/machine1";
const char* TOPIC_ACK = "factory/machine1/ack";
const char* CLIENT_ID = "velxio-node1";
const char* MACHINE   = "M01";

const unsigned long PERIODE_MS = 2000;
const uint32_t BASE_EPOCH = 1719828600UL;

WiFiClient net;
PubSubClient mqttClient(net);

uint32_t sequence = 73706;
unsigned long publies = 0;
unsigned long dernierEnvoi = 0;

char dernierMsg[320] = {0};

// Mesure RTT
#define NB_PENDANTES 8

uint32_t pendSeq[NB_PENDANTES] = {0};
unsigned long pendMs[NB_PENDANTES] = {0};

unsigned long rttNb = 0;
unsigned long rttMin = 0;
unsigned long rttMax = 0;
unsigned long rttSomme = 0;

void noterEnvoi(uint32_t seq) {
  static uint8_t index = 0;

  pendSeq[index] = seq;
  pendMs[index] = millis();

  index = (index + 1) % NB_PENDANTES;
}

long rttPour(uint32_t seq) {
  for (uint8_t i = 0; i < NB_PENDANTES; i++) {
    if (pendSeq[i] == seq) {
      return (long)(millis() - pendMs[i]);
    }
  }

  return -1;
}

void onAck(char* topic, byte* payload, unsigned int len) {

  char buf[64];

  unsigned int n =
      (len < sizeof(buf) - 1) ? len : sizeof(buf) - 1;

  memcpy(buf, payload, n);
  buf[n] = '\0';

  unsigned long seqAck = 0;

  if (sscanf(buf, "ACK %lu", &seqAck) != 1) {
    return;
  }

  long rtt = rttPour((uint32_t)seqAck);

  if (rtt < 0) {
    return;
  }

  rttNb++;
  rttSomme += (unsigned long)rtt;

  if (rttNb == 1 || (unsigned long)rtt < rttMin) {
    rttMin = (unsigned long)rtt;
  }

  if ((unsigned long)rtt > rttMax) {
    rttMax = (unsigned long)rtt;
  }

  Serial.print("RTT seq=");
  Serial.print(seqAck);
  Serial.print(" ");
  Serial.print(rtt);
  Serial.println(" ms");
}

// Donnees industrielles simulees
float vibration = 0.820f;
float acoustic = 0.672f;
float temperature = 64.37f;
float current = 11.90f;

float imf1 = 0.241f;
float imf2 = -0.011f;
float imf3 = 0.024f;

float bruit() {
  static uint32_t seed = 0x2545F491u;

  seed = seed * 1664525u + 1013904223u;

  return (float)((seed >> 8) & 0xFFFF) / 65535.0f;
}

float derive(float valeur, float pas, float minVal, float maxVal) {

  float nouvelleValeur =
      valeur + (bruit() - 0.5f) * 2.0f * pas;

  if (nouvelleValeur < minVal) {
    nouvelleValeur = minVal;
  }

  if (nouvelleValeur > maxVal) {
    nouvelleValeur = maxVal;
  }

  return nouvelleValeur;
}

void formatTimestamp(uint32_t epoch, char* out, size_t n) {

  uint32_t jours = epoch / 86400UL;
  uint32_t reste = epoch % 86400UL;

  int64_t z = (int64_t)jours + 719468;
  int64_t era = z / 146097;

  uint32_t doe =
      (uint32_t)(z - era * 146097);

  uint32_t yoe =
      (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;

  int64_t an =
      (int64_t)yoe + era * 400;

  uint32_t doy =
      doe - (365 * yoe + yoe / 4 - yoe / 100);

  int mp =
      (int)((5 * doy + 2) / 153);

  int jour =
      (int)(doy - (153 * mp + 2) / 5 + 1);

  int mois =
      mp + (mp < 10 ? 3 : -9);

  if (mois <= 2) {
    an++;
  }

  snprintf(
    out,
    n,
    "%04d-%02d-%02d %02d:%02d:%02d",
    (int)an,
    mois,
    jour,
    (int)(reste / 3600),
    (int)((reste % 3600) / 60),
    (int)(reste % 60)
  );
}

void connectMQTT() {

  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setBufferSize(512);
  mqttClient.setKeepAlive(30);
  mqttClient.setCallback(onAck);

  while (!mqttClient.connected()) {

    Serial.print("MQTT connexion... ");

    if (mqttClient.connect(CLIENT_ID)) {

      Serial.println("OK");

      mqttClient.subscribe(TOPIC_ACK, 1);

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

  Serial.println("ESP32-1 - Emetteur industriel M01");

  Serial.print("FAULT_MODE=");
  Serial.println(FAULT_MODE);

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

void envoyer(const char* message, uint32_t seq) {

  bool ok = mqttClient.publish(TOPIC, message);

  publies++;

  if (ok) {
    noterEnvoi(seq);
  }

  Serial.print("TX seq=");
  Serial.print(seq);

  Serial.print(" len=");
  Serial.print(strlen(message));

  Serial.print(" pub=");
  Serial.print(publies);

  Serial.println(ok ? " OK" : " ECHEC");
}

void loop() {

  if (!mqttClient.connected()) {

    Serial.print("Lien MQTT perdu, rc=");
    Serial.println(mqttClient.state());

    connectMQTT();
  }

  mqttClient.loop();

  // Statistiques RTT toutes les 20 secondes
  static unsigned long dernierBilan = 0;

  if (millis() - dernierBilan >= 20000) {

    dernierBilan = millis();

    if (rttNb > 0) {

      Serial.print("RTT min=");
      Serial.print(rttMin);

      Serial.print(" moy=");
      Serial.print(rttSomme / rttNb);

      Serial.print(" max=");
      Serial.print(rttMax);

      Serial.print(" mesures=");
      Serial.println(rttNb);

    } else {

      Serial.println("RTT : aucune mesure");
    }
  }

  if (millis() - dernierEnvoi < PERIODE_MS) {
    return;
  }

  dernierEnvoi = millis();

  vibration =
      derive(vibration, 0.03f, 0.60f, 0.95f);

  acoustic =
      derive(acoustic, 0.02f, 0.60f, 0.78f);

  temperature =
      derive(temperature, 0.35f, 62.00f, 67.00f);

  current =
      derive(current, 0.25f, 10.50f, 13.00f);

  imf1 =
      derive(imf1, 0.02f, 0.10f, 0.35f);

  imf2 =
      derive(imf2, 0.01f, -0.05f, 0.05f);

  imf3 =
      derive(imf3, 0.01f, -0.02f, 0.06f);

  float tempEnv = temperature;
  float currentEnv = current;

#if FAULT_MODE == 2
  tempEnv = 999.99f;
  currentEnv = -42.00f;
#endif

  char timestamp[24];

  formatTimestamp(
    BASE_EPOCH + (millis() / 1000UL),
    timestamp,
    sizeof(timestamp)
  );

  char message[320];

  snprintf(
    message,
    sizeof(message),

    "{\"data\":{"
    "\"machine\":\"%s\","
    "\"vibration\":%.3f,"
    "\"acoustic\":%.3f,"
    "\"temperature\":%.2f,"
    "\"current\":%.2f,"
    "\"IMF_1\":%.3f,"
    "\"IMF_2\":%.3f,"
    "\"IMF_3\":%.3f,"
    "\"timestamp\":\"%s\","
    "\"sequence\":%lu"
    "}}",

    MACHINE,
    vibration,
    acoustic,
    tempEnv,
    currentEnv,
    imf1,
    imf2,
    imf3,
    timestamp,
    (unsigned long)sequence
  );

  envoyer(message, sequence);

  strncpy(
    dernierMsg,
    message,
    sizeof(dernierMsg) - 1
  );

  dernierMsg[sizeof(dernierMsg) - 1] = '\0';

#if FAULT_MODE == 1
  // Rejeu du meme message avec la meme sequence
  envoyer(dernierMsg, sequence);
#endif

  sequence++;

#if FAULT_MODE == 3
  // Saut volontaire d'un numero de sequence
  sequence++;
#endif
}