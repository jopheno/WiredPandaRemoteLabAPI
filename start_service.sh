SCRIPT=$(readlink -f "$0")
CPATH=$(dirname "$SCRIPT")

echo "> Changing directory to: ${CPATH}"

cd ${CPATH}

echo "> Activating Virtual Environment..."

# Activating VirtualEnv
source venv/bin/activate

echo "> Virtual Environment Activated!"

# Starting web and TCP service
python app.py
