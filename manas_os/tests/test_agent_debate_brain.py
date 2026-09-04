from manas_os.agents import debate


def test_debate_prompt_requires_chart_synthesis_not_gate_paraphrase():
    prompt = debate._system_prompt()
    assert "Read chart_behavior first" in prompt
    assert "Gates are the safety boundary, not the reasoning rubric" in prompt
    assert "asymmetric reversal" in prompt
    assert "expected sequence/time window" in prompt
    assert "strongest_contradiction" in prompt
