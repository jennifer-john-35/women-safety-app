# 🌍 AI Women Safety System

A real-time women safety application built with Python and Streamlit. It predicts location risk using machine learning, allows incident reporting, sends SOS email alerts to emergency contacts, and supports a background hotkey trigger for instant help — no need to open the app.

## Features

- 🔐 Secure login/register with bcrypt password hashing
- 🗺️ Risk heatmap of high-danger locations worldwide
- 🧠 ML-based risk prediction (RandomForest) by location and time of day
- 🚨 Incident reporting that dynamically updates risk scores
- 🆘 SOS email alerts sent instantly to emergency contacts
- ⚡ Background hotkey trigger — press `Ctrl+Shift+S` anytime to send SOS
- 🛣️ Safe route analyzer between two locations
- 📞 Emergency contact management (name, phone, email)

## Tech Stack

Python, Streamlit, scikit-learn, smtplib, folium, bcrypt, geopy, joblib

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in your Gmail credentials:
   ```
   SMTP_USER=youremail@gmail.com
   SMTP_PASSWORD=your_gmail_app_password
   ```
   > Gmail requires an [App Password](https://myaccount.google.com/apppasswords) — not your regular password.

3. Run the app:
   ```bash
   streamlit run app.py
   ```

4. Optionally, run the hotkey listener in a separate terminal:
   ```bash
   python hotkey_sos.py --user <your_username>
   ```
   Then press `Ctrl+Shift+S` from anywhere to trigger SOS instantly.

## Project Structure

```
app.py                  # Streamlit UI entry point
auth.py                 # User authentication
risk_engine.py          # ML risk prediction model
incident_manager.py     # Incident reporting + hotspot updates
contact_manager.py      # Emergency contact management
sos_service.py          # SOS email alerting
route_analyzer.py       # Safe route analysis
hotkey_sos.py           # Background hotkey SOS trigger
config.py               # Environment variable loader
.env.example            # Template for credentials
```
