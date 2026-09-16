import json
import os
import threading
from datetime import datetime, timezone


# ============================================================
# CONFIGURATION
# ============================================================

JOURNAL_FILE = os.getenv(
    "JOURNAL_FILE",
    "/data/journal_recepteur.json"
)


# ============================================================
# VERROU
# ============================================================

journal_lock = threading.Lock()


# ============================================================
# INITIALISATION
# ============================================================

def initialiser_journal():

    dossier = os.path.dirname(
        JOURNAL_FILE
    )

    if dossier:

        os.makedirs(
            dossier,
            exist_ok=True
        )


    if not os.path.exists(
        JOURNAL_FILE
    ):

        with open(
            JOURNAL_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                [],
                f,
                indent=4,
                ensure_ascii=False
            )


# ============================================================
# LECTURE JOURNAL
# ============================================================

def lire_journal():

    initialiser_journal()


    try:

        with open(
            JOURNAL_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            contenu = json.load(f)


        if isinstance(
            contenu,
            list
        ):

            return contenu


        return []


    except Exception:

        return []


# ============================================================
# ECRITURE JOURNAL
# ============================================================

def ecrire_journal(
    entrees
):

    dossier = os.path.dirname(
        JOURNAL_FILE
    )

    if dossier:

        os.makedirs(
            dossier,
            exist_ok=True
        )


    # --------------------------------------------------------
    # Ecriture temporaire
    # --------------------------------------------------------

    fichier_temp = (
        JOURNAL_FILE
        + ".tmp"
    )


    with open(
        fichier_temp,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(

            entrees,

            f,

            indent=4,

            ensure_ascii=False
        )


    os.replace(
        fichier_temp,
        JOURNAL_FILE
    )


# ============================================================
# AJOUT ENTREE
# ============================================================

def ajouter_entree(
    entree
):

    initialiser_journal()


    with journal_lock:

        journal = lire_journal()

        journal.append(
            entree
        )

        ecrire_journal(
            journal
        )


# ============================================================
# JOURNALISATION MESSAGE
# ============================================================

def journaliser_message(

    data,

    signature_valide,

    replay,

    anomalie_ia

):

    entree = {

        "timestamp_journal":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "type":
            "message",

        "machine":
            str(
                data.get(
                    "machine",
                    "unknown"
                )
            ),

        "sequence":
            int(
                data.get(
                    "sequence",
                    -1
                )
            ),

        "timestamp_donnee":
            str(
                data.get(
                    "timestamp",
                    ""
                )
            ),

        "signature_valide":
            bool(
                signature_valide
            ),

        "replay":
            bool(
                replay
            ),

        "anomalie_ia":
            bool(
                anomalie_ia
            ),

        "vibration":
            float(
                data.get(
                    "vibration",
                    0
                )
            ),

        "acoustic":
            float(
                data.get(
                    "acoustic",
                    0
                )
            ),

        "temperature":
            float(
                data.get(
                    "temperature",
                    0
                )
            ),

        "current":
            float(
                data.get(
                    "current",
                    0
                )
            )
    }


    ajouter_entree(
        entree
    )


# ============================================================
# JOURNALISATION ALERTE
# ============================================================

def journaliser_alerte(

    data,

    alerte,

    signature_valide,

    replay

):

    entree = {

        "timestamp_journal":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "type":
            "alerte",

        "machine":
            str(
                data.get(
                    "machine",
                    "unknown"
                )
            ),

        "sequence":
            int(
                data.get(
                    "sequence",
                    -1
                )
            ),

        "evenement":
            alerte.get(
                "type_evt",
                "unknown"
            ),

        "criticite":
            int(
                alerte.get(
                    "criticite",
                    0
                )
            ),

        "criticite_label":
            alerte.get(
                "criticite_label",
                ""
            ),

        "action":
            alerte.get(
                "action",
                ""
            ),

        "signature_valide":
            bool(
                signature_valide
            ),

        "replay":
            bool(
                replay
            )
    }


    ajouter_entree(
        entree
    )


# ============================================================
# DERNIERES ENTREES
# ============================================================

def dernieres_entrees(
    limite=50
):

    journal = lire_journal()

    return journal[
        -limite:
    ][::-1]


# ============================================================
# STATISTIQUES
# ============================================================

def statistiques_journal():

    journal = lire_journal()


    messages = 0

    alertes = 0

    signatures_invalides = 0

    replays = 0

    anomalies_ia = 0


    for entree in journal:

        if entree.get(
            "type"
        ) == "message":

            messages += 1


            if not entree.get(
                "signature_valide",
                True
            ):

                signatures_invalides += 1


            if entree.get(
                "replay",
                False
            ):

                replays += 1


            if entree.get(
                "anomalie_ia",
                False
            ):

                anomalies_ia += 1


        elif entree.get(
            "type"
        ) == "alerte":

            alertes += 1


    return {

        "messages": messages,

        "alertes": alertes,

        "signatures_invalides":
            signatures_invalides,

        "replays":
            replays,

        "anomalies_ia":
            anomalies_ia,

        "total_entrees":
            len(journal)
    }


# ============================================================
# INITIALISATION AU DEMARRAGE
# ============================================================

initialiser_journal()
