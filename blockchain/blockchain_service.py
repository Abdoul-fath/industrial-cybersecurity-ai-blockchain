from flask import Flask, request, jsonify
import hashlib
import json
import sqlite3
import os
import threading
from datetime import datetime, timezone


# ============================================================
# APPLICATION FLASK
# ============================================================

app = Flask(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

DB_FILE = "/data/blockchain.db"

DB_DIRECTORY = os.path.dirname(
    DB_FILE
)

os.makedirs(
    DB_DIRECTORY,
    exist_ok=True
)


# ============================================================
# VERROU SQLITE
# ============================================================

db_lock = threading.Lock()


# ============================================================
# BASE DE DONNEES
# ============================================================

def get_db():

    conn = sqlite3.connect(
        DB_FILE,
        timeout=30
    )

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# INITIALISATION DATABASE
# ============================================================

def init_db():

    with db_lock:

        conn = get_db()

        try:

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS blocks (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    block_index INTEGER NOT NULL UNIQUE,

                    timestamp TEXT NOT NULL,

                    node_id TEXT NOT NULL,

                    event_type TEXT NOT NULL,

                    criticity INTEGER NOT NULL,

                    verification TEXT NOT NULL,

                    data_hash TEXT NOT NULL,

                    previous_hash TEXT NOT NULL,

                    block_hash TEXT NOT NULL UNIQUE,

                    machine TEXT,

                    sequence INTEGER

                )
                """
            )

            # ------------------------------------------------
            # Compatibilité avec ancienne base
            # ------------------------------------------------

            existing_columns = [
                row["name"]
                for row in conn.execute(
                    "PRAGMA table_info(blocks)"
                ).fetchall()
            ]

            if "machine" not in existing_columns:

                conn.execute(
                    "ALTER TABLE blocks ADD COLUMN machine TEXT"
                )

            if "sequence" not in existing_columns:

                conn.execute(
                    "ALTER TABLE blocks ADD COLUMN sequence INTEGER"
                )

            conn.commit()

        finally:

            conn.close()


# ============================================================
# HASH SHA-256
# ============================================================

def calculate_hash(block):

    block_string = json.dumps(
        block,
        sort_keys=True,
        separators=(
            ",",
            ":"
        ),
        ensure_ascii=False
    )

    return hashlib.sha256(
        block_string.encode(
            "utf-8"
        )
    ).hexdigest()


# ============================================================
# CREATION DU DICTIONNAIRE D'UN BLOC
# ============================================================

def block_for_hash(block):

    return {

        "block_index": int(
            block["block_index"]
        ),

        "timestamp": str(
            block["timestamp"]
        ),

        "node_id": str(
            block["node_id"]
        ),

        "event_type": str(
            block["event_type"]
        ),

        "criticity": int(
            block["criticity"]
        ),

        "verification": str(
            block["verification"]
        ),

        "data_hash": str(
            block["data_hash"]
        ),

        "previous_hash": str(
            block["previous_hash"]
        )
    }


# ============================================================
# DERNIER BLOC
# ============================================================

def get_last_block():

    conn = get_db()

    try:

        row = conn.execute(
            """
            SELECT *
            FROM blocks
            ORDER BY block_index DESC
            LIMIT 1
            """
        ).fetchone()

        return row

    finally:

        conn.close()


# ============================================================
# BLOC GENESIS
# ============================================================

def create_genesis_block():

    with db_lock:

        conn = get_db()

        try:

            row = conn.execute(
                """
                SELECT *
                FROM blocks
                ORDER BY block_index ASC
                LIMIT 1
                """
            ).fetchone()

            if row is not None:

                return dict(row)

            block = {

                "block_index": 0,

                "timestamp":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),

                "node_id":
                    "BLOCKCHAIN",

                "event_type":
                    "GENESIS",

                "criticity":
                    0,

                "verification":
                    "INITIALISATION",

                "data_hash":
                    "0" * 64,

                "previous_hash":
                    "0" * 64
            }

            block_hash = calculate_hash(
                block
            )

            conn.execute(
                """
                INSERT INTO blocks (

                    block_index,

                    timestamp,

                    node_id,

                    event_type,

                    criticity,

                    verification,

                    data_hash,

                    previous_hash,

                    block_hash,

                    machine,

                    sequence

                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    block["block_index"],
                    block["timestamp"],
                    block["node_id"],
                    block["event_type"],
                    block["criticity"],
                    block["verification"],
                    block["data_hash"],
                    block["previous_hash"],
                    block_hash,
                    None,
                    None
                )
            )

            conn.commit()

            block["block_hash"] = block_hash

            print(
                "✅ Bloc Genesis créé.",
                flush=True
            )

            return block

        finally:

            conn.close()


# ============================================================
# AJOUT D'UN BLOC
# ============================================================

