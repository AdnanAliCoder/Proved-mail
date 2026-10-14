# ProveMails

ProveMails is a private, administrator-managed email verification website. It uses HTML, CSS and vanilla JavaScript for the interface, Django/Python for the web backend, and the existing verification engine in the verifier package.

## Features

- A new responsive ProveMails brand and public landing page.
- A private workspace with CSV/XLSX upload, progress polling, cancellation, job history and status counts.
- Existing verification signals retained: syntax, DNS/MX, disposable and role addresses, SPF/DMARC, typo suggestions, catch-all behavior, and SMTP recipient checks where the network permits them.
- Separate Valid, Invalid, Risky and Unknown result categories. Unknown means the mailbox could not be confirmed; it should not automatically be treated as invalid.
- Download all results or filter by status as CSV or XLSX. The input columns are retained and verification columns are added.
- A one-time administrator bootstrap page. The permitted admin email and setup key come from the server environment. After the first administrator is created, public registration closes.
- Admin settings for website branding, title/description metadata, Google AdSense code, Google Analytics code, and additional head snippets.
- Google Search Console HTML verification-file upload that serves the verified file name from the website root.
- Editable About, Privacy Policy, Terms of Use and Contact pages, with page-specific SEO titles and descriptions.
- Dynamic robots.txt and sitemap.xml.
- SQLite by default for local testing; PostgreSQL via DATABASE_URL for an Oracle Cloud VM.
- A separate background worker so long verification batches do not block normal website requests.

## Windows 10: run locally

Install Python 3.11 or a compatible newer Python and Git. Open PowerShell in the repository folder.

    py -3.11 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    Copy-Item .env.example .env

Open .env in a text editor and set these values before the first run:

- DJANGO_SECRET_KEY — replace the example with a long, random secret.
- DJANGO_DEBUG=True for local development.
- ALLOWED_HOSTS=127.0.0.1,localhost
- SITE_URL=http://127.0.0.1:8000
- PROVEDMAILS_ADMIN_EMAIL — the single email address permitted to create the admin account.
- PROVEDMAILS_ADMIN_SIGNUP_KEY — a private, hard-to-guess one-time setup key.

Leave DATABASE_URL empty to use a local SQLite database.

Run database migrations and start Django:

    python manage.py migrate
    python manage.py check
    python manage.py runserver

Open http://127.0.0.1:8000 in your browser. The public site is served by Django; do not use Python's static http.server for the main app.

In a second PowerShell window, change to the same project directory, activate the virtual environment, and start the queue worker:

    .\.venv\Scripts\Activate.ps1
    python manage.py process_jobs --poll-seconds 2

The worker must remain running while verification jobs are being processed. Stop it with Ctrl+C when finished.

## Create the only administrator account

Open /admin-signup/ on the local site. Enter the exact PROVEDMAILS_ADMIN_EMAIL configured in .env, the PROVEDMAILS_ADMIN_SIGNUP_KEY, your name and a strong password. The password is stored using Django's password hashing, not plain text.

After the account is created, the public sign-up page closes automatically. Remove PROVEDMAILS_ADMIN_SIGNUP_KEY from .env after the first setup if you do not need to recreate the database. Never commit .env or share its key.

If you delete the local database and need to bootstrap again, configure a new setup key and run migrations again. Keep database backups secure.

## Configure website settings

Sign in with the administrator account, then open Admin panel.

- Site & SEO settings: edit the site name, tagline, public site URL, page title and description.
- Google AdSense: paste the official snippet for a property you control.
- Google Analytics: paste the official tag/snippet for your property.
- Extra head code: use for additional scripts or verification snippets when needed.
- Search Console: upload the original Google HTML verification file. It must retain a name like google123abc.html and include Google's verification token.
- Public pages: update each page's content, SEO title, meta description and publication state.

Only the superuser can reach these controls. These editable snippets are rendered as administrator-supplied HTML; only paste code from sources you trust.

## Oracle Cloud production deployment

See deploy/oracle-cloud.md for Ubuntu, PostgreSQL, Gunicorn, the separate worker and reverse-proxy setup. In production:

1. Set DJANGO_DEBUG=False, a strong DJANGO_SECRET_KEY, correct ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS.
2. Set SITE_URL to the final HTTPS hostname.
3. Set DATABASE_URL to the PostgreSQL connection URL and enable database TLS if required.
4. Run python manage.py migrate and python manage.py collectstatic --noinput.
5. Run Gunicorn as the web service and python manage.py process_jobs --poll-seconds 2 as one separate worker service.
6. Configure HTTPS through Nginx or another reverse proxy and secure the media directory and database.
7. Create the one-time admin account, then remove the setup key and restart the services.

For this app the term “Oracle Cloud database” refers to a database reachable from the Oracle Cloud VM. PostgreSQL is the configured production database backend. If you specifically use Oracle Database (the Oracle SQL database product), a separate Oracle database driver and settings configuration are needed.

## Batch-size and verification notes

- Current upload cap: 50 MB per file.
- Current row cap: 100,000 leads per batch.
- Test 100–200 rows first, then gradually increase the batch size.
- Speed depends on DNS, provider throttling, catch-all behavior, SMTP availability and network policy.
- Most residential networks and some cloud providers block outbound SMTP port 25. When live SMTP checks are not possible, the engine reports unconfirmed addresses as Unknown instead of guessing.
- A Valid result is not a guarantee of delivery; providers can change behavior at any time.
- The background worker should run as a single process for this starter version.

## Original engine and license status

The original verifier package and standalone Flask/HTML files have been retained in the repository so the verification logic is not discarded. The Django app is the primary website and does not depend on the old Flask API running on port 5050. Review NOTICE.md before redistribution: the initial imported source listing did not contain an upstream LICENSE file, so no upstream license has been assumed.
