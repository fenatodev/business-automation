import subprocess


def test_reply_template_search_behavior():
    subprocess.run(["node", "tests/js/reply_template_search.cjs"], check=True)


def test_reply_template_search_controls_are_accessible():
    html = open("app/operator_ui/index.html", encoding="utf-8").read()
    assert 'id="reply-template-search"' in html
    assert 'for="reply-template-search"' in html
    assert 'id="reply-template-search" placeholder="Nome ou conteúdo" autocomplete="off" aria-controls="reply-template-list" aria-describedby="reply-template-filter-status"' in html
    assert 'id="reply-template-search-clear" type="button"' in html
    assert 'id="reply-template-filter-status" class="small" role="status" aria-live="polite"' in html
