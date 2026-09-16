#!/bin/bash

LOG=~/PFA_CyberIA/markov_analysis/disponibilite_cycles.log

echo "===== TEST DISPONIBILITE BLOCKCHAIN =====" > "$LOG"
date -Is >> "$LOG"

for i in 1 2 3 4 5
do
    echo "===== CYCLE $i =====" | tee -a "$LOG"

    echo "NORMAL_START $(date -Is)" | tee -a "$LOG"
    sleep 30

    echo "BLOCKCHAIN_STOP $(date -Is)" | tee -a "$LOG"
    docker stop blockchain >> "$LOG" 2>&1

    sleep 10

    echo "BLOCKCHAIN_START $(date -Is)" | tee -a "$LOG"
    docker start blockchain >> "$LOG" 2>&1

    sleep 30
done

echo "===== FIN TEST =====" | tee -a "$LOG"
date -Is >> "$LOG"
