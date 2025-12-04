# 🚀 Task Management System

A comprehensive Django web application designed to manage organizational tasks and employee complaints efficiently. Features a responsive dashboard, automated reminders, and role-based access control.

## ✨ Key Features

* **Task Management:** Create, assign, and track tasks with due dates, tags, and sub-steps.
* **Complaint Portal:** Dedicated workflow for reporting and resolving internal issues (IT, HR, etc.).
* **Smart Dashboard:** Visual KPIs for task progress and complaint resolution stats.
* **Notifications:** Automated email reminders and in-app alerts for upcoming deadlines.
* **Security:** Role-Based Access Control (RBAC) and secure environment variable management.
* **Bulk Import:** Custom management command to import users from CSV/Excel.

## 🛠️ Tech Stack

* **Backend:** Django 5, Python 3.12
* **Frontend:** HTML5, Tailwind CSS (CDN), Alpine.js
* **Database:** SQLite (Dev) / Configurable for PostgreSQL
* **Utilities:** Pandas (Data Import), Whitenoise (Static Files)

## ⚙️ Installation & Setup

1.  **Clone the repository**
    ```bash
    git clone [https://github.com/B-Nadir/Task-Manager.git](https://github.com/B-Nadir/Task-Manager.git)
    cd Task-Manager
    ```

2.  **Create and Activate Virtual Environment**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Mac/Linux
    source venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**
    Create a `.env` file in the root directory (same level as `manage.py`) and add your secrets:
    ```ini
    DEBUG=True
    SECRET_KEY=your-secret-key-here
    EMAIL_HOST_USER=your-email@gmail.com
    EMAIL_HOST_PASSWORD=your-app-password
    ```

5.  **Run Migrations**
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

6.  **Create Superuser**
    ```bash
    python manage.py createsuperuser
    ```

7.  **Run Server**
    ```bash
    python manage.py runserver
    ```

## 📦 Bulk User Import

To import users from a CSV file (columns: Login ID, First Name, Last Name, Email, Password, Role):

```bash
python manage.py import_users users.csv
