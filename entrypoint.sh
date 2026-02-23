pip install --no-cache-dir -r requirements.txt
if [ "${USE_POSTGRES:-1}" = "1" ]; then
  python scripts/init_db.py
fi
uvicorn main:app --host 0.0.0.0 --port 8080
