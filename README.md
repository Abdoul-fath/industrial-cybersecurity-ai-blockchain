# Intelligent Industrial Cybersecurity System using AI, Blockchain, M2M and Markov Processes

> Research & Development prototype for predictive maintenance, intrusion detection, industrial data integrity and probabilistic reliability analysis in Industry 4.0 environments.

## Overview

This project was developed as part of an engineering internship at **Smart Automation Technologies**.

The objective is to design and experimentally validate an intelligent industrial cybersecurity architecture combining:

- Machine-to-Machine (M2M) communications
- MQTT
- Edge Computing
- Artificial Intelligence / Anomaly Detection
- Intrusion Detection System (IDS)
- Blockchain-based integrity and traceability
- Predictive Maintenance
- Markov Processes for probabilistic analysis
- Real-time monitoring and visualization

The system simulates an industrial machine transmitting sensor data to an Edge gateway, where the data are verified, analyzed, stored, monitored and protected.

---

## System Architecture

```text
Industrial Machine / PI1
        │
        │ Sensor Data
        │ JSON + Sequence + Ed25519 Signature
        ▼
      MQTT
   Mosquitto Broker
        │
        ▼
Edge Gateway / PI2
        │
        ├── Signature Verification
        ├── Replay Detection
        ├── AI / Isolation Forest
        ├── Intrusion Detection
        ├── Alert Generation
        ├── InfluxDB Storage
        │
        ├────────► Grafana Monitoring
        │
        ▼
Blockchain Service
        │
        ├── SHA-256 Hashing
        ├── Event Traceability
        └── Integrity Verification

                +

        Markov Analysis
        │
        ├── Transaction lifecycle
        ├── System availability
        ├── Recovery analysis
        └── Cybersecurity states
```

---

## Main Components

### PI1 — Industrial Node

The first node represents an industrial machine or intelligent sensor.

Main functions:

- industrial sensor data generation
- predictive-maintenance dataset replay
- JSON message creation
- sequence-number generation
- Ed25519 digital signature
- MQTT publication
- Markov event logging

### PI2 — Edge Gateway

The second node acts as an Edge gateway and monitoring node.

Main functions:

- MQTT subscription
- digital-signature verification
- replay-attack detection
- anomaly detection
- IDS processing
- alert generation
- InfluxDB storage
- blockchain event submission
- Markov event logging

---

## Artificial Intelligence

The prototype includes anomaly-detection mechanisms based on Machine Learning.

The main model used in the experimental architecture is:

- **Isolation Forest**

The Edge node analyzes industrial variables such as:

- vibration
- acoustic signal
- temperature
- electrical current
- IMF_1
- IMF_2
- IMF_3

---

## Dataset

The project uses the **IoT Integrated Predictive Maintenance Dataset**.

Dataset source:

https://www.kaggle.com/datasets/ziya07/iot-integrated-predictive-maintenance-dataset

Main features:

- Timestamp
- Machine ID
- Vibration
- Acoustic signal
- Temperature
- Current
- IMF_1
- IMF_2
- IMF_3
- Machine state label

---

## Cybersecurity Mechanisms

The prototype integrates several protection mechanisms:

- Ed25519 digital signatures
- message integrity verification
- sequence-number validation
- replay-attack detection
- invalid-signature detection
- industrial-data consistency checks
- IDS-based anomaly detection
- blockchain event traceability

Controlled attack scenarios are implemented in the `attacks/` directory.

---

## Blockchain Layer

A lightweight blockchain service was implemented using Python, Flask and SQLite.

The blockchain is used for:

- critical-event traceability
- SHA-256 hashing
- block chaining
- timestamping
- integrity verification
- security-event logging

This implementation is intentionally lightweight and does not implement a distributed consensus mechanism such as Ethereum or Hyperledger Fabric.

---

## Markov Process Analysis

Markov models were used to analyze the probabilistic behavior of the experimental architecture.

Three main scenarios were studied.

### 1. Transaction Lifecycle

Example states:

```text
CREATED
   ↓
MQTT_SUBMITTED
   ↓
RECEIVED
   ↓
VALIDATED
   ↓
BLOCKCHAIN_SUBMITTED
   ↓
CONFIRMED
```

