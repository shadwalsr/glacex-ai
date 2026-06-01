import pytest
import respx
import httpx
from delivery.digest_generator import DigestResult, compile_markdown_digest, send_to_ntfy

def test_compile_markdown_digest():
    digest = DigestResult(
        research_breakthroughs=["New sparse attention mechanism improves training speed by 20%."],
        new_tools=["AgentLang v0.1 released supporting fast RAG routing."],
        product_launches=[],
        company_news=["AI Startup raises $50M in Series A."],
        must_read_papers=["Attention Is All You Need."]
    )
    
    md = compile_markdown_digest(digest)
    
    assert "# GlaceX Daily Digest" in md
    assert "## 🔬 Research Breakthroughs" in md
    assert "- New sparse attention mechanism" in md
    assert "## 🛠️ New Tools" in md
    assert "- AgentLang v0.1" in md
    assert "## 🚀 Product Launches" in md
    assert "_No new updates in this category today._" in md
    assert "## 📄 Must-Read Papers" in md
    assert "- Attention Is All You Need." in md

@respx.mock
def test_send_to_ntfy_success():
    # Mock ntfy.sh endpoint
    ntfy_route = respx.post("https://ntfy.sh/glacex_test_topic").respond(status_code=200, text="ok")
    
    # Temporarily override topic
    import delivery.digest_generator
    orig_topic = delivery.digest_generator.NTFY_TOPIC
    delivery.digest_generator.NTFY_TOPIC = "glacex_test_topic"
    
    try:
        success = send_to_ntfy("Test message content", "Test Title")
        assert success
        assert ntfy_route.called
    finally:
        delivery.digest_generator.NTFY_TOPIC = orig_topic

@respx.mock
def test_send_to_ntfy_failure():
    ntfy_route = respx.post("https://ntfy.sh/glacex_test_topic").respond(status_code=500, text="internal server error")
    
    import delivery.digest_generator
    orig_topic = delivery.digest_generator.NTFY_TOPIC
    delivery.digest_generator.NTFY_TOPIC = "glacex_test_topic"
    
    try:
        success = send_to_ntfy("Test message content", "Test Title")
        assert not success
        assert ntfy_route.called
    finally:
        delivery.digest_generator.NTFY_TOPIC = orig_topic
