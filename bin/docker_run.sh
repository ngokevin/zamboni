# Startup script for running Zamboni under Docker.

# Check for mysql being up and running.
mysqladmin -u root --host mysql_1 --silent --wait=30 ping || exit 1

# Check database exists. If not create it first.
mysql -u root --host mysql_1 -e 'use zamboni;'
if [ $? -ne 0 ]; then
    echo "Zamboni database doesn't exist. Let's create it"
    mysql -u root --host mysql_1 -e 'create database zamboni'
    echo "Syncing db..."
    python manage.py syncdb --noinput
    echo "Initialising data..."
    python manage.py loaddata init
    echo "Jumping migrations forward to the most recent."
    schematic migrations/ --fake
fi

python manage.py runserver 0.0.0.0:2600
