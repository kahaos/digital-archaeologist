import httpx

from digital_archaeologist.collectors.web import WebCollector


def test_web_extracts_basic_metadata():
    html = """<html><head><title>Old Tool</title><meta name='description' content='A useful tool'></head><body><h1>Old Tool</h1><h2>Features</h2><p>Still useful.</p></body></html>"""
    def handler(request):
        return httpx.Response(200, text=html, headers={"content-type": "text/html"})
    collector = WebCollector(client=httpx.Client(transport=httpx.MockTransport(handler)))
    draft = collector.inspect("https://example.com/tool")
    assert draft.metadata["status_code"] == 200
    assert draft.title == "Old Tool"
    assert draft.metadata["description"] == "A useful tool"
    assert draft.metadata["headings"] == ["Old Tool", "Features"]


def test_web_failure_returns_structured_failed_draft():
    def handler(request):
        return httpx.Response(503, text="unavailable")
    collector = WebCollector(client=httpx.Client(transport=httpx.MockTransport(handler)))
    draft = collector.inspect("https://example.com/down")
    assert draft.metadata["ok"] is False
    assert draft.metadata["status_code"] == 503
    assert draft.metadata["error"] == "http_error"
