from where_did_my_time_go.rules import AppContext, Rule, apply_rules, match_rule


def test_substring_match_process() -> None:
    rule = Rule(1, True, "substring", "chrome.exe", None, "Video", 1)
    context = AppContext("chrome.exe", "YouTube - Video")
    assert match_rule(rule, context) is True


def test_regex_match_title() -> None:
    rule = Rule(1, True, "regex", None, r"YouTube", "Video", 1)
    context = AppContext("chrome.exe", "YouTube - Video")
    assert match_rule(rule, context) is True


def test_apply_rules_priority() -> None:
    rules = [
        Rule(2, True, "substring", "chrome.exe", None, "Work", 2),
        Rule(1, True, "substring", "chrome.exe", "YouTube", "Video", 1),
    ]
    context = AppContext("chrome.exe", "YouTube - Video")
    assert apply_rules(rules, context) == "Video"
