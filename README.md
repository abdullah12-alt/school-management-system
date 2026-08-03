# Luminead — Multi-Tenant School Management SaaS

A production-ready, multi-tenant Luminead built with Django and SQLite (PostgreSQL-ready via `DATABASE_URL`). Each school is fully isolated at the query level. A single shared codebase serves unlimited schools.

---

## Features

- **Multi-tenant isolation** — every school's data is siloed; no cross-tenant data leaks
- **Role-based access control** — School Admin, Teacher, Accountant, Librarian, Staff, Student, Parent
- **Academic management** — ClassRooms, Sections, Subjects, Timetables
- **Attendance** — Teachers mark daily attendance; Students/Parents view history
- **Exams & Grading** — Create exams, enter marks, view report cards
- **Fee & Finance** — Accountants manage invoices; Students/Parents view their fee status
- **Deployment-ready** — Whitenoise static files, `DATABASE_URL` env var, Procfile for Railway/Render

---

## Local Setup

### Prerequisites
- Python 3.10+
- pip
- A PostgreSQL database (e.g. [Neon](https://neon.tech)) — or leave `DATABASE_URL` unset to use local SQLite

### Steps

```bash
# 1. Clone the repo
git clone <repo-url>
cd school-managment-system

# 2. Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r school-saas/requirements.txt

# 4. Navigate to the Django project
cd school-saas

# 5. Configure database (copy example and set your Neon URL)
copy .env.example .env
# Edit .env and set DATABASE_URL=postgresql://...?sslmode=require

# 6. Apply migrations
python manage.py migrate

# 7. Seed demo data (creates 2 schools + all demo accounts)
python manage.py seed_demo_data

# 8. Run the development server
python manage.py runserver
```

Then open http://127.0.0.1:8000 in your browser.

---

## Demo Login Credentials

| Role               | Email                       | Password      | School           |
|--------------------|-----------------------------|---------------|------------------|
| Platform Super Admin | admin@Luminead.com       | admin123456   | —                |
| School Admin       | admin@greenwood.edu         | greenwood123  | Greenwood Academy |
| Teacher            | james.w@greenwood.edu       | teacher123    | Greenwood Academy |
| Accountant         | mark.a@greenwood.edu        | account123    | Greenwood Academy |
| Librarian          | lib.a@greenwood.edu         | library123    | Greenwood Academy |
| Staff              | staff.a@greenwood.edu       | staff123      | Greenwood Academy |
| Parent             | parent.a@greenwood.edu      | parent123     | Greenwood Academy |
| Student            | student.a@greenwood.edu     | student123    | Greenwood Academy |
| School Admin       | admin@sunrise.edu           | sunrise123    | Sunrise School    |
| Student            | student.b@sunrise.edu       | student123    | Sunrise School    |

---

## Environment Variables

For production, set these environment variables:

| Variable         | Description                                  | Default                        |
|------------------|----------------------------------------------|--------------------------------|
| `SECRET_KEY`     | Django secret key                            | Insecure dev key (change this!)|
| `DEBUG`          | Enable debug mode (`True` / `False`)         | `True`                         |
| `ALLOWED_HOSTS`  | Comma-separated allowed hosts                | `*`                            |
| `DATABASE_URL`   | Full database URL (e.g. PostgreSQL)          | SQLite (local `db.sqlite3`)    |

### Example `.env` (for local reference)
```bash
SECRET_KEY=your-super-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgres://user:password@host:5432/dbname
```

---

## Deploy to Railway / Render

### Railway

1. Push your code to GitHub.
2. Create a new Railway project and connect your repository.
3. Set the **Root Directory** to `school-saas`.
4. Add the following **environment variables** in Railway dashboard:
   - `SECRET_KEY` = (generate a secure random key)
   - `DEBUG` = `False`
   - `ALLOWED_HOSTS` = `<your-railway-domain>.up.railway.app`
   - `DATABASE_URL` = (Railway auto-provides this if you add a PostgreSQL plugin)
5. Railway will detect the `Procfile` and run: `gunicorn config.wsgi:application`
6. After first deploy, run migrations via Railway's shell:
   ```bash
   python manage.py migrate
   python manage.py seed_demo_data
   ```

### Render

1. Create a new **Web Service** pointing to your GitHub repo.
2. Set **Root Directory**: `school-saas`
3. Set **Build Command**: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
4. Set **Start Command**: `gunicorn config.wsgi:application`
5. Add environment variables (same as above).

---

## Generating a Secure Secret Key

```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## Running Tests

```bash
cd school-saas
python manage.py test core
```

All tests cover:
- Role-based access control (403/404 enforcement)
- URL-tampering protection (other students' IDs)
- Attendance DB-level uniqueness constraint
- Multi-tenant isolation across 2 demo schools
