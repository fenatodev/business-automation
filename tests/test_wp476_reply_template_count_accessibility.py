from pathlib import Path


def test_reply_template_character_counters_are_described_by_their_fields():
    html = Path("app/operator_ui/index.html").read_text(encoding="utf-8")

    assert 'id="reply-template-name"' in html
    assert 'id="reply-template-name" placeholder="Ex: Saudação inicial" aria-describedby="reply-template-name-count" required' in html
    assert 'id="reply-template-content" rows="3" placeholder="Texto da resposta..." aria-describedby="reply-template-content-count" required' in html
    assert 'id="reply-template-name-count" class="small" aria-live="off">0/100 caracteres' in html
    assert 'id="reply-template-content-count" class="small" aria-live="off">0/4000 caracteres' in html
