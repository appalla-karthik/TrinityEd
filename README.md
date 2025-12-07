# TrinityEd – AI-based Dropout Prediction & Counseling System

TrinityEd is an AI-powered web application developed for **Smart India Hackathon 2025 (SIH 25)** by **Team BytesOfHope**.  
The system helps educational institutions **identify at-risk students early** and enables **timely counseling and intervention** using data-driven insights.

*Live Demo:*  https://trinityed.onrender.com/
---

## 🚀 Features

- Early dropout risk prediction using **Machine Learning**
- Unified dashboard for **attendance, marks, and fee data**
- Explainable ML models for transparent decision-making
- Interactive data visualization using **Chart.js**
- AI-assisted counseling support
- Automated alerts via **Email (SMTP)** and **WhatsApp API**
- Role-based access for students, mentors, and admins

---

## 🧠 Machine Learning

- Algorithms Used:
  - Logistic Regression
  - Random Forest
- Libraries:
  - Scikit-learn
  - Pandas
  - NumPy
- Purpose:
  - Trend detection
  - Anomaly spotting
  - Dropout risk scoring

---

## 🛠 Tech Stack

### Backend
- Django (Python)
- SQLite (Database)
- Scikit-learn (ML)
- OpenAI API (Counseling assistance)

### Frontend
- HTML
- Tailwind CSS
- JavaScript
- Chart.js

### Notifications & Services
- SMTP (Email alerts)
- WhatsApp API (Parent/Mentor alerts)

### Tools & Deployment
- GitHub (Version Control)
- Render / Cloud Hosting
- Gunicorn & Whitenoise

---

## 🏗️ Architecture Overview

    Client (Browser)
    ↓
    Django Web Server
    ↓
    ML Models (Scikit-learn)
    ↓
    Database (SQLite)
    ↓
    External APIs (OpenAI, Email, WhatsApp)


---

## 📦 Installation & Setup

1. Clone the repository
   ```bash
   git clone https://github.com/your-username/trinityed.git
   cd trinityed
   ```
2. Create and activate a virtual environment
   ```
   python -m venv venv
   source venv/bin/activate
   ```
   # On Windows:
   ```
   venv\Scripts\activate
   ```
3. Install dependencies
   ```
   pip install -r requirements.txt
   ```
4. Run database migrations
   ```
   python manage.py migrate
   ```
5. Start the development server
    ```
    python manage.py runserver
    ```
