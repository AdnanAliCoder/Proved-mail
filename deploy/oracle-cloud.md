# ProveMails on Oracle Cloud

This guide assumes an Ubuntu Oracle Cloud VM and PostgreSQL reachable from that VM. The Django application can use local SQLite for a quick laptop test, but production should set DATABASE_URL to a private PostgreSQL endpoint and keep its credentials only in the server environment.

## 1. Prepare Ubuntu

Install Python, venv support, Git and build tools:

    sudo apt update
    sudo apt install -y python3-venv python3-pip git build-essential libpq-dev nginx

Clone your repository and enter it:

    git clone https://github.com/AdnanAliCoder/Proved-mail.git
    cd Proved-mail

Create and activate a virtual environment, then install packages:

    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt

## 2. Configure environment

Create a private .env file from .env.example. Use a long random Django secret, your real domain, the correct ALLOWED_HOSTS, and the administrator email. Set DJANGO_DEBUG=False in production. Generate a random setup key and keep it private; after the administrator signs up, remove PROVEDMAILS_ADMIN_SIGNUP_KEY from the environment.

For PostgreSQL, set DATABASE_URL using the connection URL supplied for your database. Restrict the database to trusted private network sources; do not expose PostgreSQL to the public internet. Set DATABASE_SSL_REQUIRE=True when your database provider requires TLS.

Do not commit .env, database passwords, Google snippets containing secrets, or lead files to GitHub.

## 3. Initialize database and static files

    source .venv/bin/activate
    python manage.py check --deploy
    python manage.py migrate
    python manage.py collectstatic --noinput

For the first start-up, ensure the public site URL points to the deployed HTTPS hostname. Check the allowed host and CSRF origins before attempting login.

## 4. Create the one-time administrator

Open /admin-signup/ in the browser. Enter the exact address configured in PROVEDMAILS_ADMIN_EMAIL, the private PROVEDMAILS_ADMIN_SIGNUP_KEY, your name, and a strong password. Once the superuser exists, public registration is disabled automatically. The password is stored using Django's password hashing, not plain text.

After successful setup, remove PROVEDMAILS_ADMIN_SIGNUP_KEY from the production environment and restart the services. Keep the administrator email configured for documentation only; no more accounts can be registered through the public form.

## 5. Run the web application and the background worker

The web process serves Django pages and queues uploads. A separate single worker process does the heavy verification. This separation lets the web app continue to respond while long batches are running.

For a quick foreground smoke test:

    gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 2 --threads 4
    python manage.py process_jobs --poll-seconds 2

Configure the commands as separate systemd services for production. Run only one queue worker unless you add database locking/claiming for multiple workers. Use Nginx as a reverse proxy, configure HTTPS, and proxy to Gunicorn on localhost port 8000.

Example web service command:

    /home/ubuntu/Proved-mail/.venv/bin/gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 2 --threads 4 --timeout 120

Example worker command:

    /home/ubuntu/Proved-mail/.venv/bin/python /home/ubuntu/Proved-mail/manage.py process_jobs --poll-seconds 2

Use your actual deployment path in service files, then enable them with systemctl. Add Nginx rules so /static/ is served from STATIC_ROOT and /media/ from MEDIA_ROOT, with access restricted as appropriate. Protect media/uploads from public directory listing.

## 6. Important SMTP limitation

The verification engine uses DNS/MX checks and attempts SMTP recipient checks on port 25 where available. Many residential ISPs, cloud networks and mail providers block or throttle outbound SMTP. If port 25 is blocked, the engine deliberately reports unconfirmed addresses as unknown rather than fabricating a valid result. Test port 25 from the actual worker VM before relying on mailbox-level checks.

## 7. Large files and operations

Uploads are limited to 50 MB and 100,000 rows per job. Start by testing 100–200 rows, then larger batches. Processing speed depends on DNS latency, SMTP rate limits, catch-all behavior and network restrictions. The background worker stores results in the database in bulk; use a database with enough disk and memory for both the original file and verification rows.

Back up the database and media directory together. Add log rotation, firewall rules, OS security updates, and a process monitor before production use.
