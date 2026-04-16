#!/bin/bash

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# If a command is passed to the container, run it.
# Otherwise, start Gunicorn.
if [ $# -gt 0 ]; then
    echo "Executing command: $@"
    exec "$@"
else
    echo "Starting gunicorn with 3 workers..."
    exec gunicorn --bind 0.0.0.0:8000 --workers 3 Learning.wsgi:application
fi
