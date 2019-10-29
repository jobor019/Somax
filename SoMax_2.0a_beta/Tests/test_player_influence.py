from somaxlibrary.ActivityPattern import ClassicActivityPattern
from somaxlibrary.Labels import MelodicLabel
from somaxlibrary.MemorySpaces import NGramMemorySpace
from somaxlibrary.MergeActions import PhaseModulationMergeAction, DistanceMergeAction
from somaxlibrary.Player import Player
from somaxlibrary.Target import CallableTarget
from somaxlibrary.scheduler.ScheduledObject import TriggerMode


def test_player_influence_pitch():
    target = CallableTarget(lambda x: print(x))
    corpus_file = "Tests/test.json"
    fullpath = ["streamview", "atom"]
    p = Player("player", target, TriggerMode.MANUAL)
    p.read_file(corpus_file)
    p.create_streamview([fullpath[0]], 1.0, (DistanceMergeAction, PhaseModulationMergeAction))
    p.create_atom(fullpath, 1.0, MelodicLabel, ClassicActivityPattern, NGramMemorySpace, False)

    p.influence(fullpath, MelodicLabel(72), 0.0)
    p.influence(fullpath, MelodicLabel(74), 0.1)
    p.influence(fullpath, MelodicLabel(76), 0.2)

    assert p.new_event(1.2).label(MelodicLabel).label == 77
    assert p.new_event(2.2).label(MelodicLabel).label == 79
