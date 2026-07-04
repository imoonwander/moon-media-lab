from moon_media_lab.media.resolver import plan_cut_times


def test_prefers_silence_midpoint_near_target():
    cuts = plan_cut_times(100.0, 30, [(28.0, 30.0)])
    assert cuts[0] == 29.0


def test_falls_back_to_target_without_silence():
    cuts = plan_cut_times(100.0, 30, [])
    assert cuts == [30.0, 60.0, 90.0]


def test_cuts_are_strictly_increasing():
    cuts = plan_cut_times(200.0, 30, [(28.0, 30.0), (55.0, 56.0), (90.0, 91.0)])
    assert cuts == sorted(cuts)
    assert all(later > earlier for earlier, later in zip(cuts, cuts[1:]))


def test_short_audio_needs_no_cuts():
    assert plan_cut_times(20.0, 30, []) == []