The transition probabilities were estimated directly from experimental logs.

### 2. Blockchain Availability

A Continuous-Time Markov Chain (CTMC) was used to represent:

```text
AVAILABLE ⇄ UNAVAILABLE
```

The recovery rate was estimated from controlled blockchain service interruptions.

### 3. Cybersecurity States

Security transitions include:

```text
RECEIVED
   ├── VALIDATED
   └── SECURITY_REJECTED
          ├── INVALID_SIGNATURE
          └── REPLAY
```

---

## Experimental Results

Some representative results obtained during the experiments:

| Experiment | Result |
|---|---:|
| Nominal transactions at 1 msg/s | 1014 / 1014 confirmed |
| Nominal transactions at 10 msg/s | 1123 / 1123 confirmed |
| Nominal transactions at 20 msg/s | 1254 / 1254 confirmed |
| Blockchain mean recovery time | ≈ 2.53 s |
| Invalid-signature attacks detected | 20 / 20 |
| Replay attacks detected | 20 / 20 |
| Controlled malicious messages detected | 40 / 40 |
| Velxio nominal MQTT validation | 51 / 51 messages |

At approximately **40 messages/s**, the system eventually confirmed all messages after the queue was drained, but a strong backlog appeared and the mean end-to-end latency increased significantly.

---

## Velxio Validation

A complementary embedded-system validation was performed using **Velxio**.

Because networking between simulated Raspberry Pi Linux guests was not available in the platform, the M2M communication layer was reproduced using two ESP32 boards:

```text
ESP32-1
Industrial Node
    │
    │ MQTT
    ▼
Public MQTT Broker
    │
    ▼
ESP32-2
Edge Gateway
```

The following scenarios were validated:

- nominal MQTT communication
- replay detection
- falsified industrial data detection
- missing sequence detection
- RTT measurement using acknowledgements

---

## Monitoring

Industrial measurements and security events are stored in **InfluxDB** and visualized using **Grafana**.

This enables:

- real-time monitoring
- historical analysis
- anomaly visualization
- security-event tracking

---

## Technologies

### Languages

- Python
- C/C++ (ESP32 / Arduino)
- Bash
- YAML
- JSON

### Infrastructure

- Docker
- Docker Compose
- Ubuntu
- VMware

### Communication

- MQTT
- TCP/IP
- HTTP

### Data & Monitoring

- InfluxDB
- Grafana

### AI / Data Science

- Scikit-learn
- Pandas
- NumPy
- Isolation Forest

### Security

- Ed25519
- SHA-256
- IDS
- Blockchain

### Embedded Simulation

- Velxio
- ESP32

---

## Project Structure

```text
.
├── attacks/
├── blockchain/
├── docs/
├── markov_analysis/
├── mosquitto/
├── pi1/
├── pi2/
├── velxio/
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## Running the Project

### Requirements

- Docker
- Docker Compose

Clone the repository:

```bash
git clone <repository-url>
cd industrial-cybersecurity-ai-blockchain
```

Start the complete architecture:

```bash
docker compose up --build
```

Stop the services:

```bash
docker compose down
```

---

## Research Report

The complete engineering report describing the theoretical background, system architecture, cybersecurity scenarios, experimental results and Markov-process analysis is available in:

```text
docs/report.pdf
```

---

## Limitations

Current limitations include:

- lightweight single-node blockchain
- no distributed consensus
- experimentally injected blockchain failures
- limited number of cybersecurity attack types
- simulation-based Raspberry Pi environment
- no persistent retry queue for failed blockchain submissions

---

## Future Work

Future developments may include:

- physical deployment on Raspberry Pi devices
- OPC UA and Modbus TCP integration
- distributed permissioned blockchain
- Hyperledger Fabric experimentation
- persistent event-retry mechanism
- advanced DoS/DDoS scenarios
- deep-learning-based IDS
- long-duration industrial testing
- extended Markov reliability models

---

## Author

**Abdoul-Fatah Omar Hassan**

Engineering Student — Telecommunications Systems and Networks  
ENSA Tétouan

Project developed during an R&D internship at **Smart Automation Technologies**.

---

## Disclaimer

This project was developed for academic and research purposes.

All cybersecurity experiments were performed in controlled and authorized environments.