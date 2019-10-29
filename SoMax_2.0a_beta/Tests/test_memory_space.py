from somaxlibrary.Corpus import Corpus
from somaxlibrary.Labels import MelodicLabel, HarmonicLabel
from somaxlibrary.MemorySpaces import NGramMemorySpace
from somaxlibrary.Transforms import TransposeTransform


def test_ngram_build_melodic():
    corpus: Corpus = Corpus("Tests/test.json")
    ngram_depth = 3
    memspace: NGramMemorySpace = NGramMemorySpace(corpus, label_type=MelodicLabel, history_len=ngram_depth)
    label_sequence = [e.label(MelodicLabel) for e in corpus.events]

    assert label_sequence
    assert memspace.structured_data
    for i in range(ngram_depth, corpus.length()):
        seq = tuple([label.label for label in label_sequence[i - ngram_depth:i]])
        assert (seq in memspace.structured_data)
        assert (memspace.structured_data[seq][0] == corpus.event_at(i - 1))


def test_ngram_build_harmonic():
    corpus: Corpus = Corpus("Tests/test.json")
    ngram_depth = 3
    memspace: NGramMemorySpace = NGramMemorySpace(corpus, label_type=HarmonicLabel, history_len=ngram_depth)
    label_sequence = [e.label(HarmonicLabel) for e in corpus.events]

    assert label_sequence
    assert memspace.structured_data
    for i in range(ngram_depth, corpus.length()):
        seq = tuple([label.label for label in label_sequence[i - ngram_depth:i]])
        assert (seq in memspace.structured_data)
        assert (memspace.structured_data[seq][0] == corpus.event_at(i - 1))


def test_influence():
    corpus: Corpus = Corpus("Tests/test.json")
    ngram_depth = 3
    memspace: NGramMemorySpace = NGramMemorySpace(corpus, label_type=MelodicLabel, history_len=ngram_depth)

    assert memspace.structured_data
    peaks = memspace.influence(corpus.event_at(1).label(MelodicLabel), 0.0)
    assert not peaks
    peaks = memspace.influence(corpus.event_at(2).label(MelodicLabel), 0.01)
    assert not peaks
    peaks = memspace.influence(corpus.event_at(3).label(MelodicLabel), 0.02)
    assert peaks[0].event.label(MelodicLabel).label == corpus.event_at(3).label(MelodicLabel).label
    assert len(peaks) == 1
    peaks = memspace.influence(corpus.event_at(4).label(MelodicLabel), 0.03)
    assert peaks[0].event.label(MelodicLabel).label == corpus.event_at(4).label(MelodicLabel).label
    assert len(peaks) == 1
    peaks = memspace.influence(corpus.event_at(5).label(MelodicLabel), 0.03)
    assert peaks[0].event.label(MelodicLabel).label == corpus.event_at(5).label(MelodicLabel).label
    assert len(peaks) == 1
    peaks = memspace.influence(corpus.event_at(2).label(MelodicLabel), 0.03)
    assert not peaks


def test_single_transform():
    corpus: Corpus = Corpus("Tests/test.json")
    ngram_depth = 3
    transpose_size = -2
    transforms = [(TransposeTransform(transpose_size),)]
    memspace = NGramMemorySpace(corpus, label_type=MelodicLabel, history_len=ngram_depth, transforms=transforms)
    assert memspace.structured_data
    peaks = memspace.influence(MelodicLabel(70), 0.01)  # first event shifted -2
    assert not peaks
    peaks = memspace.influence(MelodicLabel(72), 0.01)  # second event shifted -2
    assert not peaks
    peaks = memspace.influence(MelodicLabel(74), 0.02)  # third event shifted -2
    # still points at third event:
    assert peaks[0].event.label(MelodicLabel).label == corpus.event_at(3).label(MelodicLabel).label
    assert peaks[0].transforms == (TransposeTransform(transpose_size),)


def test_multiple_sequential_transforms():
    # Should from input C D E match both C D E and F E G
    corpus: Corpus = Corpus("Tests/test.json")
    ngram_depth = 3
    transforms = [(TransposeTransform(i),) for i in range(-6, 6)]  #
    memspace = NGramMemorySpace(corpus, label_type=MelodicLabel, history_len=ngram_depth, transforms=transforms)
    assert memspace.structured_data
    peaks = memspace.influence(MelodicLabel(72), 0.01)
    assert not peaks
    peaks = memspace.influence(MelodicLabel(74), 0.01)
    assert not peaks
    peaks = memspace.influence(MelodicLabel(76), 0.02)
    assert len(peaks) == 2
    assert peaks[0].transforms[0].semitones == -5 or peaks[0].transforms[0].semitones == 0
    assert peaks[1].transforms[0].semitones == -5 or peaks[1].transforms[0].semitones == 0


def test_multiple_parallel_transforms():
    corpus: Corpus = Corpus("Tests/test.json")
    ngram_depth = 3
    transforms = [(TransposeTransform(-3), TransposeTransform(-2))]
    memspace = NGramMemorySpace(corpus, label_type=MelodicLabel, history_len=ngram_depth, transforms=transforms)
    assert memspace.structured_data
    peaks = memspace.influence(MelodicLabel(72), 0.01)
    assert not peaks
    peaks = memspace.influence(MelodicLabel(74), 0.01)
    assert not peaks
    peaks = memspace.influence(MelodicLabel(76), 0.02)
    assert len(peaks) == 1
