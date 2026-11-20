# 📁 File Sharing Web App

A self-hosted file sharing application built with **Django**. Upload a file, get a unique **share code** (and link), and send it to whoever needs the file — no email attachments, no public folders.

Administrators control who may upload and download, manage user accounts, review a full audit log (who, what, when, from which IP address), and clean up old files.

---

## Table of contents

- [Features](#features)
- [User roles](#user-roles)
- [Requirements](#requirements)
- [Installation](#installation)
- [Running the application](#running-the-application)
- [How to use it](#how-to-use-it)
- [Configuration](#configuration)
- [Cleaning up old files](#cleaning-up-old-files)
- [Running in production](#running-in-production)
- [Running the tests](#running-the-tests)
- [Project structure](#project-structure)
- [License](#license)

---

## Features

| Area | What it does |
|---|---|
| **Upload** | Upload one or many files at once (up to 20 per upload, size limit configurable). Each file gets its own share code. |
| **Share codes** | Every file receives a random 22‑character code (about 128 bits of randomness, so codes cannot be guessed) and a share link like `https://your-site/f/<code>/`. |
| **Download** | Open the share link, or paste the code (or the whole link) on the *Download* page. |
| **Access control** | An admin decides whether uploads and downloads need a signed‑in account, or are open to anyone. Upload and download are set separately. |
| **Audit log** | Every upload, download, invalid code, delete, cleanup, settings change and user change is logged with time, file name, share code, size, user name and **IP address**. Visitors who aren't signed in are logged as **N/A**. |
| **Pagination & search** | *My files*, *All files*, *Activity log* and *Users* are paginated and searchable; filters are kept when changing pages. |
| **Brute‑force protection** | After 10 wrong codes from the same IP address, that address is locked out for 60 seconds. Each further wrong code doubles the lockout (max 24 hours). |
| **Cleanup** | Admins can preview and delete files older than *N* days from the admin panel, or run it automatically with a scheduled command. |
| **Safe storage** | Files are stored under random names and are never served directly. Every download goes through a view that checks access and writes a log entry. |
| **Light & dark mode** | The interface follows the operating system's theme and works on mobile. |

## User roles

| Capability | Anonymous visitor | General user | Admin |
|---|:---:|:---:|:---:|
| Upload files | only if *public upload* is on | ✅ | ✅ |
| Download with a share code | only if *public download* is on | ✅ | ✅ |
| See and delete own uploads (*My files*) | – | ✅ | ✅ |
| See and delete **all** files | – | – | ✅ |
| View the activity log | – | – | ✅ |
| Create / edit / disable / delete admins and general users | – | – | ✅ |
| Change access settings | – | – | ✅ |
| Clean up old files | – | – | ✅ |

There is no public sign‑up page: accounts are created by an admin. To keep you from locking yourself out, admins cannot demote, disable or delete their own account, and the last remaining admin cannot be removed.

---

## Requirements

- **Python 3.12 or newer** (Django 6.1 requires it)
- `pip`
- Git (to clone the repository)

No external database server is needed — the app uses SQLite out of the box.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/abyshergill/File-Sharing-Web-App.git
cd File-Sharing-Web-App
git checkout django-rewrite
```

### 2. Create and activate a virtual environment

macOS / Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

Windows (PowerShell):

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create the database

```bash
python manage.py migrate
```

This creates `data/db.sqlite3`. Uploaded files will be stored in `data/uploads/`.

### 5. Create the first admin account

```bash
python manage.py createsuperuser
```

Enter a username, an optional email and a password. This account is automatically an **Admin**.

## Running the application

```bash
python manage.py runserver
```

Open **http://127.0.0.1:8000** in your browser and sign in with the admin account you just created.

To make it reachable from other devices on your network:

```bash
DJANGO_ALLOWED_HOSTS=192.168.1.20,localhost python manage.py runserver 0.0.0.0:8000
```

(Replace `192.168.1.20` with your computer's IP address.)

---

## How to use it

### As an admin — first‑time setup

1. Sign in and click **Admin panel** in the top bar.
2. **Access settings** — choose the mode:
   - *Both off (default):* only signed‑in users can upload and download.
   - *Public upload on:* anyone can upload without an account.
   - *Public download on:* anyone with a share code can download without an account.
3. **Users** — click **New general user** or **New admin** to create accounts. From the same list you can edit a user's role, disable an account, reset a password or delete a user (their files are kept).

### Uploading a file

1. Click **Upload** and choose one or more files.
2. After uploading you'll see a table with each file's **share code** and **Copy link** buttons.
3. Send the code or link to the person who needs the file. **Save it** — the code is the only way to reach the file.

Signed‑in users can find all their uploads later under **My files**.

### Downloading a file

- Open the share link directly, **or**
- Go to **Download**, paste the code (or the full link) and click **Find file**, then **Download**.

### Monitoring and maintenance (admin)

| Page | Purpose |
|---|---|
| **Dashboard** | Totals: files stored, storage used, users, and uploads / downloads / invalid codes in the last 7 days, plus the latest activity. |
| **All files** | Every file with uploader, uploader IP, download count and last download time. Search by name, code, user or IP. Delete any file. |
| **Activity log** | Full audit trail. Filter by action (upload, download, invalid code, …) and search by file name, code, user or IP. |
| **Cleanup** | Enter a number of days, preview which files would be removed, then confirm. |

The built‑in Django admin is also available at `/django-admin/` for admins who want direct database access.

### Main URLs

| URL | Page |
|---|---|
| `/` | Home |
| `/upload/` | Upload files |
| `/find/` | Enter a share code |
| `/f/<code>/` | File details and download button |
| `/my-files/` | Your uploads |
| `/panel/` | Admin panel |
| `/accounts/users/` | User management |
| `/accounts/login/` | Sign in |

---

## Configuration

All settings are optional and read from environment variables.

| Variable | Default | Purpose |
|---|---|---|
| `DJANGO_DEBUG` | `true` | Set to `false` in production. |
| `DJANGO_SECRET_KEY` | development key | **Required** when `DJANGO_DEBUG=false`. Use a long random string. |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,[::1]` | Comma‑separated host names the site is served on. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | – | Full origins for HTTPS deployments, e.g. `https://files.example.com`. |
| `DJANGO_TIME_ZONE` | `UTC` | Time zone used when showing dates, e.g. `Asia/Kolkata`. |
| `FILESHARE_STORAGE_DIR` | `data/uploads` | Folder where uploaded files are stored. |
| `FILESHARE_MAX_UPLOAD_MB` | `100` | Maximum size of a single file, in MB. |
| `FILESHARE_PAGE_SIZE` | `20` | Rows per page in all lists. |
| `FILESHARE_MAX_FAILED_ATTEMPTS` | `10` | Wrong codes allowed from one IP before lockout. |
| `FILESHARE_LOCKOUT_BASE_SECONDS` | `60` | Length of the first lockout; doubles with each further wrong code. |
| `FILESHARE_TRUST_X_FORWARDED_FOR` | `false` | Turn on **only** when running behind your own reverse proxy (nginx, Caddy, …) so the visitor's real IP is logged. Without a proxy, leave it off — otherwise visitors could fake their IP address. |

Example:

```bash
export DJANGO_TIME_ZONE=Asia/Kolkata
export FILESHARE_MAX_UPLOAD_MB=500
python manage.py runserver
```

## Cleaning up old files

From the browser: **Admin panel → Cleanup**.

From the command line:

```bash
# Show how many files would be deleted
python manage.py cleanup_old_files --days 30 --dry-run

# Delete files uploaded more than 30 days ago
python manage.py cleanup_old_files --days 30
```

To run it automatically every night at 03:00 (Linux/macOS cron):

```
0 3 * * * cd /path/to/File-Sharing-Web-App && venv/bin/python manage.py cleanup_old_files --days 30
```

Deleted files are removed from disk and from the database. Their entries in the activity log are kept.

## Running in production

The `runserver` command is for development only. For a real deployment:

1. Set the environment variables:
   ```bash
   export DJANGO_DEBUG=false
   export DJANGO_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(50))')"
   export DJANGO_ALLOWED_HOSTS=files.example.com
   export DJANGO_CSRF_TRUSTED_ORIGINS=https://files.example.com
   export FILESHARE_TRUST_X_FORWARDED_FOR=true   # only because nginx sits in front
   ```
2. Collect static files: `python manage.py collectstatic`
3. Run with an application server, e.g.
   `pip install gunicorn && gunicorn config.wsgi:application --bind 127.0.0.1:8000`
4. Put **nginx** (or another web server) in front to handle HTTPS and serve `/static/` from the `staticfiles/` folder. Set nginx's `client_max_body_size` to at least `FILESHARE_MAX_UPLOAD_MB`.
5. If you run several gunicorn workers, switch `CACHES` in `config/settings.py` to Redis or Memcached so the wrong‑code lockout is shared between workers.
6. Back up the `data/` folder (database + uploaded files) regularly.

## Running the tests

```bash
python manage.py test
```

The tests cover access modes, N/A + IP logging, share codes, lockout, file permissions, pagination, user management and cleanup.

## Project structure

```
File-Sharing-Web-App/
├── config/                     # Django project: settings, root URLs, WSGI/ASGI
├── accounts/                   # Custom User model (Admin / General role)
│   ├── models.py
│   ├── views.py                # User management for admins
│   ├── forms.py
│   └── decorators.py           # @admin_required
├── sharing/                    # File sharing app
│   ├── models.py               # SharedFile, ActivityLog, SiteSettings
│   ├── services.py             # IP detection, logging, access rules, lockout, cleanup
│   ├── views.py                # Upload, find, file detail, download, my files
│   ├── panel_views.py          # Admin panel: dashboard, files, logs, settings, cleanup
│   ├── forms.py
│   └── management/commands/
│       └── cleanup_old_files.py
├── templates/                  # HTML templates
├── static/css/app.css          # Styles (light & dark)
├── data/                       # Created at runtime: db.sqlite3 + uploads/ (git‑ignored)
├── manage.py
├── requirements.txt
├── LICENSE.txt
└── README.md
```

## License

This project is licensed under the **MIT License** — see [LICENSE.txt](LICENSE.txt) for the full text.

Copyright (c) 2025 K.S. GILL (Aby)
