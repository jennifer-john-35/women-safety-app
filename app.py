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
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(page_title="AI Women Safety System", layout="wide")

st.markdown("""
<style>
.block-container { padding-top: 1rem; padding-bottom: 1rem; }
h1, h2, h3 { text-align: center; }
</style>
""", unsafe_allow_html=True)

st.title("🌍 AI Women Safety System")
st.caption("Powered by Machine Learning Risk Prediction Model")

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
            st.error(msg)

    st.markdown("---")
    st.subheader("📝 Register")
    with st.form("register_form"):
        reg_username = st.text_input("Username", key="reg_username")
        reg_password = st.text_input("Password (min 8 chars)", type="password", key="reg_password")
        reg_submitted = st.form_submit_button("Register")

    if reg_submitted:
        ok, msg = auth.register_user(reg_username, reg_password)
        if ok:
            st.success(msg + " You can now log in.")
        else:
            st.error(msg)

# ---------------------------------------------------------------------------
# Main application — only shown when logged in
# ---------------------------------------------------------------------------
else:
    username = st.session_state.user
    st.success(f"Welcome, {username}")

    # Single SOS button at the top of the page (Requirement 5.4)
    if st.button("🆘 SOS — Send Emergency Alert", type="primary"):
        result = sos_service.trigger_sos(username, lat=0.0, lon=0.0)
        if "warning" in result:
            st.warning(result["warning"])
        else:
            if result["notified"]:
                st.success("✅ SOS sent! Notified: " + ", ".join(result["notified"]))
            if result["failed"]:
                st.error("Failed to notify: " + ", ".join(result["failed"]))
            if not result["notified"] and not result["failed"]:
                st.info("SOS logged. No contacts with email addresses found.")

    if st.button("🚪 Logout"):
        auth.logout_user()
        st.rerun()

    # Dashboard metrics
    _incidents = incident_manager._load_incidents()
    _hotspots = incident_manager.load_hotspots()
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Incidents", len(_incidents))
    col2.metric("High Risk Cities", len([h for h in _hotspots if h.get("risk", 0) > 0.7]))
    col3.metric("Active Alerts", len(_incidents))

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
        m = folium.Map(location=[20, 0], zoom_start=2)
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

                st.metric("Risk Score", round(score, 2))
                if classification == "HIGH":
                    st.error("🔴 HIGH RISK AREA")
                elif classification == "MODERATE":
                    st.warning("🟠 MODERATE RISK")
                else:
                    st.success("🟢 LOW RISK")

                # Incidents for this location
                related = incident_manager.get_incidents_for_place(place)
                st.write("### Incidents in this area:")
                if related:
                    for r in related:
                        st.write(f"- {r.get('type', 'Unknown')} at {r.get('timestamp', 'N/A')}")
                else:
                    st.write("No reported incidents yet.")

                # Safety tips based on classification
                st.write("### 🛡️ Safety Tips")
                if classification == "HIGH":
                    st.write("- Avoid isolated areas")
                    st.write("- Travel in groups")
                    st.write("- Keep emergency contacts ready")
                elif classification == "MODERATE":
                    st.write("- Stay alert")
                    st.write("- Avoid late night travel")
                else:
                    st.write("- Area is relatively safe")

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
                st.error("Location is required.")
            else:
                ok, msg = incident_manager.report_incident(username, report_place, incident_type)
                if ok:
                    st.success("✅ " + msg)
                else:
                    st.error(msg)

    # -----------------------------------------------------------------------
    # Tab 3 — SOS (Task 11.5)
    # -----------------------------------------------------------------------
    with tabs[3]:
        st.subheader("🆘 Emergency SOS")
        contacts = contact_manager.get_contacts(username)
        if not contacts:
            st.warning("⚠️ No emergency contacts registered. Please add contacts before using SOS.")
        if st.button("🚨 Send SOS Alert", key="sos_tab_button"):
            result = sos_service.trigger_sos(username, lat=0.0, lon=0.0)
            if "warning" in result:
                st.warning(result["warning"])
            else:
                if result["notified"]:
                    st.success("✅ SOS sent! Notified contacts:")
                    for name in result["notified"]:
                        st.write(f"  - {name}")
                if result["failed"]:
                    st.error("Failed to notify: " + ", ".join(result["failed"]))
                if not result["notified"] and not result["failed"]:
                    st.info("SOS logged. No contacts with email addresses found.")

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
                st.success("✅ " + msg)
            else:
                st.error(msg)

        st.write("### Saved Contacts")
        saved = contact_manager.get_contacts(username)
        if saved:
            for idx, c in enumerate(saved):
                col_info, col_del = st.columns([4, 1])
                with col_info:
                    st.write(
                        f"**{c.get('name', '—')}** | "
                        f"📱 {c.get('phone', '—')} | "
                        f"✉️ {c.get('email', '—')}"
                    )
                with col_del:
                    if st.button("Delete", key=f"del_contact_{idx}"):
                        ok, msg = contact_manager.delete_contact(username, idx)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
        else:
            st.info("No contacts added yet.")

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
                    # (False, error_message)
                    st.error(result[1])
                else:
                    score = result["risk_score"]
                    classification = result["classification"]
                    safe_zones = result["safe_zones"]

                    st.metric("Route Risk Score", round(score, 2))
                    if classification == "HIGH":
                        st.error("🔴 HIGH RISK Route")
                    elif classification == "MODERATE":
                        st.warning("🟠 MODERATE RISK Route")
                    else:
                        st.success("🟢 LOW RISK Route")

                    st.write("### 🏥 Nearby Safe Zones")
                    for zone in safe_zones:
                        st.write(f"- {zone}")
