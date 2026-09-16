import json
import pandas as pd
from pathlib import Path


PI1_FILE = Path(
    "/home/hisboula/PFA_CyberIA/pi1/markov_events_pi1.jsonl"
)

PI2_FILE = Path(
    "/home/hisboula/PFA_CyberIA/pi2/markov_events_pi2.jsonl"
)

OUTPUT_FILE = Path(
    "/home/hisboula/PFA_CyberIA/markov_analysis/scenario1_results.csv"
)


def load_jsonl(path):

    rows = []

    with open(path, "r", encoding="utf-8") as f:

        for line in f:

            line = line.strip()

            if not line:
                continue

            try:
                rows.append(json.loads(line))

            except json.JSONDecodeError:
                print(
                    "Ligne JSON invalide ignorée :",
                    line[:100]
                )

    return pd.DataFrame(rows)


# ============================================================
# CHARGEMENT
# ============================================================

pi1 = load_jsonl(PI1_FILE)
pi2 = load_jsonl(PI2_FILE)

events = pd.concat(
    [pi1, pi2],
    ignore_index=True
)

events["timestamp"] = pd.to_datetime(
    events["timestamp"],
    utc=True
)

events = events.sort_values(
    [
        "machine",
        "sequence",
        "timestamp"
    ]
)


# ============================================================
# CONSTRUCTION D'UNE LIGNE PAR TRANSACTION
# ============================================================

pivot = events.pivot_table(
    index=[
        "machine",
        "sequence"
    ],
    columns="state",
    values="timestamp",
    aggfunc="first"
).reset_index()


expected_states = [
    "CREATED",
    "MQTT_SUBMITTED",
    "MQTT_ACKNOWLEDGED",
    "RECEIVED",
    "VALIDATED",
    "BLOCKCHAIN_SUBMITTED",
    "CONFIRMED",
    "MQTT_FAILED",
    "SECURITY_REJECTED",
    "BLOCKCHAIN_REJECTED",
    "BLOCKCHAIN_FAILED"
]


for state in expected_states:

    if state not in pivot.columns:
        pivot[state] = pd.NaT


# ============================================================
# CALCUL DES LATENCES
# ============================================================

def latency_ms(start, end):

    if pd.isna(start) or pd.isna(end):
        return None

    return (
        end - start
    ).total_seconds() * 1000


pivot["latency_creation_mqtt_ms"] = pivot.apply(
    lambda r: latency_ms(
        r["CREATED"],
        r["MQTT_SUBMITTED"]
    ),
    axis=1
)

pivot["latency_mqtt_ms"] = pivot.apply(
    lambda r: latency_ms(
        r["MQTT_SUBMITTED"],
        r["RECEIVED"]
    ),
    axis=1
)

pivot["latency_mqtt_ack_ms"] = pivot.apply(
    lambda r: latency_ms(
        r["MQTT_SUBMITTED"],
        r["MQTT_ACKNOWLEDGED"]
    ),
    axis=1
)

pivot["latency_validation_ms"] = pivot.apply(
    lambda r: latency_ms(
        r["RECEIVED"],
        r["VALIDATED"]
    ),
    axis=1
)

pivot["latency_edge_ms"] = pivot.apply(
    lambda r: latency_ms(
        r["VALIDATED"],
        r["BLOCKCHAIN_SUBMITTED"]
    ),
    axis=1
)

pivot["latency_blockchain_ms"] = pivot.apply(
    lambda r: latency_ms(
        r["BLOCKCHAIN_SUBMITTED"],
        r["CONFIRMED"]
    ),
    axis=1
)

pivot["latency_total_ms"] = pivot.apply(
    lambda r: latency_ms(
        r["CREATED"],
        r["CONFIRMED"]
    ),
    axis=1
)


# ============================================================
# STATUT FINAL
# ============================================================

def determine_status(row):

    if pd.notna(row["CONFIRMED"]):
        return "CONFIRMED"

    if pd.notna(row["BLOCKCHAIN_REJECTED"]):
        return "BLOCKCHAIN_REJECTED"

    if pd.notna(row["BLOCKCHAIN_FAILED"]):
        return "BLOCKCHAIN_FAILED"

    if pd.notna(row["SECURITY_REJECTED"]):
        return "SECURITY_REJECTED"

    if pd.notna(row["MQTT_FAILED"]):
        return "MQTT_FAILED"

    return "INCOMPLETE"


pivot["final_status"] = pivot.apply(
    determine_status,
    axis=1
)


# ============================================================
# COMPTEURS
# ============================================================

created = pivot["CREATED"].notna().sum()

