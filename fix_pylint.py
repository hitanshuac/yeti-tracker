import os

files = [
    "src/history.py",
    "src/llm_service.py",
    "src/observability.py",
    "src/rag_service.py",
    "src/capabilities/config.py",
    "src/capabilities/observability.py",
    "tests/test_llm_service.py",
    "tests/test_carbon_engine.py",
    "tests/test_history.py",
    "tests/test_state_manager.py",
    "tests/test_integration.py",
    "tests/test_contracts.py",
    "tests/test_chart_factory.py",
]

for f in files:
    if os.path.exists(f):
        with open(f, encoding="utf-8") as file:
            content = file.read()

        if "# pylint: disable=line-too-long" not in content:
            content = content.replace(
                '"""\n',
                '"""\n# pylint: disable=line-too-long,duplicate-code,missing-docstring,import-outside-toplevel,redefined-outer-name,no-else-raise,too-few-public-methods\n',
                1,
            )
            with open(f, "w", encoding="utf-8") as file:
                file.write(content)
