# tests/test_smoke.py

def test_smoke_import_and_handle():
    """
    A very fast check that:
    1) your Agent class can be imported,
    2) it responds to `.handle()` (without crashing),
    3) and for a no-op input it returns a string.
    """
    from app.agent import Agent

    # instantiate in “stub” mode so it doesn’t actually hit your real LLM
    a = Agent(use_real_llm=False)

    # it should have a .handle() method
    assert callable(a.handle)

    # calling handle on anything should return a string (even empty)
    out = a.handle("hello")
    assert isinstance(out, str)