mqtt_submitted = pivot[
    "MQTT_SUBMITTED"
].notna().sum()

mqtt_ack = pivot[
    "MQTT_ACKNOWLEDGED"
].notna().sum()

received = pivot[
    "RECEIVED"
].notna().sum()

validated = pivot[
    "VALIDATED"
].notna().sum()

blockchain_submitted = pivot[
    "BLOCKCHAIN_SUBMITTED"
].notna().sum()

confirmed = pivot[
    "CONFIRMED"
].notna().sum()


# ============================================================
# PROBABILITES
# ============================================================

def prob(numerator, denominator):

    if denominator == 0:
        return 0.0

    return numerator / denominator


p_c_m = prob(
    mqtt_submitted,
    created
)

p_m_r = prob(
    received,
    mqtt_submitted
)

p_r_v = prob(
    validated,
    received
)

p_v_b = prob(
    blockchain_submitted,
    validated
)

p_b_c = prob(
    confirmed,
    blockchain_submitted
)


# ============================================================
# SAUVEGARDE
# ============================================================

pivot.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# AFFICHAGE
# ============================================================

print("")
print("==============================================")
print(" ANALYSE MARKOV - SCENARIO 1")
print("==============================================")

print(
    f"Transactions créées              : {created}"
)

print(
    f"Soumises à MQTT                  : {mqtt_submitted}"
)

print(
    f"Acquittées MQTT QoS 1            : {mqtt_ack}"
)

print(
    f"Reçues par PI2                   : {received}"
)

print(
    f"Validées                         : {validated}"
)

print(
    f"Soumises à la blockchain         : {blockchain_submitted}"
)

print(
    f"Confirmées blockchain            : {confirmed}"
)


print("")
print("PROBABILITES EMPIRIQUES")
print("----------------------------------------------")

print(
    f"P(CREATED -> MQTT_SUBMITTED) = {p_c_m:.6f}"
)

print(
    f"P(MQTT_SUBMITTED -> RECEIVED) = {p_m_r:.6f}"
)

print(
    f"P(RECEIVED -> VALIDATED) = {p_r_v:.6f}"
)

print(
    f"P(VALIDATED -> BLOCKCHAIN_SUBMITTED) = {p_v_b:.6f}"
)

print(
    f"P(BLOCKCHAIN_SUBMITTED -> CONFIRMED) = {p_b_c:.6f}"
)


# ============================================================
# STATISTIQUES LATENCES
# ============================================================

latency_columns = [

    "latency_creation_mqtt_ms",

    "latency_mqtt_ms",

    "latency_mqtt_ack_ms",

    "latency_validation_ms",

    "latency_edge_ms",

    "latency_blockchain_ms",

    "latency_total_ms"
]


print("")
print("LATENCES")
print("----------------------------------------------")


for column in latency_columns:

    values = pivot[column].dropna()

    if len(values) == 0:
        continue

    print("")
    print(column)

    print(
        f"  N       : {len(values)}"
    )

    print(
        f"  Moyenne : {values.mean():.3f} ms"
    )

    print(
        f"  Médiane : {values.median():.3f} ms"
    )

    print(
        f"  Min     : {values.min():.3f} ms"
    )

    print(
        f"  Max     : {values.max():.3f} ms"
    )

    print(
        f"  P95     : {values.quantile(0.95):.3f} ms"
    )

    print(
        f"  P99     : {values.quantile(0.99):.3f} ms"
    )


# ============================================================
# VERIFICATION LATENCES MQTT NEGATIVES
# ============================================================

negative_mqtt = pivot[
    pivot["latency_mqtt_ms"] < 0
]


print("")
print("VERIFICATION MQTT")
print("----------------------------------------------")

print(
    f"Latences MQTT négatives : {len(negative_mqtt)}"
)


# ============================================================
# TRANSACTIONS INCOMPLETES
# ============================================================

incomplete = pivot[
    pivot["final_status"] == "INCOMPLETE"
]


print("")
print("TRANSACTIONS INCOMPLETES")
print("----------------------------------------------")

print(
    f"Nombre : {len(incomplete)}"
)


if len(incomplete) > 0:

    print(
        incomplete[
            [
                "machine",
                "sequence",
                "CREATED",
                "MQTT_SUBMITTED",
                "MQTT_ACKNOWLEDGED",
                "RECEIVED",
                "VALIDATED",
                "BLOCKCHAIN_SUBMITTED",
                "CONFIRMED"
            ]
        ].to_string(
            index=False
        )
    )


print("")
print(
    f"CSV généré : {OUTPUT_FILE}"
)

print("==============================================")
