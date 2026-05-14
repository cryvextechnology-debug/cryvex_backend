#!/bin/bash
echo "--- Cryvex Security Check ---"

# 1. Check for vulnerable dependencies
echo "[1/2] Running pip-audit..."
if command -v pip-audit &> /dev/null
then
    pip-audit
else
    echo "pip-audit not found. Install it with 'pip install pip-audit'."
fi

echo ""

# 2. Static Analysis for Security Pitfalls
echo "[2/2] Running Bandit static analysis..."
if command -v bandit &> /dev/null
then
    bandit -r . -ll
else
    echo "bandit not found. Install it with 'pip install bandit'."
fi

echo "--- Check Complete ---"
