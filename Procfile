web: gunicorn atlas.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 1 --threads ${GUNICORN_THREADS:-8} --timeout ${GUNICORN_TIMEOUT:-300} --access-logfile -
