from flask import Flask, jsonify, render_template_string
import requests
import os

from journalisation import (
    dernieres_entrees,
    statistiques_journal
)


# ============================================================
# APPLICATION
# ============================================================

app = Flask(
    __name__
)


# ============================================================
# CONFIGURATION
# ============================================================

BLOCKCHAIN_URL = os.getenv(
    "BLOCKCHAIN_URL",
    "http://blockchain:5000"
)


HOST = "0.0.0.0"

PORT = int(
    os.getenv(
        "FLASK_PORT",
        "5001"
    )
)


# ============================================================
# PAGE WEB
# ============================================================

HTML = """

<!DOCTYPE html>

<html lang="fr">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>PI2 - Edge IDS</title>

<style>

body {

    font-family: Arial, sans-serif;

    background: #f4f6f8;

    margin: 0;

    padding: 30px;

}

h1 {

    color: #1f2937;

}

.container {

    max-width: 1200px;

    margin: auto;

}

.cards {

    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(
                180px,
                1fr
            )
        );

    gap: 20px;

    margin-bottom: 30px;

}

.card {

    background: white;

    padding: 20px;

    border-radius: 10px;

    box-shadow:
        0 2px 8px
        rgba(
            0,
            0,
            0,
            0.1
        );

}

.card h3 {

    margin-top: 0;

    color: #374151;

}

.value {

    font-size: 30px;

    font-weight: bold;

    color: #2563eb;

}

table {

    width: 100%;

    border-collapse:
        collapse;

    background: white;

}

th,
td {

    padding: 10px;

    border-bottom:
        1px solid #ddd;

    text-align: left;

}

th {

    background: #1f2937;

    color: white;

}

.bad {

    color: red;

    font-weight: bold;

}

.good {

    color: green;

    font-weight: bold;

}

.alert {

    background: #fff1f2;

}

</style>

</head>


<body>

<div class="container">

<h1>
    🛡️ PI2 - Edge IDS
</h1>

<p>
    Système industriel de détection
    d'intrusions et de maintenance prédictive
</p>


<div class="cards">

<div class="card">

<h3>
Messages
</h3>

<div
    class="value"
    id="messages">
0
</div>

</div>


<div class="card">

<h3>
Alertes
</h3>

<div
    class="value"
    id="alertes">
0
</div>

</div>


<div class="card">

<h3>
Signatures invalides
</h3>

<div
    class="value"
    id="signatures">
0
</div>

</div>


<div class="card">

<h3>
Attaques Replay
</h3>

<div
    class="value"
    id="replays">
0
</div>

</div>


<div class="card">

<h3>
Anomalies IA
</h3>

<div
    class="value"
    id="anomalies">
0
</div>

</div>

</div>


<h2>
Derniers événements
</h2>


<table>

<thead>

<tr>

<th>Date</th>

<th>Type</th>

<th>Machine</th>

<th>Sequence</th>

<th>Événement</th>

<th>Criticité</th>

</tr>

</thead>


<tbody id="journal">

</tbody>

</table>

</div>


<script>


async function chargerDonnees() {

    try {

        const stats =
            await fetch(
                "/api/stats"
            );

        const s =
            await stats.json();


        document
            .getElementById(
                "messages"
            )
            .innerText =
            s.journal.messages;


        document
            .getElementById(
                "alertes"
            )
            .innerText =
            s.journal.alertes;


        document
            .getElementById(
                "signatures"
            )
            .innerText =
            s.journal.signatures_invalides;


        document
            .getElementById(
                "replays"
            )
            .innerText =
            s.journal.replays;


        document
            .getElementById(
                "anomalies"
            )
            .innerText =
            s.journal.anomalies_ia;


        const response =
            await fetch(
                "/api/journal?limit=30"
            );


        const journal =
            await response.json();


        const tbody =
            document
                .getElementById(
                    "journal"
                );


        tbody.innerHTML = "";


        journal.forEach(
            event => {

                const row =
                    document
                        .createElement(
                            "tr"
                        );


                if (
                    event.type ===
                    "alerte"
                ) {

                    row.className =
                        "alert";

                }


                row.innerHTML = `

<td>
${event.timestamp_journal || ""}
</td>

<td>
${event.type || ""}
</td>

<td>
${event.machine || ""}
</td>

<td>
${event.sequence ?? ""}
</td>

<td>
${event.evenement || ""}
</td>

<td>
${event.criticite_label || ""}
</td>

`;


                tbody.appendChild(
                    row
                );

            }
        );


    }

    catch (error) {

        console.error(
            error
        );

    }

}


chargerDonnees();


setInterval(
    chargerDonnees,
    3000
);


</script>


</body>

</html>

"""


