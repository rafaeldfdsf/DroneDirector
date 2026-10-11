import cv2
import numpy as np


def test_scene_change_never_crossed(tmp_path):
    from services.segmentation import find_candidate_windows
    path = tmp_path / 'scene.mp4'
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'mp4v'), 10, (96, 64))
    for i in range(90):
        writer.write(np.full((64, 96, 3), (20, 30, 40) if i < 40 else (210, 220, 230), np.uint8))
    writer.release()
    windows = find_candidate_windows(path, lambda _: None)
    assert windows
    assert all(not (w['start'] < 3.9 and w['end'] > 4.5) for w in windows)
    assert all(0 < w['end'] - w['start'] <= 8.01 for w in windows)


def test_short_edges_preserved(tmp_path):
    from services.segmentation import find_candidate_windows
    path = tmp_path / 'short.mp4'
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'mp4v'), 10, (96, 64))
    for _ in range(23):
        writer.write(np.full((64, 96, 3), 100, np.uint8))
    writer.release()
    windows = find_candidate_windows(path, lambda _: None)
    assert windows[0]['start'] == 0
    assert abs(windows[-1]['end'] - 2.3) < .01


def test_motion_pause_changes_boundary():
    from services.segmentation import windows_from_samples
    times=list(np.arange(0.,20.,.5))
    speeds=[2. for _ in times]
    speeds[12]=.01
    windows=windows_from_samples(times,[0. for _ in times],speeds,20.)
    assert windows[0]['end']==6.
    assert windows[0]['cutReason']=='Pausa de movimento'


def test_constant_motion_has_bounded_windows():
    from services.segmentation import windows_from_samples
    times=list(np.arange(0.,22.,.5))
    windows=windows_from_samples(times,[0. for _ in times],[2. for _ in times],22.)
    assert windows[0]['start']==0
    assert windows[-1]['end']==22
    assert all(0<w['end']-w['start']<=8 for w in windows)
