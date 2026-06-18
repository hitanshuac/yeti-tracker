import datetime
import json
import os
import re

import duckdb
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load from .secrets/.env if it exists, otherwise fallback to default .env
if os.path.exists(".secrets/.env"):
    load_dotenv(".secrets/.env")
else:
    load_dotenv()

PROMPT_INGESTION_BAIT = """You are a warm, non-judgmental, hyper-supportive lifestyle listener.
Your goal is to safely extract data points without making the user feel guilty.
NEVER mention carbon, climate change, or environmental impact.
Act like a friendly lifestyle blogger just capturing their day.
CRITICAL: You MUST calculate the YEARLY total for each category based on the text.
If they say 'once a month', multiply by 12. If they say 'every workday', multiply by 260.
If frequency is unspecified, assume the stated number is their yearly total.
You MUST perform the math silently and output ONLY the final computed integer.
DO NOT output formulas (e.g., no '260 * 10'). The JSON values MUST be raw integers.
Estimate distances in km. If specific locations are mentioned without distances (e.g. "from Kandivali to Sakinaka"),
you MUST estimate the real-world distance between them in km based on your geographic knowledge.
You MUST output a strict JSON object exactly matching this format:
{{
  "miles_driven": 0,
  "flight_miles": 0,
  "transit_miles": 0,
  "ac_hours": 0,
  "restaurant_meals": 0
}}
Text: {safe_text}"""

PROMPT_WRATH_SWITCH = """{system_msg}
The user just tried to hide behind a friendly conversation. They confessed to their actions.
[SILENT ACCOUNTABILITY METRICS]: {kpis}
The user's primary goal today is: {goal}. YOU MUST TAILOR YOUR ADVICE SPECIFICALLY TO THIS GOAL.
{extra_txt}
{rag_context}
You must output a strict JSON object matching this schema:
{{
  "silver_lining": "One sentence praising the user for a sustainable choice they made or at least acknowledging their honesty.",
  "roast": "One witty, aggressive observation calling out their massive forecast and their history.",
  "guilt_easing_question": "A friendly, harmless-sounding follow up question that subtly encourages them to confess another bad habit (e.g., 'Do you have any fun weekend trips planned?').",
  "alternatives": [
    {{
      "type": "Convenience",
      "alternative": "A simple baby step that is extremely easy to adopt",
      "pros": "The benefits",
      "cons": "The downsides",
      "est_monthly_savings_inr": 500.00
    }},
    {{
      "type": "Maximum Impact",
      "alternative": "A major lifestyle change that guarantees massive carbon savings",
      "pros": "The benefits",
      "cons": "The downsides",
      "est_monthly_savings_inr": 2500.00
    }}
  ]
}}
CRITICAL INSTRUCTION: You MUST provide exactly two alternatives (one 'Convenience' and one 'Maximum Impact'). Together, these alternatives MUST reduce their total Social Cost of Carbon by AT LEAST 20%.
LOGIC DIRECTIVE: Your alternatives MUST be hyper-specific to the exact categories driving their footprint. If their footprint comes entirely from AC, DO NOT suggest they stop driving. If they already use public transit, DO NOT suggest public transit—instead suggest they WFH or tackle their AC/Diet. DO NOT give redundant advice.
DO NOT be insulting to their identity, attack the behavior. OUTPUT ONLY VALID JSON. No extra text."""  # noqa: E501


