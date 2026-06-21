import re

# A simple regex to catch most common emoji ranges
emoji_pattern = re.compile(
    r"["
    r"\U0001F600-\U0001F64F"  # emoticons
    r"\U0001F300-\U0001F5FF"  # symbols & pictographs
    r"\U0001F680-\U0001F6FF"  # transport & map symbols
    r"\U0001F700-\U0001F77F"  # alchemical symbols
    r"\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
    r"\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
    r"\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
    r"\U0001FA00-\U0001FA6F"  # Chess Symbols
    r"\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
    r"\u2600-\u26FF"  # Miscellaneous Symbols
    r"\u2700-\u27BF"  # Dingbats
    r"]+",
    re.UNICODE,
)

files = ["app.py", "src/llm_service.py", "src/carbon_engine.py"]
for f in files:
    try:
        with open(f, encoding="utf-8") as file:
            content = file.read()

        content_no_emoji = emoji_pattern.sub("", content)

        with open(f, "w", encoding="utf-8") as file:
            file.write(content_no_emoji)
        print(f"Cleaned {f}")
    except Exception as e:
        print(f"Error processing {f}: {e}")
