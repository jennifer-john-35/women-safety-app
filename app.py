"""
app.py — Streamlit entry point for the AI Women Safety System.

All business logic is delegated to service modules. This file only handles
UI rendering and session state management.
"""
import os
import json
from datetime import datetime

import streamlit as st
import folium
from streamlit_folium import st_folium

import auth
import risk_engine
import incident_manager
import sos_service
import contact_manager
import route_analyzer
import config


# ---------------------------------------------------------------------------
# UI helper functions
# ---------------------------------------------------------------------------

def card(content: str, border_color: str = "var(--accent)", title: str = "") -> str:
    """Return an HTML card string for st.markdown."""
    content = content if content is not None else ""
    border_color = border_color if border_color is not None else "var(--accent)"
    title = title if title is not None else ""
    title_html = f'<div style="font-weight:700;margin-bottom:0.5rem;">{title}</div>' if title else ""
    return (
        f'<div style="background:var(--bg-card);border-left:4px solid {border_color};'
        f'border-radius:var(--radius);padding:var(--padding);margin-bottom:1rem;">'
        f'{title_html}{content}</div>'
    )


def badge(label: str, color: str) -> str:
    """Return a colored pill badge HTML string. Unknown color falls back to var(--accent)."""
    label = label if label is not None else ""
    color = color if color is not None else "var(--accent)"
    return (
        f'<span style="background:{color};color:#fff;padding:0.3rem 0.9rem;'
        f'border-radius:999px;font-weight:700;font-size:1rem;">{label}</span>'
    )


def metric_card(label: str, value: str, border_color: str = "var(--accent)") -> str:
    """Return a styled metric card HTML string."""
    label = label if label is not None else ""
    value = value if value is not None else ""
    border_color = border_color if border_color is not None else "var(--accent)"
    return (
        f'<div style="background:var(--bg-card);border-top:4px solid {border_color};'
        f'border-radius:var(--radius);padding:var(--padding);text-align:center;">'
        f'<div style="font-size:2rem;font-weight:800;color:var(--text-primary);">{value}</div>'
        f'<div style="font-size:0.9rem;color:var(--text-muted);">{label}</div>'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(page_title="AI Women Safety System", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');

:root {
  --bg-primary:   #0f0f1a;
  --bg-card:      #1a1a2e;
  --accent:       #a855f7;
  --danger:       #ef4444;
  --warning:      #f97316;
  --success:      #22c55e;
  --text-primary: #f1f5f9;
  --text-muted:   #94a3b8;
  --radius:       12px;
  --padding:      1.25rem;
  --max-width:    1100px;
}

html, body, .stApp {
  background-color: var(--bg-primary) !important;
  color: var(--text-primary) !important;
  font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
}

#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { display: none; }

.block-container {
  max-width: var(--max-width);
  padding-top: 1rem;
  padding-bottom: 1rem;
}

section[data-testid="stSidebar"] {
  background-color: var(--bg-card) !important;
  padding: var(--padding);
}

.stButton > button[kind="primary"] {
  background-color: var(--accent) !important;
  border-color: var(--accent) !important;
  color: #fff !important;
}

.stTabs [data-baseweb="tab-list"] {
  gap: 0.5rem;
}
.stTabs [data-baseweb="tab"] {
  font-size: 1rem;
  padding: 0.6rem 1.2rem;
}
.stTabs [aria-selected="true"] {
  color: var(--accent) !important;
  border-bottom-color: var(--accent) !important;
}

.stTextInput > div > div > input,
.stSelectbox > div > div,
.stTextArea textarea {
  border-color: var(--accent) !important;
}

@keyframes pulse-sos {
  0%, 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.7); }
  50%       { box-shadow: 0 0 0 12px rgba(239,68,68,0); }
}

