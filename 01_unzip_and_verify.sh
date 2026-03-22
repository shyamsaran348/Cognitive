#!/bin/bash

# 01_unzip_and_verify.sh - Unzip datasets and verify structure

BASE_DIR="/Users/shyam/Desktop/cognitive_project"

echo "Unzipping ADReSS 2020..."
cd "$BASE_DIR/adress2020"
# unzip -q ADReSS-IS2020-train.zip
# unzip -q ADReSS-IS2020-test.zip
# Note: User says they are already unzipped in adress2020/ADReSS-IS2020-data
# But the original zips are still there. We verify the directory exists.
if [ -d "ADReSS-IS2020-data" ]; then
    echo "[OK] ADReSS data directory exists."
else
    echo "[!] ADReSS data folder missing. Unzipping..."
    unzip -q ADReSS-IS2020-train.zip
    unzip -q ADReSS-IS2020-test.zip
fi

echo "Verifying TAUKADIAL..."
cd "$BASE_DIR/taukadial"
if [ -d "TAUKADIAL-24" ]; then
    echo "[OK] TAUKADIAL directory exists."
else
    echo "[!] TAUKADIAL directory missing. Please unzip TAUKADIAL-24.tgz files."
    # tar -xzf TAUKADIAL-24-train.tgz
    # tar -xzf TAUKADIAL-24-test.tgz
fi

echo "Structure check complete."
