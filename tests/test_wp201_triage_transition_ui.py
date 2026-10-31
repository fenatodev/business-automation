"""WP-201 — Filter triage options based on valid transitions.

The UI now hides/disables triage options that are invalid for the
current opportunity status, preventing the operator from selecting
transitions that the backend would reject (WP-133).
"""


def test_valid_transitions_map_exists():
    """JavaScript has _VALID_TRANSITIONS map in selectOpportunity."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    assert "_VALID_TRANSITIONS" in js


def test_valid_transitions_pending():
    """Pending can transition to follow, ignore, prepare_proposal, in_progress."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    # Find the _VALID_TRANSITIONS block
    start = js.index("_VALID_TRANSITIONS")
    block = js[start:start + 500]
    assert "pending:" in block
    assert '"follow"' in block
    assert '"ignore"' in block
    assert '"prepare_proposal"' in block
    assert '"in_progress"' in block


def test_valid_transitions_terminal_states():
    """Done, lost, and ignore are terminal or restricted."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    start = js.index("_VALID_TRANSITIONS")
    block = js[start:start + 600]
    # done: ["done"] — done only allows staying done
    assert 'done: ["done"]' in block
    # lost: ["lost"] — lost only allows staying lost
    assert 'lost: ["lost"]' in block
    # ignore: ["ignore"] — ignore is terminal
    assert 'ignore: ["ignore"]' in block


def test_option_filtering_uses_hidden_and_disabled():
    """Options are hidden and disabled based on allowed transitions."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    assert "option.hidden" in js
    assert "option.disabled" in js
    assert "allowed.includes(option.value)" in js


def test_clear_selection_resets_options():
    """clearSelection resets option visibility for next selection."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    clear_start = js.index("function clearSelection")
    clear_end = js.index("function disconnect", clear_start)
    clear_block = js[clear_start:clear_end]
    assert "option.hidden = false" in clear_block
    assert "option.disabled = false" in clear_block


def test_select_opportunity_filters_before_setting_value():
    """Options are filtered before setting the select value."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    # Find selectOpportunity function
    sel_start = js.index("async function selectOpportunity")
    sel_end = js.index("async function loadOpportunityConversations", sel_start)
    sel_block = js[sel_start:sel_end]
    # The filter loop should come before setting nextActionSelect.value
    filter_pos = sel_block.index("option.hidden")
    value_pos = sel_block.index("nextActionSelect.value")
    assert filter_pos < value_pos


def test_in_progress_allows_done_and_lost():
    """In progress opportunities can transition to done or lost."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    start = js.index("_VALID_TRANSITIONS")
    block = js[start:start + 600]
    # in_progress: ["in_progress", "done", "lost"]
    assert 'in_progress: ["in_progress", "done", "lost"]' in block


def test_ignore_is_terminal():
    """Ignore state only allows staying in ignore."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    start = js.index("_VALID_TRANSITIONS")
    block = js[start:start + 600]
    assert 'ignore: ["ignore"]' in block


def test_follow_allows_proposal():
    """Follow can transition to prepare_proposal."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    start = js.index("_VALID_TRANSITIONS")
    block = js[start:start + 500]
    follow_start = block.index('"follow"')
    follow_section = block[follow_start:follow_start + 100]
    assert '"prepare_proposal"' in follow_section


def test_prepare_proposal_allows_in_progress():
    """Prepare proposal can transition to in_progress."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    start = js.index("_VALID_TRANSITIONS")
    block = js[start:start + 500]
    prepare_start = block.index('"prepare_proposal"')
    prepare_section = block[prepare_start:prepare_start + 100]
    assert '"in_progress"' in prepare_section


def test_html_has_all_triage_options():
    """HTML triage select has all 7 options."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    triage_start = html.index('id="next-action"')
    triage_end = html.index("</select>", triage_start)
    triage_select = html[triage_start:triage_end]
    for value in ["pending", "follow", "ignore", "prepare_proposal", "in_progress", "done", "lost"]:
        assert f'value="{value}"' in triage_select, f"Missing option: {value}"


def test_backend_valid_transitions_match():
    """Backend _VALID_TRANSITIONS should match the concept in JS."""
    with open("app/routers/opportunities.py") as f:
        py = f.read()
    assert "_VALID_TRANSITIONS" in py
    # Check terminal states
    assert '"done": set()' in py or "'done': set()" in py
    assert '"lost": set()' in py or "'lost': set()" in py
    assert '"ignore": set()' in py or "'ignore': set()" in py


def test_js_transitions_include_self_transition():
    """JS allows staying in current state (self-transition)."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    start = js.index("_VALID_TRANSITIONS")
    block = js[start:start + 600]
    # Each state key should appear in its own array value
    # pending includes "pending"
    assert 'pending: ["pending"' in block
    # follow includes "follow"
    assert 'follow: ["pending", "follow"' in block
    # ignore includes "ignore"
    assert 'ignore: ["ignore"]' in block
    # prepare_proposal includes "prepare_proposal"
    assert 'prepare_proposal: ["pending", "follow", "prepare_proposal"' in block
    # in_progress includes "in_progress"
    assert 'in_progress: ["in_progress"' in block
    # done includes "done"
    assert 'done: ["done"]' in block
    # lost includes "lost"
    assert 'lost: ["lost"]' in block


def test_filter_uses_next_action_select():
    """Filter targets the next-action select element."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    assert 'nextActionSelect' in js or '"next-action"' in js


def test_transition_filter_in_select_opportunity():
    """_VALID_TRANSITIONS is defined inside selectOpportunity."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    sel_start = js.index("async function selectOpportunity")
    sel_end = js.index("async function loadOpportunityConversations", sel_start)
    sel_block = js[sel_start:sel_end]
    assert "_VALID_TRANSITIONS" in sel_block