def init_db(db_path: str = "data/yeti.duckdb"):
    """Idempotent initialization of the history table."""
    conn = duckdb.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_history (
            session_id VARCHAR,
            timestamp TIMESTAMP,
            daily_carbon_kg DOUBLE,
            tier VARCHAR
        )
    """)


def append_history(session_id: str, daily_carbon_kg: float, tier: str, db_path: str = "data/yeti.duckdb"):
    """Persists a confession event."""
    init_db(db_path)
    conn = duckdb.connect(db_path)
    conn.execute(
        "INSERT INTO user_history VALUES (?, ?, ?, ?)", [session_id, datetime.datetime.now(), daily_carbon_kg, tier]
    )


def fetch_historical_kpis(session_id: str, db_path: str = "data/yeti.duckdb") -> str:
    """Extracts aggregate KPIs for Silent Accountability."""
    init_db(db_path)
    conn = duckdb.connect(db_path)
    res = conn.execute(
        "SELECT COUNT(*), AVG(daily_carbon_kg) FROM user_history WHERE session_id = ?", [session_id]
    ).fetchone()
    if res and res[0] > 0:
        return f"User has confessed {res[0]} times. Their average daily footprint is {res[1]:.1f} kg."
    return "This is the user's first confession."


def log_error_to_json(error_type: str, component: str, message: str, log_file: str = "data/error_logs.json"):
    """Appends an error entry to a JSON file idempotently, ensuring schema compliance."""
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    if not os.path.exists(log_file):
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump([], f)

    with open(log_file, encoding="utf-8") as f:
        try:
            logs = json.load(f)
            if not isinstance(logs, list):
                logs = []
        except json.JSONDecodeError:
            logs = []

    before_count = len(logs)
    new_entry = {
        "error_type": error_type,
        "component": component,
        "message": message,
        "status": "UNRESOLVED",
        "resolution_strategy": None,
    }
    logs.append(new_entry)

    temp_file = f"{log_file}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)
    os.replace(temp_file, log_file)

    with open(log_file, encoding="utf-8") as f:
        verified = json.load(f)
        assert len(verified) == before_count + 1, "Data loss detected during logging"


class ParsedPersonalData(BaseModel):
    """Pydantic model representing parsed activities."""

    miles_driven: int = Field(ge=0)
    flight_miles: int = Field(ge=0)
    transit_miles: int = Field(ge=0)
    ac_hours: int = Field(ge=0)
    restaurant_meals: int = Field(ge=0)


class AdvisorAlternative(BaseModel):
    type: str
    alternative: str
    pros: str
    cons: str
    est_monthly_savings_inr: float


class AdvisorResponse(BaseModel):
    silver_lining: str
    roast: str
    guilt_easing_question: str
    alternatives: list[AdvisorAlternative]


def sanitize_input(text: str) -> str:
    """Sanitizes raw input text to mitigate CWE-74 prompt injection."""
    if not isinstance(text, str):
        raise ValueError("Input must be a string")
    sanitized = text[:1000]
    for char in ["<", ">", "{", "}"]:
        sanitized = sanitized.replace(char, "")
    return sanitized.strip()


def run_duckdb_math(
    car_miles: int,
    flight_miles: int,
    transit_miles: int,
    ac_hours: int,
    restaurant_meals: int,
    dataset_path: str = "data/carbon_factors.csv",
) -> tuple[float, float, dict]:
    """Calculates forecasted carbon footprint and financial cost using DuckDB."""
    conn = duckdb.connect()

    try:
        query = f"SELECT activity, co2_kg_per_unit, social_cost_usd_per_kg FROM read_csv_auto('{dataset_path}')"
        results = conn.execute(query).fetchall()
        factors = {row[0]: {"co2": float(row[1]), "scc": float(row[2])} for row in results}
    except Exception as e:
        log_error_to_json(type(e).__name__, "run_duckdb_math", str(e))
        factors = {}

    def get_factor(activity: str, key: str, default: float) -> float:
        return factors.get(activity, {}).get(key, default)

    yearly_car_co2 = car_miles * get_factor("miles_driven", "co2", 0.4)
    yearly_flight_co2 = flight_miles * get_factor("flight_miles", "co2", 0.25)
    yearly_transit_co2 = transit_miles * get_factor("transit_miles", "co2", 0.14)
    yearly_ac_co2 = ac_hours * get_factor("ac_hours", "co2", 1.5)
    yearly_restaurant_co2 = restaurant_meals * get_factor("restaurant_meal", "co2", 8.5)

    yearly_miles = yearly_car_co2 + yearly_flight_co2 + yearly_transit_co2
    yearly_ac = yearly_ac_co2
    yearly_restaurant = yearly_restaurant_co2

    yearly_co2 = yearly_miles + yearly_ac + yearly_restaurant

    carbon_tax_usd = (
        yearly_miles * get_factor("miles_driven", "scc", 0.19)
        + yearly_ac * get_factor("ac_hours", "scc", 0.19)
        + yearly_restaurant * get_factor("restaurant_meal", "scc", 2.50)
    )

    breakdown = {"Transportation": yearly_miles, "AC/Heating": yearly_ac, "Eating Out": yearly_restaurant}

    return yearly_co2, carbon_tax_usd, breakdown


def _safe_eval_math_expr(match: "re.Match") -> str:
    """Safely evaluate a simple arithmetic expression (e.g., '260 * 10')."""
    import re as _re

    expr = match.group(0)
    # Only allow digits, spaces, *, +, -, /, and .
    if _re.fullmatch(r"[\d\s\*\+\-\/\.]+", expr):
        try:
            return str(int(eval(expr)))
        except Exception:
            return "0"
    return "0"


def _recover_failed_generation(error_msg: str) -> dict | None:
    """Extract and fix the failed_generation JSON from a Groq 400 error."""
    import re

    # Pull out the failed_generation string from the error message
    match = re.search(r"'failed_generation':\s*'(.*?)'}\}", error_msg, re.DOTALL)
    if not match:
        return None

    raw_json = match.group(1)
    # Unescape the string
    raw_json = raw_json.replace("\\n", "\n").replace('\\"', '"')

    # Replace arithmetic expressions (e.g., "260 * 2 * 6.4") with computed ints
    fixed_json = re.sub(r"[\d]+(?:\s*[\*\+\-\/]\s*[\d\.]+)+", _safe_eval_math_expr, raw_json)

    try:
        data = json.loads(fixed_json)
        # Ensure all values are integers
        return {k: int(float(v)) if isinstance(v, int | float) else v for k, v in data.items()}
    except (json.JSONDecodeError, ValueError):
        return None


def parse_messy_text(text: str) -> dict:
    """Uses LLM to extract JSON from messy natural language safely."""
    import time

    from groq import Groq

    api_key = os.environ.get("GROQ_API_KEY")
    default_payload = {
        "miles_driven": 0,
        "flight_miles": 0,
        "transit_miles": 0,
        "ac_hours": 0,
        "restaurant_meals": 0,
    }

    if not api_key:
        st.error("Missing GROQ_API_KEY. Please set it in your environment.")
        log_error_to_json("EnvironmentError", "parse_messy_text", "Missing GROQ_API_KEY.")
        return default_payload

    safe_text = sanitize_input(text)
    client = Groq(api_key=api_key)

    prompt = PROMPT_INGESTION_BAIT.format(safe_text=safe_text)

    for _attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            data = json.loads(content)
            return data
        except Exception as e:
            error_str = str(e)
            log_error_to_json(type(e).__name__, "parse_messy_text", error_str)

            # Attempt recovery from Groq's failed_generation field
            if "failed_generation" in error_str:
                recovered = _recover_failed_generation(error_str)
                if recovered:
                    st.info("🔧 Recovered LLM output from math expressions.")
                    return recovered

            time.sleep(1)

    return default_payload


def fetch_rag_context(text: str, dataset_path: str = "data/carbon_factors.csv") -> str:
    """Uses DuckDB to extract context from the dataset."""
    import re

    conn = duckdb.connect()
    try:
        words = re.findall(r"\w+", text.lower())
        keywords = [w for w in words if len(w) > 4]
        if not keywords:
            return ""

        conditions = [f"LOWER(description) LIKE '%{kw}%' OR LOWER(activity) LIKE '%{kw}%'" for kw in keywords]
        where_clause = " OR ".join(conditions)

        query = f"SELECT activity, description, co2_kg_per_unit, social_cost_usd_per_kg FROM read_csv_auto('{dataset_path}') WHERE {where_clause} LIMIT 3"  # noqa: E501
        results = conn.execute(query).fetchall()

        if not results:
            return ""

        context_lines = ["RAG CONTEXT (Carbon Factors from Database):"]
        for row in results:
            context_lines.append(f"- {row[0]} ({row[1]}): {row[2]} kg CO2/unit, ${row[3]} SCC/unit")
        return "\n".join(context_lines)
    except Exception as e:
        log_error_to_json(type(e).__name__, "fetch_rag_context", str(e))
        return ""


@st.cache_data(show_spinner=False)
def get_yeti_advice(
    carbon: float,
    tax: float,
    car_miles: int,
    flight_miles: int,
    transit_miles: int,
    ac: int,
    restaurant_meals: int,
    tier: str,
    goal: str,
    rag_context: str = "",
) -> dict:
    """Uses LLM to generate advice and returns a JSON dictionary."""
    from groq import Groq

    api_key = os.environ.get("GROQ_API_KEY")
    default_payload = {
        "silver_lining": "I appreciate your honesty.",
        "roast": "But your carbon footprint is a total disaster.",
        "guilt_easing_question": "Are there any other guilty pleasures you want to share?",
        "alternatives": [
            {
                "type": "Convenience",
                "alternative": "Work from home 2 days a week",
                "pros": "Save time and gas",
                "cons": "Less social interaction",
                "est_monthly_savings_inr": 500.0,
            },
            {
                "type": "Maximum Impact",
                "alternative": "Sell your car and bike everywhere",
                "pros": "Massive carbon savings",
                "cons": "Extremely inconvenient in winter",
                "est_monthly_savings_inr": 2500.0,
            },
        ],
    }

    if not api_key:
        return default_payload

    if carbon > 15000:
        system_msg = "You are a ruthless climate auditor. The user is actively destroying the planet."
    elif carbon > 8000:
        system_msg = "You are a strict, disappointed advisor. The user is careless."
    else:
        system_msg = "You are a friendly environmental scientist. The user's footprint is okay, but could be better."

    extra_txt = f"The user's EXACT YEARLY FORECAST is {carbon:,.0f} kg, creating a Social Cost of Carbon (Tax Debt) of ₹{tax:,.2f} INR (calculated at 15.80 INR per kg CO2).\nThis year, they will travel {car_miles} km by car, {flight_miles} km by plane, and {transit_miles} km by train/bus.\nThey will use the AC for {ac} hours, and eat out at restaurants {restaurant_meals} times."  # noqa: E501

    session_id = st.session_state.get("session_id", "demo_user")
    kpis = fetch_historical_kpis(session_id)

    prompt = PROMPT_WRATH_SWITCH.format(
        system_msg=system_msg, kpis=kpis, goal=goal, extra_txt=extra_txt, rag_context=rag_context
    )

    client = Groq(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        log_error_to_json(type(e).__name__, "get_yeti_advice", str(e))
        return default_payload


def create_gauge_chart(value: float, max_value: float, title: str) -> go.Figure:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": title, "font": {"color": "white"}},
            gauge={
                "axis": {"range": [None, max_value], "tickcolor": "white"},
                "bar": {"color": "#ff4b4b"},
                "bgcolor": "white",
                "borderwidth": 2,
                "bordercolor": "gray",
                "steps": [
                    {"range": [0, max_value * 0.3], "color": "lightgreen"},
                    {"range": [max_value * 0.3, max_value * 0.7], "color": "yellow"},
                    {"range": [max_value * 0.7, max_value], "color": "salmon"},
                ],
            },
        )
    )
    fig.update_layout(
        paper_bgcolor="#0e1117",
        font={"color": "white", "family": "Arial"},
        height=250,
        margin={"l": 20, "r": 20, "b": 20, "t": 50},
    )
    return fig


def create_savings_waterfall(monthly_tax: float, savings: float) -> go.Figure:
    """Shows a waterfall chart: Current Tax -> Savings -> Optimized Tax."""
    optimized = max(0, monthly_tax - savings)
    weekly_saved = savings / 4.33
    quarterly_saved = savings * 3

    fig = go.Figure(
        go.Waterfall(
            name="Monthly Impact",
            orientation="v",
            measure=["absolute", "relative", "total"],
            x=["Your Monthly Tax", "AI Savings Plan", "After Rescue"],
            y=[monthly_tax, -savings, optimized],
            text=[f"₹{monthly_tax:,.0f}", f"-₹{savings:,.0f}", f"₹{optimized:,.0f}"],
            textposition="outside",
            connector={"line": {"color": "#555"}},
            decreasing={"marker": {"color": "#00cc66"}},
            increasing={"marker": {"color": "#ff4b4b"}},
            totals={"marker": {"color": "#3b82f6"}},
        )
    )
    pct = (savings / monthly_tax * 100) if monthly_tax > 0 else 0
    fig.update_layout(
        title={
            "text": f"You save ₹{weekly_saved:,.0f}/wk · ₹{savings:,.0f}/mo · ₹{quarterly_saved:,.0f}/qtr ({pct:.0f}% reduction)",  # noqa: E501
            "font": {"color": "#00cc66", "size": 14},
        },
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font={"color": "white", "family": "Arial"},
        height=380,
        margin={"l": 20, "r": 20, "b": 20, "t": 60},
        showlegend=False,
    )
    fig.update_yaxes(gridcolor="#333333", title="INR / Month")
    return fig


def create_doom_vs_rescue(monthly_tax: float, savings: float) -> go.Figure:
    """Shows 12-month projection: doom trajectory vs rescue trajectory."""
    months = [f"Month {i}" for i in range(1, 13)]
    doom = [monthly_tax * i for i in range(1, 13)]
    optimized_monthly = max(0, monthly_tax - savings)
    rescue = [optimized_monthly * i for i in range(1, 13)]
    cumulative_saved = [(monthly_tax - optimized_monthly) * i for i in range(1, 13)]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=months,
            y=doom,
            mode="lines+markers",
            name="💀 Current Path",
            line={"color": "#ff4b4b", "width": 3},
            fill=None,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=months,
            y=rescue,
            mode="lines+markers",
            name="🛡️ After Rescue",
            line={"color": "#00cc66", "width": 3},
        )
    )
    fig.add_trace(
        go.Bar(
            x=months,
            y=cumulative_saved,
            name="💰 Cumulative Saved",
            marker_color="rgba(59, 130, 246, 0.4)",
        )
    )
    fig.update_layout(
        title={"text": "12-Month Financial Trajectory", "font": {"color": "white"}},
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font={"color": "white", "family": "Arial"},
        height=380,
        margin={"l": 20, "r": 20, "b": 20, "t": 50},
        yaxis_title="Cumulative INR",
        barmode="overlay",
        legend={"orientation": "h", "y": -0.15},
    )
    fig.update_yaxes(gridcolor="#333333")
    return fig


if __name__ == "__main__":
    import random

    st.set_page_config(layout="wide", page_title="Yeti-Tracker Carbon Footprint")
    st.title("Yeti-Tracker: Know Your Footprint")

    default_vals = {"car_miles": 10, "flight_miles": 0, "transit_miles": 0, "ac_hours": 4, "restaurant_meals": 0}
    for k, v in default_vals.items():
        if k not in st.session_state:
            st.session_state[k] = v

    if "session_id" not in st.session_state:
        import datetime
        import uuid

        st.session_state.session_id = str(uuid.uuid4())

        # Seed 30-day history for this specific session
        conn = duckdb.connect("data/yeti.duckdb")
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=30)
        curr = start_date
        base = 20.0
        while curr <= end_date:
            base += random.uniform(0.1, 1.5)
            d_val = base + random.uniform(-5.0, 10.0)
            conn.execute(
                "INSERT INTO user_history VALUES (?, ?, ?, ?)", [st.session_state.session_id, curr, d_val, "Human"]
            )
            curr += datetime.timedelta(days=1)

    if "last_extracted_text" not in st.session_state:
        st.session_state.last_extracted_text = "I drove about 40 miles round trip for work. Ate out at a fancy restaurant for lunch. Left the AC on for 10 hours."  # noqa: E501

    if "confessional_input" not in st.session_state:
        st.session_state.confessional_input = st.session_state.last_extracted_text

    def handle_extract():
        messy = st.session_state.get("confessional_input", "")
        st.session_state.last_extracted_text = messy
        parsed = parse_messy_text(messy)
        st.session_state.car_miles = parsed.get("miles_driven", 0)
        st.session_state.flight_miles = parsed.get("flight_miles", 0)
        st.session_state.transit_miles = parsed.get("transit_miles", 0)
        st.session_state.ac_hours = parsed.get("ac_hours", 0)
        st.session_state.restaurant_meals = parsed.get("restaurant_meals", 0)

    def handle_reply():
        reply = st.session_state.get("reply_input", "")
        if reply:
            st.session_state.confessional_input += f"\n\nYeti Advisor Response: {reply}"
            st.session_state.reply_input = ""
            handle_extract()
            st.session_state.auto_extracted = True
            st.session_state.run_math = True
            st.session_state.has_calculated = True

    def handle_calculate():
        messy = st.session_state.get("confessional_input", "")
        last = st.session_state.get("last_extracted_text", "")
        if messy != last:
            handle_extract()
            st.session_state.auto_extracted = True
        st.session_state.run_math = True
        st.session_state.has_calculated = True

    def set_random_persona():
        personas = [
            "The Commuter: I drive 20 miles to work every weekday. No flights. Eat out once a week.",
            "The Crypto Bro: I run 5 AC units 24/7 for my mining rig. I eat out 3 times a day. I fly first class to Dubai once a month.",  # noqa: E501
            "The Corporate Jetsetter: I fly cross-country every week. I take Ubers everywhere (maybe 50 miles a week). Eat out every day.",  # noqa: E501
            "The Eco-Warrior: I ride my bike to work. No AC. Eat out maybe once a month. No flights.",
            "The Suburbanite: I drive a big SUV about 40 miles a day for errands. Keep the AC blasted all summer. Fly to Florida once a year for vacation.",  # noqa: E501
        ]
        st.session_state.confessional_input = random.choice(personas)

    # Top Gamification Section
    if st.session_state.get("has_calculated", False):
        # Only show success messages once per calculate event
        if st.session_state.get("run_math", False):
            if st.session_state.pop("auto_extracted", False):
                st.success("✅ Auto-extracted your new text!")

        c_miles = st.session_state.car_miles
        f_miles = st.session_state.flight_miles
        t_miles = st.session_state.transit_miles
        a_hours = st.session_state.ac_hours
        r_meals = st.session_state.restaurant_meals

        carbon, tax_usd, breakdown = run_duckdb_math(c_miles, f_miles, t_miles, a_hours, r_meals)

        monthly_carbon = carbon / 12.0
        monthly_tax = tax_usd / 12.0

        if carbon > 30000:
            tier = "Category 3 Catastrophe"
            color = "#ff4b4b"
            msg = f"CATEGORY 3 CATASTROPHE ({monthly_carbon:,.0f} kg / mo)"
            img_path = "data/assets/godzilla.jpg"
        elif carbon > 15000:
            tier = "Category 2 Catastrophe"
            color = "#ffaa00"
            msg = f"CATEGORY 2 CATASTROPHE ({monthly_carbon:,.0f} kg / mo)"
            img_path = "data/assets/yeti.jpg"
        elif carbon > 9000:
            tier = "Category 1 Warning"
            color = "#ffd700"
            msg = f"CATEGORY 1 WARNING ({monthly_carbon:,.0f} kg / mo)"
            img_path = "data/assets/vegeta.jpg"
        else:
            tier = "Human"
            color = "#00cc66"
            msg = f"ACCEPTABLE IMPACT ({monthly_carbon:,.0f} kg / mo)"
            img_path = None

        st.markdown(
            f"<h1 style='text-align: center; color: {color}; font-size: 4em;'>{msg}</h1>", unsafe_allow_html=True
        )

        if img_path and os.path.exists(img_path):
            st.image(img_path, use_container_width=True)

        if st.session_state.get("run_math", False):
            session_id = st.session_state.get("session_id", "demo_user")
            append_history(session_id, carbon / 365.0, tier)
            st.session_state.run_math = False

        st.markdown("---")
        st.markdown("### 🎙️ The Smart Advisor")
        with st.spinner("Analyzing your financial doom..."):
            rag_context = fetch_rag_context(st.session_state.get("confessional_input", ""))
            advice_json = get_yeti_advice(
                carbon, tax_usd, c_miles, f_miles, t_miles, a_hours, r_meals, tier, "Save the Planet", rag_context
            )

            # Guilt Easing Component — leads with a friendly question
            question = advice_json.get("guilt_easing_question", "Anything else you want to share?")
            st.info(f"🗣️ **Yeti Advisor asks:** {question}")

            st.success(f"☀️ **Silver Lining:** {advice_json.get('silver_lining', '')}")
            st.error(f"🔥 **The Roast:** {advice_json.get('roast', '')}")

            # Feedback Loop Input
            st.text_input(
                "💬 Confess more...",
                key="reply_input",
                on_change=handle_reply,
                placeholder="Type your response here and hit Enter...",
            )

            alts = advice_json.get("alternatives", [])
            total_monthly_savings = sum(a.get("est_monthly_savings_inr", 0) for a in alts)

            if alts:
                st.markdown("#### 💡 Adapt These TODAY (Instant Gratification)")
                import pandas as pd

                alts_display = pd.DataFrame(alts).rename(
                    columns={
                        "type": "🏷️ Strategy",
                        "alternative": "💡 What To Do",
                        "pros": "✅ Pros",
                        "cons": "⚠️ Cons",
                        "est_monthly_savings_inr": "💰 Monthly Savings (₹)",
                    }
                )
                # Using st.table ensures text wraps perfectly instead of truncating!
                st.table(alts_display.set_index("🏷️ Strategy"))

        # --- Financial Impact Dashboard ---
        st.markdown("---")
        st.markdown(
            f"### 💸 You're burning **₹{monthly_tax:,.0f}/month** — "
            f"but you could save **₹{total_monthly_savings:,.0f}/month** starting today."
        )

        # "Save Yourself" toggle
        if "show_rescue" not in st.session_state:
            st.session_state.show_rescue = False

        def toggle_rescue():
            st.session_state.show_rescue = not st.session_state.show_rescue

        btn_label = "💀 Show My Doom" if st.session_state.show_rescue else "🛡️ Save Yourself"
        st.button(btn_label, on_click=toggle_rescue, use_container_width=True)

        mc1, mc2 = st.columns(2)
        with mc1:
            st.markdown("### Monthly Carbon Tax")
            # Fixed baseline max to 25000 INR so color bands (green/yellow/red) map to objective severity
            gauge_max = max(25000, monthly_tax * 1.2)
            fig_tax = create_gauge_chart(monthly_tax, gauge_max, "Monthly Social Cost of Carbon (INR)")
            st.plotly_chart(fig_tax, use_container_width=True)

            with st.expander("🤔 How is this calculated?"):
                st.markdown("Your monthly tax is derived from the **Social Cost of Carbon (SCC)**:")
                st.write("🌍 **1 kg of CO2 = ₹15.80 in global climate damages.**")
                st.markdown("---")
                for category, val_kg in breakdown.items():
                    st.write(f"- **{category}:** {val_kg:,.0f} kg CO2/year")
                st.markdown("---")
                st.write(f"**Total Yearly:** {carbon:,.0f} kg CO2")
                st.write(f"**Yearly Tax:** {carbon:,.0f} kg * ₹15.80 = **₹{tax_usd:,.2f}**")
                st.write(f"**Monthly Tax:** ₹{tax_usd:,.2f} / 12 = **₹{monthly_tax:,.2f}**")

        with mc2:
            if st.session_state.show_rescue:
                st.markdown("### 🛡️ Your Rescue Plan")
                fig = create_doom_vs_rescue(monthly_tax, total_monthly_savings)
            else:
                st.markdown("### 💀 The Damage")
                fig = create_savings_waterfall(monthly_tax, total_monthly_savings)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 1. The Confessional (LLM Auto-Fill)")
        st.text_area(
            "Confess your lifestyle:",
            height=100,
            key="confessional_input",
        )
        c1, c2 = st.columns(2)
        with c1:
            st.button("Extract Data", type="primary", on_click=handle_extract, use_container_width=True)
        with c2:
            st.button("🎲 Try a Demo Persona", on_click=set_random_persona, use_container_width=True)

    with col2:
        st.markdown("### 2. Human Verification")
        st.info("The math engine ONLY uses these deterministic sliders. Verify the AI didn't hallucinate.")

        c_max, f_max, t_max, a_max, r_max = 50000, 100000, 50000, 8760, 1095

        st.slider("Car Kilometers Driven (Yearly)", 0, max(c_max, st.session_state.car_miles), key="car_miles")
        st.slider("Flight Kilometers (Yearly)", 0, max(f_max, st.session_state.flight_miles), key="flight_miles")
        st.slider(
            "Public Transit Kilometers (Yearly)", 0, max(t_max, st.session_state.transit_miles), key="transit_miles"
        )
        st.slider("AC / Heating Hours (Yearly)", 0, max(a_max, st.session_state.ac_hours), key="ac_hours")
        st.slider("Restaurant Meals (Yearly)", 0, max(r_max, st.session_state.restaurant_meals), key="restaurant_meals")

        st.button("Calculate Financial Impact", type="primary", use_container_width=True, on_click=handle_calculate)

    st.markdown("---")
    st.markdown("## 📈 Your Confession History")

    conn = duckdb.connect("data/yeti.duckdb")
    try:
        query = (
            "SELECT timestamp, daily_carbon_kg FROM user_history "
            f"WHERE session_id = '{st.session_state.session_id}' "
            "AND daily_carbon_kg < 1000 "
            "ORDER BY timestamp ASC"
        )
        history_df = conn.execute(query).fetchdf()
        if not history_df.empty:
            history_df["7_day_MA"] = history_df["daily_carbon_kg"].rolling(window=7, min_periods=1).mean()

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=history_df["timestamp"],
                    y=history_df["daily_carbon_kg"],
                    mode="markers",
                    name="Each Confession",
                    marker={"color": "#ff4b4b", "size": 8, "opacity": 0.7},
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=history_df["timestamp"],
                    y=history_df["7_day_MA"],
                    mode="lines",
                    name="7-Day Trend",
                    line={"color": "#ffd700", "width": 3},
                )
            )

            fig.add_hline(y=30000 / 365, line_dash="dash", line_color="red", annotation_text="⚠️ Category 3")
            fig.add_hline(y=15000 / 365, line_dash="dash", line_color="orange", annotation_text="⚠️ Category 2")
            fig.add_hline(y=9000 / 365, line_dash="dash", line_color="yellow", annotation_text="Category 1")

            fig.update_layout(
                paper_bgcolor="#0e1117",
                plot_bgcolor="#0e1117",
                font={"color": "white", "family": "Arial"},
                height=400,
                margin={"l": 20, "r": 20, "b": 20, "t": 50},
                xaxis_title="Date",
                yaxis_title="Daily Carbon (kg)",
                legend={"orientation": "h", "y": -0.15},
            )
            fig.update_yaxes(gridcolor="#333333")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No historical data yet. Confess your lifestyle to start tracking!")
    except Exception:
        st.info("Historical tracking will appear after your first confession.")
