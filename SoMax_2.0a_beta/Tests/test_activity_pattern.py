from somaxlibrary.ActivityPattern import ClassicActivityPattern
from somaxlibrary.Corpus import Corpus
from somaxlibrary.CorpusEvent import NoteCorpusEvent
from somaxlibrary.Influence import ClassicInfluence
from somaxlibrary.Transforms import NoTransform


def test_classic_decay():
    corpus: Corpus = Corpus("Tests/test.json")
    event: NoteCorpusEvent = corpus.event_at(0)
    transforms = (NoTransform(),)
    influences = [ClassicInfluence(event, 0, transforms)]
    pattern = ClassicActivityPattern()
    pattern.insert(influences)
    start_time = pattern.peaks[0].time
    start_score = pattern.peaks[0].score

    pattern.update_peaks(1.0)
    assert pattern.peaks[0].time == start_time + 1.0
    updated_score = pattern.peaks[0].score
    assert 0 < updated_score < start_score
    pattern.update_peaks(2.0)
    assert pattern.peaks[0].time == start_time + 2.0
    assert 0 < pattern.peaks[0].score < start_score
    pattern.update_peaks(5.0)
    assert len(pattern.peaks) == 0


def test_classic_decay_two():
    corpus: Corpus = Corpus("Tests/test.json")
    event1: NoteCorpusEvent = corpus.event_at(0)
    event2: NoteCorpusEvent = corpus.event_at(1)
    transforms = (NoTransform(),)
    influence1 = [ClassicInfluence(event1, 0, transforms)]
    influence2 = [ClassicInfluence(event2, 2, transforms)]
    pattern = ClassicActivityPattern()
    pattern.insert(influence1)
    pattern.update_peaks(2.0)
    pattern.insert(influence2)
    assert (len(pattern.peaks) == 2)
    pattern.update_peaks(5.0)
    assert (len(pattern.peaks) == 1)
    pattern.update_peaks(7.0)
    assert (len(pattern.peaks) == 0)
