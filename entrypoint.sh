#!/bin/bash

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Start Gunicorn
echo "Starting gunicorn..."
exec gunicorn --bind 0.0.0.0:8000 --workers 3 Learning.wsgi:application
