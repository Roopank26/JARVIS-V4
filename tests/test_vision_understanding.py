"""
Tests for JARVIS Vision Production — Screen Understanding.
"""

import io

from jarvis.vision.production import ScreenAnalyzer, VisionConfig


def _make_image_bytes(width: int = 100, height: int = 100) -> bytes:
    buf = io.BytesIO()
    from PIL import Image

    img = Image.new("RGB", (width, height), color="white")
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestScreenUnderstanding:
    def setup_method(self):
        self.config = VisionConfig()
        self.analyzer = ScreenAnalyzer(self.config)
        self.image = _make_image_bytes()

    def test_understand_screen_returns_dict_without_llm(self):
        result = self.analyzer.understand_screen(self.image, "", {})
        assert isinstance(result, dict)
        assert "description" in result
        assert "primary_action" in result
        assert "ui_elements" in result

    def test_understand_screen_uses_ocr_text_when_available(self, monkeypatch):
        class FakeClient:
            def is_available(self):
                return True

            async def generate(self, system="", prompt="", temperature=0.7, max_tokens=2048, model=None):
                return '{"description": "User sees a login screen", "primary_action": "enter credentials", "ui_elements": ["username field", "password field", "login button"]}'

        monkeypatch.setattr("jarvis.api.gemini.SimpleLLMClient", lambda: FakeClient(), raising=False)
        result = self.analyzer.understand_screen(self.image, "Login Sign up", {"width": 100, "height": 100})
        assert isinstance(result, dict)
        assert "Login" in result["description"] or "login" in result["description"]
        assert result["primary_action"] == "enter credentials"

    def test_understand_screen_falls_back_on_llm_failure(self, monkeypatch):
        class DummyClient:
            def is_available(self):
                return False

        monkeypatch.setattr("jarvis.api.gemini.SimpleLLMClient", lambda: DummyClient(), raising=False)
        result = self.analyzer.understand_screen(self.image, "", {})
        assert "description" in result
