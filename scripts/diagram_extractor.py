import os
from pathlib import Path


def generate_d2(output_path):
    """Write the hardcoded, high-fidelity D2 architecture map."""

    d2_content = """
direction: right

classes: {
  user_node: {
    shape: person
    style: { fill: "#4CAF50"; font-color: "#ffffff" }
  }
  ui: {
    shape: rectangle
    style: { fill: "#FF5722"; font-color: "#ffffff"; border-radius: 5 }
  }
  llm: {
    shape: cloud
    style: { fill: "#9C27B0"; font-color: "#ffffff" }
  }
  db: {
    shape: cylinder
    style: { fill: "#2196F3"; font-color: "#ffffff" }
  }
  engine: {
    shape: hexagon
    style: { fill: "#607D8B"; font-color: "#ffffff" }
  }
}

user: User { class: user_node }

yeti_tracker: Yeti-Tracker Hybrid Pipeline {
  style: { fill: transparent; stroke: "#cccccc"; stroke-dash: 5 }

  app: Streamlit UI (app.py) { class: ui }
  llm_svc: Groq Extraction (llm_service.py) { class: llm }
  verification: UI Sliders (Verification Gate) { class: ui }
  carbon: Deterministic Math (carbon_engine.py) { class: engine }
  duck: DuckDB Instance { class: db }
  history: UUID Session History { class: db }
  gamification: Tier Classification Visuals { class: ui }

  app -> llm_svc: 1. Natural Language Diary
  llm_svc -> verification: 2. Parse to Integers
  verification -> carbon: 3. User Approves Strict Values
  carbon -> duck: 4. Execute SCC Math
  carbon -> gamification: 5. Determine Catastrophe Tier
  carbon -> history: 6. Persist Session
}

user -> yeti_tracker.app: Logs daily habits
yeti_tracker.gamification -> user: Displays Roasts & Visuals
"""

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(d2_content.strip() + "\n")
    print(f"[SUCCESS] Generated high-fidelity codebase architecture diagram at {output_path}")


if __name__ == "__main__":
    docs_dir = Path(__file__).parent.parent / "docs" / "assets"
    output_file = docs_dir / "auto_architecture.d2"
    generate_d2(output_file)
