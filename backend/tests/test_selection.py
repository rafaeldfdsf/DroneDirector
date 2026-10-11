from services.scoring import select_segments


def test_quality_beats_source_counts():
    segments = [dict(filename='a', start=0., end=5., score=90.),
                dict(filename='a', start=15., end=20., score=89.),
                dict(filename='b', start=0., end=5., score=10.)]
    assert [s['filename'] for s in select_segments(segments, 10, ['a', 'b'])] == ['a', 'a']


def test_adjacent_allowed_overlap_rejected():
    segments = [dict(filename='a', start=0., end=5., score=90.),
                dict(filename='a', start=4., end=9., score=89.),
                dict(filename='a', start=5., end=10., score=88.)]
    assert [s['start'] for s in select_segments(segments, 10, ['a'])] == [0., 5.]


def test_soft_diversity_on_close_quality():
    segments = [dict(filename=f, start=i*5., end=i*5.+5., score=90.) for f in ['a', 'b'] for i in range(2)]
    assert {s['filename'] for s in select_segments(segments, 10, ['a', 'b'])} == {'a', 'b'}
