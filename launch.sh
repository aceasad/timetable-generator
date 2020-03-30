source venv/bin/activate
kill -9 $(lsof -i:8000 -t) 2> /dev/null
gunicorn --bind 0.0.0.0:8000 wsgi:app --timeout 100 --workers 2 &