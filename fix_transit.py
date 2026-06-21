content = open("app.py", encoding="utf-8").read()

# State initialization and AI tracker variables
content = content.replace(
    'st.session_state.transit_km = getattr(parsed, "transit_km", 0)',
    'st.session_state.bus_km = getattr(parsed, "bus_km", 0)\n    st.session_state.train_metro_km = getattr(parsed, "train_metro_km", 0)',
)
content = content.replace(
    "st.session_state.ai_transit_km = st.session_state.transit_km",
    "st.session_state.ai_bus_km = st.session_state.bus_km\n    st.session_state.ai_train_metro_km = st.session_state.train_metro_km",
)

# SRE override tuple list
content = content.replace(
    '("transit_km", "ai_transit_km", 0),',
    '("bus_km", "ai_bus_km", 0),\n        ("train_metro_km", "ai_train_metro_km", 0),',
)

# Loop initialization list
content = content.replace('"transit_km",', '"bus_km",\n        "train_metro_km",')

# Personas dict keys
content = content.replace('"transit_km": 0,', '"bus_km": 0,\n            "train_metro_km": 0,')
content = content.replace('"transit_km": 2600,', '"bus_km": 0,\n            "train_metro_km": 2600,')

# UI sliders - replace transit with bus and train
slider_old = """        st.slider(
            "Public Transit Kilometers (Yearly)",
            0,
            max(t_max, st.session_state.transit_km),
            key="transit_km",
            help="Total km by bus, train, or metro per year.",
        )"""
slider_new = """        st.slider(
            "Bus Kilometers (Yearly)",
            0,
            max(t_max, st.session_state.get("bus_km", 0)),
            key="bus_km",
            help="Total km traveled by bus per year.",
        )
        st.slider(
            "Train/Metro Kilometers (Yearly)",
            0,
            max(t_max, st.session_state.get("train_metro_km", 0)),
            key="train_metro_km",
            help="Total km traveled by electric train or metro per year.",
        )"""
content = content.replace(slider_old, slider_new)

# Advisor request instantiation
content = content.replace(
    'transit_km=st.session_state.get("transit_km", 0),',
    'bus_km=st.session_state.get("bus_km", 0),\n                train_metro_km=st.session_state.get("train_metro_km", 0),',
)

open("app.py", "w", encoding="utf-8").write(content)
