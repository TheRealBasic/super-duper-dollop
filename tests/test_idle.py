from where_did_my_time_go.idle import get_idle_status


def test_idle_status_threshold() -> None:
    def idle_func() -> int:
        return 190

    status = get_idle_status(idle_func, 180)
    assert status.is_idle is True
    assert status.idle_seconds == 190


def test_idle_status_active() -> None:
    def idle_func() -> int:
        return 30

    status = get_idle_status(idle_func, 180)
    assert status.is_idle is False
    assert status.idle_seconds == 30