def add_block(data):

    with db_lock:

        conn = get_db()

        try:

            # ------------------------------------------------
            # Dernier bloc
            # ------------------------------------------------

            last_block = conn.execute(
                """
                SELECT *
                FROM blocks
                ORDER BY block_index DESC
                LIMIT 1
                """
            ).fetchone()

            # ------------------------------------------------
            # Genesis si nécessaire
            # ------------------------------------------------

            if last_block is None:

                genesis = {

                    "block_index": 0,

                    "timestamp":
                        datetime.now(
                            timezone.utc
                        ).isoformat(),

                    "node_id":
                        "BLOCKCHAIN",

                    "event_type":
                        "GENESIS",

                    "criticity":
                        0,

                    "verification":
                        "INITIALISATION",

                    "data_hash":
                        "0" * 64,

                    "previous_hash":
                        "0" * 64
                }

                genesis_hash = calculate_hash(
                    genesis
                )

                conn.execute(
                    """
                    INSERT INTO blocks (

                        block_index,
                        timestamp,
                        node_id,
                        event_type,
                        criticity,
                        verification,
                        data_hash,
                        previous_hash,
                        block_hash,
                        machine,
                        sequence

                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        genesis["block_index"],
                        genesis["timestamp"],
                        genesis["node_id"],
                        genesis["event_type"],
                        genesis["criticity"],
                        genesis["verification"],
                        genesis["data_hash"],
                        genesis["previous_hash"],
                        genesis_hash,
                        None,
                        None
                    )
                )

                conn.commit()

                last_block = conn.execute(
                    """
                    SELECT *
                    FROM blocks
                    ORDER BY block_index DESC
                    LIMIT 1
                    """
                ).fetchone()

            # ------------------------------------------------
            # Nouvel index
            # ------------------------------------------------

            block_index = (
                int(
                    last_block["block_index"]
                )
                + 1
            )

            # ------------------------------------------------
            # Nouveau bloc
            # ------------------------------------------------

            block = {

                "block_index":
                    block_index,

                "timestamp":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),

                "node_id":
                    data["node_id"],

                "event_type":
                    data["event_type"],

                "criticity":
                    int(
                        data["criticity"]
                    ),

                "verification":
                    data["verification"],

                "data_hash":
                    data["data_hash"],

                "previous_hash":
                    last_block["block_hash"]
            }

            # ------------------------------------------------
            # Hash
            # ------------------------------------------------

            block_hash = calculate_hash(
                block
            )

            # ------------------------------------------------
            # INSERT
            # ------------------------------------------------

            conn.execute(
                """
                INSERT INTO blocks (

                    block_index,

                    timestamp,

                    node_id,

                    event_type,

                    criticity,

                    verification,

                    data_hash,

                    previous_hash,

                    block_hash,

                    machine,

                    sequence

                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    block["block_index"],
                    block["timestamp"],
                    block["node_id"],
                    block["event_type"],
                    block["criticity"],
                    block["verification"],
                    block["data_hash"],
                    block["previous_hash"],
                    block_hash,
                    data.get("machine"),
                    data.get("sequence")
                )
            )

            conn.commit()

            block["block_hash"] = block_hash

            block["machine"] = data.get(
                "machine"
            )

            block["sequence"] = data.get(
                "sequence"
            )

            return block

        finally:

            conn.close()


# ============================================================
# VALIDATION PAYLOAD
# ============================================================

def validate_payload(data):

    if not isinstance(
        data,
        dict
    ):

        return (
            False,
            "JSON invalide"
        )

    required_fields = [

        "node_id",

        "event_type",

        "criticity",

        "verification",

        "data_hash"
    ]

    for field in required_fields:

        if field not in data:

            return (
                False,
                f"Champ manquant : {field}"
            )

    # --------------------------------------------------------
    # Criticité
    # --------------------------------------------------------

    try:

        criticity = int(
            data["criticity"]
        )

    except Exception:

        return (
            False,
            "criticity doit être un entier"
        )

    if criticity < 0 or criticity > 3:

        return (
            False,
            "criticity doit être comprise entre 0 et 3"
        )

    # --------------------------------------------------------
    # Hash
    # --------------------------------------------------------

    data_hash = str(
        data["data_hash"]
    )

    if len(data_hash) != 64:

        return (
            False,
            "data_hash doit contenir 64 caractères"
        )

    try:

        int(
            data_hash,
            16
        )

    except ValueError:

        return (
            False,
            "data_hash doit être un SHA-256 hexadécimal"
        )

    return (
        True,
        None
    )


# ============================================================
# API HEALTH
# ============================================================

@app.route(
    "/health",
    methods=["GET"]
)
def health():

    return jsonify({

        "status":
            "ok",

        "service":
            "blockchain",

        "database":
            DB_FILE
    })


# ============================================================
# API AJOUT BLOC
# ============================================================

