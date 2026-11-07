import subprocess


def test_reply_template_character_count_behavior():
    subprocess.run(["node", "tests/js/reply_template_character_count.cjs"], check=True)


def test_reply_template_character_count_controls_are_present():
    html = open("app/operator_ui/index.html", encoding="utf-8").read()
    assert 'id="reply-template-name-count" class="small" aria-live="off">0/100 caracteres' in html
    assert 'id="reply-template-content-count" class="small" aria-live="off">0/4000 caracteres' in html
    assert 'id="reply-template-name"' in html and 'id="reply-template-name" placeholder="Ex: Saudação inicial" maxlength=' not in html
    assert 'id="reply-template-content"' in html and 'id="reply-template-content" rows="3" placeholder="Texto da resposta..." maxlength=' not in html