# ============================================================
# PAGE PRINCIPALE
# ============================================================

@app.route(
    "/",
    methods=["GET"]
)

def index():

    return render_template_string(
        HTML
    )


# ============================================================
# HEALTH
# ============================================================

@app.route(
    "/api/health",
    methods=["GET"]
)

def health():

    return jsonify({

        "status": "OK",

        "service":
            "PI2 Edge IDS",

        "blockchain":
            BLOCKCHAIN_URL

    })


# ============================================================
# STATISTIQUES
# ============================================================

@app.route(
    "/api/stats",
    methods=["GET"]
)

def stats():

    journal_stats = (
        statistiques_journal()
    )


    blockchain_status = {
        "available": False
    }


    try:

        response = requests.get(

            BLOCKCHAIN_URL
            + "/verify",

            timeout=3
        )


        if response.ok:

            blockchain_status = (
                response.json()
            )


    except Exception as e:

        blockchain_status = {

            "available": False,

            "error": str(e)

        }


    return jsonify({

        "journal":
            journal_stats,

        "blockchain":
            blockchain_status

    })


# ============================================================
# JOURNAL
# ============================================================

@app.route(
    "/api/journal",
    methods=["GET"]
)

def journal():

    try:

        limite = int(
            os.getenv(
                "DEFAULT_JOURNAL_LIMIT",
                "50"
            )
        )

    except Exception:

        limite = 50


    return jsonify(
        dernieres_entrees(
            limite
        )
    )


# ============================================================
# ALERTES
# ============================================================

@app.route(
    "/api/alerts",
    methods=["GET"]
)

def alerts():

    journal = (
        dernieres_entrees(
            500
        )
    )


    alertes = [

        event

        for event in journal

        if event.get(
            "type"
        ) == "alerte"

    ]


    return jsonify(
        alertes
    )


# ============================================================
# BLOCKCHAIN
# ============================================================

@app.route(
    "/api/blockchain",
    methods=["GET"]
)

def blockchain():

    try:

        response = requests.get(

            BLOCKCHAIN_URL
            + "/chain",

            timeout=5
        )


        response.raise_for_status()


        return jsonify(
            response.json()
        )


    except Exception as e:

        return jsonify({

            "success": False,

            "error": str(e)

        }), 503


# ============================================================
# VERIFICATION BLOCKCHAIN
# ============================================================

@app.route(
    "/api/blockchain/verify",
    methods=["GET"]
)

def blockchain_verify():

    try:

        response = requests.get(

            BLOCKCHAIN_URL
            + "/verify",

            timeout=5
        )


        response.raise_for_status()


        return jsonify(
            response.json()
        )


    except Exception as e:

        return jsonify({

            "valid": False,

            "error": str(e)

        }), 503


# ============================================================
# DEMARRAGE
# ============================================================

if __name__ == "__main__":

    print("")
    print(
        "=============================================="
    )
    print(
        "          PI2 - INTERFACE FLASK"
    )
    print(
        "=============================================="
    )
    print(
        f"Port : {PORT}"
    )
    print(
        "API  : ACTIVE"
    )
    print(
        "Web  : ACTIVE"
    )
    print(
        "=============================================="
    )
    print("")


    app.run(

        host=HOST,

        port=PORT,

        debug=False
    )