@media (max-width: 768px) {
  .stColumns { flex-direction: column !important; }
  .stColumns > div { width: 100% !important; }
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center;padding:2rem 0 1rem;">
  <h1 style="background:linear-gradient(135deg,#a855f7,#ef4444);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:2.5rem;font-weight:900;margin:0;">🌍 AI Women Safety System</h1>
  <p style="color:var(--text-muted);margin-top:0.5rem;">Powered by Machine Learning Risk Prediction Model</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Startup initialisation
# ---------------------------------------------------------------------------

@st.cache_resource
def _init_model():
    """Initialise (load or train) the ML model once per process."""
    risk_engine.initialize_model()


_init_model()

# Ensure required data files exist
for _path, _default in [
    (config.USERS_FILE, {}),
    (config.INCIDENTS_FILE, {"incidents": []}),
    (config.CONTACTS_FILE, {}),
]:
    if not os.path.exists(_path):
        with open(_path, "w", encoding="utf-8") as _f:
            json.dump(_default, _f)

# Hotspots file is self-initialising inside incident_manager.load_hotspots()

# ---------------------------------------------------------------------------
# Session state bootstrap
# ---------------------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None

# ---------------------------------------------------------------------------
# Authentication — separate Login and Register forms
# ---------------------------------------------------------------------------
if not st.session_state.user:
    st.subheader("🔐 Login")
    with st.form("login_form"):
        login_username = st.text_input("Username", key="login_username")
        login_password = st.text_input("Password", type="password", key="login_password")
        login_submitted = st.form_submit_button("Login")

    if login_submitted:
        ok, msg = auth.login_user(login_username, login_password)
        if ok:
            st.session_state.user = login_username
            st.rerun()
        else:
            st.markdown(card(msg, border_color="var(--danger)"), unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📝 Register")
    with st.form("register_form"):
        reg_username = st.text_input("Username", key="reg_username")
        reg_password = st.text_input("Password (min 8 chars)", type="password", key="reg_password")
        reg_submitted = st.form_submit_button("Register")

    if reg_submitted:
        ok, msg = auth.register_user(reg_username, reg_password)
        if ok:
            st.markdown(card(msg + " You can now log in.", border_color="var(--success)"), unsafe_allow_html=True)
        else:
            st.markdown(card(msg, border_color="var(--danger)"), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Main application — only shown when logged in
# ---------------------------------------------------------------------------
else:
    username = st.session_state.user

    with st.sidebar:
        st.markdown(f"""
        <div style="text-align:center;padding:1rem 0;">
          <div style="font-size:3rem;">👤</div>
          <div style="font-weight:700;font-size:1.1rem;color:var(--text-primary);">{username}</div>
          <div style="font-size:0.8rem;color:var(--text-muted);">Logged in</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🚪 Logout", use_container_width=True):
            auth.logout_user()
            st.rerun()
        st.markdown("---")

    # Single SOS button at the top of the page (Requirement 5.4)
    if st.button("🆘 SOS — Send Emergency Alert", type="primary"):
        result = sos_service.trigger_sos(username, lat=0.0, lon=0.0)
        if "warning" in result:
            st.markdown(card(result["warning"], border_color="var(--warning)"), unsafe_allow_html=True)
        else:
            if result["notified"]:
                st.markdown(card("✅ SOS sent! Notified: " + ", ".join(result["notified"]), border_color="var(--success)"), unsafe_allow_html=True)
            if result["failed"]:
                st.markdown(card("Failed to notify: " + ", ".join(result["failed"]), border_color="var(--danger)"), unsafe_allow_html=True)
            if not result["notified"] and not result["failed"]:
                st.markdown(card("SOS logged. No contacts with email addresses found.", border_color="var(--accent)"), unsafe_allow_html=True)

    # Dashboard metrics
    _incidents = incident_manager._load_incidents()
    _hotspots = incident_manager.load_hotspots()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(metric_card("Total Incidents", str(len(_incidents)), "var(--accent)"), unsafe_allow_html=True)
    with col2:
        st.markdown(metric_card("High Risk Cities", str(len([h for h in _hotspots if h.get("risk", 0) > 0.7])), "var(--danger)"), unsafe_allow_html=True)
    with col3:
        st.markdown(metric_card("Active Alerts", str(len(_incidents)), "var(--warning)"), unsafe_allow_html=True)

    tabs = st.tabs([
        "🌍 Heatmap",
        "🧠 Risk Prediction",
        "🚨 Report Incident",
        "🆘 SOS",
        "📞 Contacts",
        "🛣️ Safe Route",
    ])

    # -----------------------------------------------------------------------
    # Tab 0 — Heatmap (Task 11.2)
    # -----------------------------------------------------------------------
    with tabs[0]:
        st.subheader("🔥 Top Risk Locations")
        hotspots = incident_manager.load_hotspots()
        m = folium.Map(location=[20, 0], zoom_start=2, tiles="CartoDB dark_matter")
        for h in hotspots:
            risk = h.get("risk", 0.0)
            if risk > 0.75:
                color = "red"
            elif risk >= 0.5:
                color = "orange"
            else:
                color = "green"
            folium.CircleMarker(
                location=[h["lat"], h["lon"]],
                radius=12,
                color=color,
                fill=True,
                fill_opacity=0.7,
                popup=f"{h['place']} | Risk: {round(risk, 2)}",
            ).add_to(m)
        st_folium(m, use_container_width=True, height=600)

    # -----------------------------------------------------------------------
    # Tab 1 — Risk Prediction (Task 11.3)
    # -----------------------------------------------------------------------
    with tabs[1]:
        st.subheader("🧠 Risk Prediction")
        place = st.text_input("Enter Location", key="risk_place")
        if st.button("Predict Risk"):
            if not place.strip():
                st.error("Please enter a location.")
            else:
                from incident_manager import _geocode
                lat, lon = _geocode(place)
                if lat is None:
                    lat, lon = 0.0, 0.0
                hour = datetime.now().hour
                score = risk_engine.predict_risk(lat, lon, hour)
                classification = risk_engine.classify_risk(score)

                border = "var(--danger)" if classification == "HIGH" else "var(--warning)" if classification == "MODERATE" else "var(--success)"
                st.markdown(metric_card("Risk Score", str(round(score, 2)), border), unsafe_allow_html=True)
                if classification == "HIGH":
                    st.markdown(badge("🔴 HIGH RISK AREA", "#ef4444"), unsafe_allow_html=True)
                elif classification == "MODERATE":
                    st.markdown(badge("🟠 MODERATE RISK", "#f97316"), unsafe_allow_html=True)
                else:
                    st.markdown(badge("🟢 LOW RISK", "#22c55e"), unsafe_allow_html=True)

                # Incidents for this location
                related = incident_manager.get_incidents_for_place(place)
                st.write("### Incidents in this area:")
                if related:
                    for r in related:
                        st.write(f"- {r.get('type', 'Unknown')} at {r.get('timestamp', 'N/A')}")
                else:
                    st.write("No reported incidents yet.")

                if classification == "HIGH":
                    tips = "• Avoid isolated areas<br>• Travel in groups<br>• Keep emergency contacts ready"
                elif classification == "MODERATE":
                    tips = "• Stay alert<br>• Avoid late night travel"
                else:
                    tips = "• Area is relatively safe"
                st.markdown(card(tips, border_color="var(--accent)", title="🛡️ Safety Tips"), unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Tab 2 — Report Incident (Task 11.4)
    # -----------------------------------------------------------------------
    with tabs[2]:
        st.subheader("🚨 Report Incident")
        report_place = st.text_input("Location", key="report_place")
        incident_type = st.selectbox("Incident Type", [
            "Theft", "Harassment", "Chain Snatching", "Assault",
            "Stalking", "Kidnapping", "Domestic Violence", "Eve Teasing",
        ])
        if st.button("Submit Report"):
            if not report_place.strip():
                st.markdown(card("Location is required.", border_color="var(--danger)"), unsafe_allow_html=True)
            else:
                ok, msg = incident_manager.report_incident(username, report_place, incident_type)
                if ok:
                    st.markdown(card("✅ " + msg, border_color="var(--success)"), unsafe_allow_html=True)
                else:
                    st.markdown(card(msg, border_color="var(--danger)"), unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Tab 3 — SOS (Task 11.5)
    # -----------------------------------------------------------------------
    with tabs[3]:
        st.subheader("🆘 Emergency SOS")
        contacts = contact_manager.get_contacts(username)
        if not contacts:
            st.markdown(card("⚠️ No emergency contacts registered. Please add contacts before using SOS.", border_color="var(--warning)"), unsafe_allow_html=True)
        if st.button("🚨 Send SOS Alert", key="sos_tab_button"):
            result = sos_service.trigger_sos(username, lat=0.0, lon=0.0)
            if "warning" in result:
                st.markdown(card(result["warning"], border_color="var(--warning)"), unsafe_allow_html=True)
            else:
                if result["notified"]:
                    names = "<br>".join(f"• {n}" for n in result["notified"])
                    st.markdown(card("✅ SOS sent! Notified contacts:<br>" + names, border_color="var(--success)"), unsafe_allow_html=True)
                if result["failed"]:
                    st.markdown(card("Failed to notify: " + ", ".join(result["failed"]), border_color="var(--danger)"), unsafe_allow_html=True)
                if not result["notified"] and not result["failed"]:
                    st.markdown(card("SOS logged. No contacts with email addresses found.", border_color="var(--accent)"), unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Tab 4 — Contact Management (Task 11.6)
    # -----------------------------------------------------------------------
    with tabs[4]:
        st.subheader("📞 Emergency Contacts")

        with st.form("add_contact_form"):
            c_name = st.text_input("Name", key="c_name")
            c_phone = st.text_input("Phone", key="c_phone")
            c_email = st.text_input("Email", key="c_email")
            add_submitted = st.form_submit_button("Add Contact")

        if add_submitted:
            ok, msg = contact_manager.add_contact(username, c_name, c_phone, c_email)
            if ok:
                st.markdown(card("✅ " + msg, border_color="var(--success)"), unsafe_allow_html=True)
            else:
                st.markdown(card(msg, border_color="var(--danger)"), unsafe_allow_html=True)

        st.markdown("<h3 style='color:var(--text-primary);'>Saved Contacts</h3>", unsafe_allow_html=True)
        saved = contact_manager.get_contacts(username)
        if saved:
            for idx, c in enumerate(saved):
                col_info, col_del = st.columns([4, 1])
                with col_info:
                    body = (
                        f"<div style='font-weight:700;font-size:1.05rem;color:var(--text-primary);'>{c.get('name', '—')}</div>"
                        f"<div style='color:var(--text-muted);font-size:0.9rem;'>📱 {c.get('phone', '—')} &nbsp;|&nbsp; ✉️ {c.get('email', '—')}</div>"
                    )
                    st.markdown(card(body, border_color="var(--accent)"), unsafe_allow_html=True)
                with col_del:
                    if st.button("🗑️", key=f"del_contact_{idx}", help="Delete contact"):
                        ok, msg = contact_manager.delete_contact(username, idx)
                        if ok:
                            st.markdown(card(msg, border_color="var(--success)"), unsafe_allow_html=True)
                            st.rerun()
                        else:
                            st.markdown(card(msg, border_color="var(--danger)"), unsafe_allow_html=True)
        else:
            st.markdown(card("📭 No contacts added yet. Add your first emergency contact above.", border_color="var(--text-muted)"), unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Tab 5 — Safe Route (Task 11.7)
    # -----------------------------------------------------------------------
    with tabs[5]:
        st.subheader("🛣️ Safe Route Analysis")
        src = st.text_input("Source", key="route_src")
        dest = st.text_input("Destination", key="route_dest")
        if st.button("Analyze Route"):
            if not src.strip() or not dest.strip():
                st.error("Both source and destination are required.")
            else:
                result = route_analyzer.analyze_route(src, dest)
                if isinstance(result, tuple):
                    st.markdown(card(result[1], border_color="var(--danger)"), unsafe_allow_html=True)
                else:
                    score = result["risk_score"]
                    classification = result["classification"]
                    safe_zones = result["safe_zones"]

                    r_border = "var(--danger)" if classification == "HIGH" else "var(--warning)" if classification == "MODERATE" else "var(--success)"
                    st.markdown(metric_card("Route Risk Score", str(round(score, 2)), r_border), unsafe_allow_html=True)
                    if classification == "HIGH":
                        st.markdown(badge("🔴 HIGH RISK Route", "#ef4444"), unsafe_allow_html=True)
                    elif classification == "MODERATE":
                        st.markdown(badge("🟠 MODERATE RISK Route", "#f97316"), unsafe_allow_html=True)
                    else:
                        st.markdown(badge("🟢 LOW RISK Route", "#22c55e"), unsafe_allow_html=True)

                    zones_html = "".join(f"<div>🏥 {z}</div>" for z in safe_zones)
                    st.markdown(card(zones_html, border_color="var(--success)", title="🏥 Nearby Safe Zones"), unsafe_allow_html=True)
