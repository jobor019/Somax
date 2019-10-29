from copy import deepcopy

from somaxlibrary.MergeActions import DistanceMergeAction, PhaseModulationMergeAction
from somaxlibrary.Peak import Peak
from somaxlibrary.Transforms import NoTransform, TransposeTransform


def test_simultaneous_distance_merge():
    d = DistanceMergeAction()
    p1 = Peak(1.0, 0.5, (NoTransform,), 0)
    p2 = Peak(1.0, 0.5, (NoTransform,), 0)
    peaks = [p1, p2]
    merged = d.merge(peaks, _time=0.0)
    assert merged[0].time == 1.0 and merged[0].score == 1.0
    assert len(merged) == 1


def test_close_distance_merge():
    d = DistanceMergeAction()
    p1 = Peak(1.0, 0.5, (NoTransform,), 0)
    p2 = Peak(1.05, 0.5, (NoTransform,), 0)
    peaks = [p1, p2]
    merged = d.merge(peaks, _time=0.0)
    assert merged[0].time == (1.0 + 1.05) / 2 and merged[0].score == 1.0
    assert len(merged) == 1

    d = DistanceMergeAction()
    p1 = Peak(1.0, 1, (NoTransform,), 0)
    p2 = Peak(1.05, 2, (NoTransform,), 0)
    peaks = [p1, p2]
    merged = d.merge(peaks, _time=0.0)
    print(merged)
    assert p1.time < merged[0].time < p2.time and abs(merged[0].time - p1.time) > abs(merged[0].time - p2.time)
    assert merged[0].score == p1.score + p2.score
    assert len(merged) == 1


def test_close_distance_with_transforms():
    d = DistanceMergeAction()
    p1 = Peak(1.0, 0.5, (NoTransform,), 0)
    p2 = Peak(1.025, 0.5, (TransposeTransform(-2),), 0)
    p3 = Peak(1.05, 0.5, (NoTransform,), 0)
    p4 = Peak(1.075, 0.5, (TransposeTransform(-2),), 0)
    peaks = [p1, p2, p3, p4]
    merged = d.merge(peaks, _time=0.0)
    assert len(merged) == 2  # Two peaks: one NoTransform and one TransposeTransform(-2)


def test_close_distance_with_different_transforms():
    d = DistanceMergeAction()
    p1 = Peak(1.0, 0.5, (NoTransform,), 0)
    p2 = Peak(1.025, 0.5, (TransposeTransform(-2),), 0)
    p3 = Peak(1.05, 0.5, (NoTransform,), 0)
    p4 = Peak(1.075, 0.5, (TransposeTransform(-3),), 0)
    peaks = [p1, p2, p3, p4]
    merged = d.merge(peaks, _time=0.0)
    assert len(merged) == 3  # Three peaks: one NoTransform, one TransposeTransform(-2) and one TransposeTransform(-3)


def test_cascade_peaks():
    d = DistanceMergeAction()
    p1 = Peak(1.0, 0.25, (NoTransform,), 0)
    p2 = Peak(1.05, 0.25, (NoTransform,), 0)
    merged = d.merge([p1, p2], _time=0.0)
    # One peak cascaded at 1.025
    assert len(merged) == 1 and merged[0].time == 1.025 and merged[0].score == 0.5
    p3 = Peak(1.05, 0.5, (NoTransform,), 0)
    merged = d.merge([p1, p2, p3], _time=0.0)
    # One peak cascaded at ((1 + 1.05)/2 + 1.05)/2
    assert len(merged) == 1 and merged[0].time == 1.0375

    d = DistanceMergeAction()
    p1 = Peak(1.0, 0.5, (NoTransform,), 0)
    p2 = Peak(1.1, 0.5, (NoTransform,), 0)
    p3 = Peak(1.2, 0.5, (NoTransform,), 0)
    peaks = [p1, p2, p3]
    merged = d.merge(peaks, _time=0.0)
    assert len(merged) == 3


def test_phase_merge():
    d = PhaseModulationMergeAction(1.0)
    p1 = Peak(1.0, 1.0, (NoTransform,), 0)
    p2 = Peak(1.5, 1.0, (NoTransform,), 0)
    p3 = Peak(2.0, 1.0, (NoTransform,), 0)
    merged = d.merge([deepcopy(p1), deepcopy(p2), deepcopy(p3)], 1.5)
    assert p1.score > merged[0].score
    assert p2.score == merged[1].score
    assert p3.score > merged[2].score
    assert merged[0].score < merged[1].score > merged[2].score
