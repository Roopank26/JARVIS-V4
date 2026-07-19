"""
Tests for JARVIS response sanitization.

Verifies that leaked prompt/instruction blocks are removed,
while legitimate long responses are preserved.
"""

import pytest

from jarvis.core.agent import _sanitize_response


class TestResponseSanitizer:
    """Test response sanitization heuristics."""

    def test_normal_short_response_unchanged(self):
        """Normal short replies must not be modified."""
        response = "Hello, how can I help you today?"
        assert _sanitize_response(response) == response

    def test_long_research_report_preserved(self):
        """Long research reports must NOT be truncated or modified."""
        report = "\n".join([
            "# Market Analysis Report",
            "",
            "## Executive Summary",
            "The global AI market is projected to reach $1.8 trillion by 2030.",
            "Key drivers include cloud adoption, generative AI, and automation.",
            "We interviewed 200+ executives and analyzed 10,000+ data points.",
            "The report covers 12 sectors including healthcare, finance, manufacturing, retail, energy, transportation, education, agriculture, entertainment, real estate, legal, and public sector.",
            "",
            "## Methodology",
            "We analyzed 500+ companies across 12 sectors using quantitative and qualitative methods.",
            "Our methodology included surveys, interviews, financial modeling, and competitive analysis.",
            "",
            "## Findings",
            "1. Healthcare AI: 34% CAGR",
            "2. Finance AI: 28% CAGR",
            "3. Manufacturing AI: 22% CAGR",
            "4. Retail AI: 19% CAGR",
            "5. Education AI: 17% CAGR",
            "",
            "## Recommendations",
            "- Invest in infrastructure",
            "- Upskill workforce",
            "- Prioritize ethical AI",
            "- Establish governance frameworks",
            "- Partner with academic institutions",
        ] * 10)

        result = _sanitize_response(report)
        assert len(result) > 8000
        assert "Market Analysis Report" in result
        assert "Recommendations" in result

    def test_large_code_generation_preserved(self):
        """Large code outputs must NOT be modified."""
        code = "\n".join([
            "def fibonacci(n):",
            "    if n <= 1:",
            "        return n",
            "    return fibonacci(n-1) + fibonacci(n-2)",
            "",
            "class DataProcessor:",
            "    def __init__(self, data):",
            "        self.data = data",
            "",
            "    def process(self):",
            "        return [x * 2 for x in self.data]",
            "",
            "    def validate(self):",
            "        return all(isinstance(x, int) for x in self.data)",
        ] * 20)

        result = _sanitize_response(code)
        assert len(result) > 4000
        assert "def fibonacci" in result
        assert "class DataProcessor" in result

    def test_prompt_leakage_block_removed(self):
        """Pasted instruction blocks with leakage patterns must be removed."""
        leaked = (
            "Here is my response.\n\n"
            "OBJECTIVE: Process the user's request.\n"
            "ARCHITECTURE: Use modular design.\n"
            "Do not commit until tests pass.\n"
            "Rules:\n"
            "- Be concise\n"
            "- Be helpful\n"
        )
        result = _sanitize_response(leaked)
        assert "OBJECTIVE:" not in result
        assert "ARCHITECTURE:" not in result
        assert "Do not commit until" not in result
        assert "Rules:" not in result

    def test_duplicate_instruction_block_removed(self):
        """Duplicated long instruction paragraphs must be collapsed."""
        block = (
            "OBJECTIVE: Process the user's request. "
            "ARCHITECTURE: Use modular design. "
            "Do not commit until tests pass. "
            "Rules: Be concise, be helpful, be accurate. "
            "This is a very long instruction block that should be removed. " * 5
        )
        response = f"Hello!\n\n{block}\n\n{block}\n\nHow can I help?"
        result = _sanitize_response(response)
        occurrences = result.count("OBJECTIVE:")
        assert occurrences <= 1

    def test_echoed_user_prompt_removed(self):
        """Accidental echoing of long user prompts at start must be removed."""
        user_prompt = "from now onwards give any text type reply by speaking and always address me as sir"
        response = (
            f"{user_prompt}\n\n"
            "Here is the answer: Hello, I am JARVIS. "
            "I will speak my replies from now on."
        )
        result = _sanitize_response(response)
        assert user_prompt not in result
        assert "Here is the answer" in result

    def test_normal_multi_paragraph_preserved(self):
        """Normal multi-paragraph text must be preserved."""
        text = "\n\n".join([
            "First paragraph with some useful information.",
            "Second paragraph continuing the explanation.",
            "Third paragraph with additional details.",
            "Fourth paragraph wrapping up.",
        ] * 5)

        result = _sanitize_response(text)
        assert result.count("First paragraph") == 5
        assert result.count("Second paragraph") == 5

    def test_empty_response_unchanged(self):
        """Empty strings must pass through unchanged."""
        assert _sanitize_response("") == ""
        assert _sanitize_response(None) is None

    def test_documentation_output_preserved(self):
        """Long documentation-style output must be preserved."""
        doc = "\n".join([
            "# API Reference",
            "",
            "## GET /users",
            "Returns a list of users with pagination support.",
            "This endpoint supports filtering, sorting, and field selection.",
            "",
            "### Parameters",
            "- `limit`: number of results (default: 20, max: 100)",
            "- `offset`: pagination offset (default: 0)",
            "- `sort`: field to sort by",
            "",
            "### Response",
            "```json",
            '{"users": [], "total": 0, "limit": 20, "offset": 0}',
            "```",
            "",
            "## POST /users",
            "Create a new user account with validation.",
            "This endpoint requires authentication and returns 201 on success.",
            "",
            "### Request Body",
            "- `name`: string (required)",
            "- `email`: string (required, must be valid email)",
            "- `role`: string (optional, default: 'user')",
        ] * 10)

        result = _sanitize_response(doc)
        assert len(result) > 5000
        assert "API Reference" in result
        assert "```json" in result