@app.route(
    "/add_block",
    methods=["POST"]
)
def api_add_block():

    try:

        data = request.get_json(
            silent=True
        )

        valid, error = validate_payload(
            data
        )

        if not valid:

            return jsonify({

                "success":
                    False,

                "error":
                    error

            }), 400

        block = add_block(
            data
        )

        print(
            "--------------------------------------------",
            flush=True
        )

        print(
            "🔗 NOUVEAU BLOC",
            flush=True
        )

        print(
            "Index       :",
            block["block_index"],
            flush=True
        )

        print(
            "Machine     :",
            block.get("machine"),
            flush=True
        )

        print(
            "Sequence    :",
            block.get("sequence"),
            flush=True
        )

        print(
            "Node        :",
            block["node_id"],
            flush=True
        )

        print(
            "Événement   :",
            block["event_type"],
            flush=True
        )

        print(
            "Criticité   :",
            block["criticity"],
            flush=True
        )

        print(
            "Data hash   :",
            block["data_hash"],
            flush=True
        )

        print(
            "Prev hash   :",
            block["previous_hash"],
            flush=True
        )

        print(
            "Block hash  :",
            block["block_hash"],
            flush=True
        )

        print(
            "--------------------------------------------",
            flush=True
        )

        return jsonify({

            "success":
                True,

            "block":
                block

        })

    except Exception as e:

        print(
            f"❌ Erreur Blockchain : {e}",
            flush=True
        )

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ============================================================
# AFFICHAGE BLOCKCHAIN
# ============================================================

@app.route(
    "/chain",
    methods=["GET"]
)
def get_chain():

    conn = get_db()

    try:

        rows = conn.execute(
            """
            SELECT *
            FROM blocks
            ORDER BY block_index ASC
            """
        ).fetchall()

        chain = [
            dict(row)
            for row in rows
        ]

        return jsonify({

            "length":
                len(chain),

            "chain":
                chain

        })

    finally:

        conn.close()


# ============================================================
# VERIFICATION INTEGRITE
# ============================================================

@app.route(
    "/verify",
    methods=["GET"]
)
def verify_chain():

    conn = get_db()

    try:

        rows = conn.execute(
            """
            SELECT *
            FROM blocks
            ORDER BY block_index ASC
            """
        ).fetchall()

    finally:

        conn.close()

    if not rows:

        return jsonify({

            "valid":
                False,

            "message":
                "Blockchain vide"
        })

    # --------------------------------------------------------
    # Premier bloc
    # --------------------------------------------------------

    first = rows[0]

    if first["block_index"] != 0:

        return jsonify({

            "valid":
                False,

            "message":
                "Le premier bloc doit être le bloc Genesis"
        })

    # --------------------------------------------------------
    # Vérification bloc par bloc
    # --------------------------------------------------------

    for i, row in enumerate(rows):

        block = block_for_hash(
            row
        )

        calculated_hash = calculate_hash(
            block
        )

        # ----------------------------------------------------
        # Vérification hash
        # ----------------------------------------------------

        if calculated_hash != row["block_hash"]:

            return jsonify({

                "valid":
                    False,

                "message":
                    f"Bloc {row['block_index']} modifié",

                "expected_hash":
                    row["block_hash"],

                "calculated_hash":
                    calculated_hash
            })

        # ----------------------------------------------------
        # Vérification index
        # ----------------------------------------------------

        if i > 0:

            previous_block = rows[
                i - 1
            ]

            expected_index = (
                int(
                    previous_block["block_index"]
                )
                + 1
            )

            if int(
                row["block_index"]
            ) != expected_index:

                return jsonify({

                    "valid":
                        False,

                    "message":
                        "Index blockchain incorrect"
                })

            # ------------------------------------------------
            # Vérification liaison
            # ------------------------------------------------

            if (
                row["previous_hash"]
                !=
                previous_block["block_hash"]
            ):

                return jsonify({

                    "valid":
                        False,

                    "message":
                        (
                            "Rupture de la chaîne entre "
                            f"les blocs "
                            f"{previous_block['block_index']} "
                            f"et "
                            f"{row['block_index']}"
                        )
                })

    # --------------------------------------------------------
    # Blockchain valide
    # --------------------------------------------------------

    return jsonify({

        "valid":
            True,

        "message":
            "Blockchain intègre et valide",

        "blocks":
            len(rows),

        "genesis":
            True
    })


# ============================================================
# INITIALISATION
# ============================================================

init_db()

create_genesis_block()


# ============================================================
# SERVEUR
# ============================================================

if __name__ == "__main__":

    print("")
    print(
        "============================================"
    )
    print(
        "          BLOCKCHAIN SERVICE"
    )
    print(
        "============================================"
    )
    print(
        "SHA-256       : ACTIVE"
    )
    print(
        "SQLite        : ACTIVE"
    )
    print(
        "Genesis       : ACTIVE"
    )
    print(
        "API HTTP      : ACTIVE"
    )
    print(
        "Verification   : ACTIVE"
    )
    print(
        "============================================"
    )
    print("")

    app.run(
        host="0.0.0.0",
        port=5000,
        threaded=True
    )
