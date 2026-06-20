import json

from src.llm_service import ParsedPersonalData, get_advisor_response, parse_confession


# Mock groq to simulate RateLimitError and responses
class MockGroq:
    def __init__(self, mode="success"):
        self.mode = mode
        self.chat = self.Chat(self.mode)

    class Chat:
        def __init__(self, mode):
            self.mode = mode
            self.completions = self.Completions(self.mode)

        class Completions:
            def __init__(self, mode):
                self.mode = mode

            def create(self, **kwargs):
                if self.mode == "rate_limit":
                    import httpx
                    from groq import RateLimitError

                    raise RateLimitError(
                        "Rate limit exceeded",
                        response=httpx.Response(429, request=httpx.Request("POST", "url")),
                        body=None,
                    )
                elif self.mode == "invalid_json":
                    return MockResponse("{ broken json")
                elif self.mode == "success_parse":
                    data = {
                        "car_km": 10,
                        "flight_km": 0,
                        "transit_km": 5,
                        "daily_sleep_hours": 7,
                        "sleep_ac_on": False,
                        "daytime_ac_hours": 2,
                        "restaurant_meals": 1,
                    }
                    return MockResponse(json.dumps(data))
                elif self.mode == "success_advisor":
                    data = {
                        "silver_lining": "Good job.",
                        "roast": "You are terrible.",
                        "guilt_easing_question": "Any plans?",
                        "alternatives": [
                            {
                                "type": "Convenience",
                                "alternative": "Do this",
                                "pros": "Pro",
                                "cons": "Con",
                                "est_monthly_savings_inr": 500.0,
                            }
                        ],
                    }
                    return MockResponse(json.dumps(data))


class MockResponse:
    def __init__(self, content):
        self.choices = [self.Choice(content)]

    class Choice:
        def __init__(self, content):
            self.message = self.Message(content)

        class Message:
            def __init__(self, content):
                self.content = content


def test_parse_confession_success(monkeypatch):
    """Verify parse_confession returns valid parsed data on success."""
    monkeypatch.setattr("src.llm_service.Groq", lambda api_key: MockGroq("success_parse"))

    result = parse_confession("Mock input")
    assert isinstance(result, ParsedPersonalData)
    assert result.car_km == 10
    assert result.transit_km == 5


def test_parse_confession_rate_limit(monkeypatch):
    """Verify parse_confession gracefully falls back on API errors."""
    monkeypatch.setattr("src.llm_service.Groq", lambda api_key: MockGroq("rate_limit"))

    # Should not raise, should return default ParsedPersonalData
    result = parse_confession("Mock input")
    assert isinstance(result, ParsedPersonalData)
    assert result.car_km == 0
    assert result.daily_sleep_hours == 8


def test_get_advisor_response_success(monkeypatch):
    """Verify advisor returns correctly structured data."""
    monkeypatch.setattr("src.llm_service.Groq", lambda api_key: MockGroq("success_advisor"))

    result = get_advisor_response(
        carbon=5000.0,
        tax=10000.0,
        car_km=10,
        flight_km=0,
        transit_km=0,
        daily_sleep_hours=8,
        sleep_ac_on=True,
        daytime_ac_hours=2,
        restaurant_meals=1,
        tier="Human",
        goal="Mock goal",
        kpis="Mock kpis",
    )
    assert result.roast == "You are terrible."
    assert len(result.alternatives) == 1
    assert result.alternatives[0].est_monthly_savings_inr == 500.0


def test_get_advisor_response_invalid_json(monkeypatch):
    """Verify advisor falls back safely if LLM returns broken JSON."""
    monkeypatch.setattr("src.llm_service.Groq", lambda api_key: MockGroq("invalid_json"))

    result = get_advisor_response(
        carbon=5000.0,
        tax=10000.0,
        car_km=10,
        flight_km=0,
        transit_km=0,
        daily_sleep_hours=8,
        sleep_ac_on=True,
        daytime_ac_hours=2,
        restaurant_meals=1,
        tier="Human",
        goal="Mock goal",
        kpis="Mock kpis",
    )

    # Fallback structure should be intact
    assert hasattr(result, "roast")
    assert "But let's see if we can do better" in result.roast
    assert len(result.alternatives) == 2
    assert result.alternatives[0].est_monthly_savings_inr == 400.0
