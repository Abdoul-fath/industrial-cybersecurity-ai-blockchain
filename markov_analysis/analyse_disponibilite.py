import json
import re
from pathlib import Path
from datetime import datetime

EVENTS_FILE = Path(
    "/home/hisboula/PFA_CyberIA/pi2/markov_events_pi2.jsonl"
)

CYCLES_FILE = Path(
    "/home/hisboula/PFA_CyberIA/markov_analysis/disponibilite_cycles.log"
)


# ============================================================
# LECTURE DES CONFIRMATIONS
# ============================================================

confirmations = []

with open(EVENTS_FILE, "r", encoding="utf-8") as f:

    for line in f:

        line = line.strip()

        if not line:
            continue

        event = json.loads(line)

        if event.get("state") == "CONFIRMED":

            confirmations.append(
                {
                    "timestamp": datetime.fromisoformat(
                        event["timestamp"]
                    ),
                    "machine": event.get("machine"),
                    "sequence": event.get("sequence")
                }
            )


# ============================================================
# LECTURE DES CYCLES
# ============================================================

cycles = []

current_cycle = None

with open(CYCLES_FILE, "r", encoding="utf-8") as f:

    for line in f:

        line = line.strip()

        match = re.match(
            r"===== CYCLE (\d+) =====",
            line
        )

        if match:

            current_cycle = {
                "cycle": int(match.group(1))
            }

            cycles.append(current_cycle)

            continue

        if current_cycle is None:
            continue

        if line.startswith("BLOCKCHAIN_STOP "):

            timestamp = line.replace(
                "BLOCKCHAIN_STOP ",
                ""
            )

            current_cycle["stop"] = datetime.fromisoformat(
                timestamp
            )

        elif line.startswith("BLOCKCHAIN_START "):

            timestamp = line.replace(
                "BLOCKCHAIN_START ",
                ""
            )

            current_cycle["start"] = datetime.fromisoformat(
                timestamp
            )


# ============================================================
# CALCULS
# ============================================================

recovery_times = []

print("")
print("==============================================")
print(" DISPONIBILITE BLOCKCHAIN")
print("==============================================")


for cycle in cycles:

    stop_time = cycle["stop"]
    start_time = cycle["start"]

    downtime = (
        start_time - stop_time
    ).total_seconds()

    first_confirmation = None

    for confirmation in confirmations:

        if confirmation["timestamp"] >= start_time:

            first_confirmation = confirmation
            break

    print("")
    print(
        f"Cycle {cycle['cycle']}"
    )

    print(
        f"  Arrêt              : {stop_time.isoformat()}"
    )

    print(
        f"  Redémarrage        : {start_time.isoformat()}"
    )

    print(
        f"  Indisponibilité    : {downtime:.3f} s"
    )

    if first_confirmation is not None:

        recovery = (
            first_confirmation["timestamp"]
            - start_time
        ).total_seconds()

        recovery_times.append(
            recovery
        )

        print(
            "  Première confirmation : "
            f"{first_confirmation['timestamp'].isoformat()}"
        )

        print(
            f"  Temps récupération    : {recovery:.3f} s"
        )

        print(
            f"  Transaction           : "
            f"{first_confirmation['machine']} / "
            f"{first_confirmation['sequence']}"
        )

    else:

        print(
            "  Aucune confirmation après redémarrage."
        )


# ============================================================
# RESUME
# ============================================================

print("")
print("----------------------------------------------")
print("RESUME")
print("----------------------------------------------")

if recovery_times:

    mean_recovery = (
        sum(recovery_times)
        / len(recovery_times)
    )

    print(
        f"Nombre de récupérations : {len(recovery_times)}"
    )

    print(
        f"Temps moyen récupération : {mean_recovery:.6f} s"
    )

    if mean_recovery > 0:

        mu = (
            1
            /
            mean_recovery
        )

        print(
            f"mu expérimental          : {mu:.6f} s^-1"
        )

print("==============================================")
