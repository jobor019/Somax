from somaxlibrary.Corpus import Corpus
from somaxlibrary.Labels import MelodicLabel, AbstractLabel, HarmonicLabel


def test_melodic_label():
    m = MelodicLabel.classify(128)
    assert type(m) == MelodicLabel and m.label == 128
    m = MelodicLabel.classify(100)
    assert type(m) == MelodicLabel and m.label == 100
    m = MelodicLabel.classify(140)
    assert type(m) == MelodicLabel and m.label == 140

    m = AbstractLabel.classify_as("pitch", 128)
    assert type(m) == MelodicLabel and m.label == 128
    m = AbstractLabel.classify_as("pitch", 100)
    assert type(m) == MelodicLabel and m.label == 100
    m = AbstractLabel.classify_as("pitch", 140)
    assert type(m) == MelodicLabel and m.label == 140

    corpus: Corpus = Corpus("Tests/test.json")
    for event in corpus.events:
        m = MelodicLabel.classify(event)
        assert type(m) == MelodicLabel and m.label == event.pitch


def test_harmonic_label():
    som_classes = HarmonicLabel.SOM_CLASSES
    som_data = HarmonicLabel.SOM_DATA

    results_h1 = []
    results_h2 = []
    for i, chroma in enumerate(som_data):
        h1 = HarmonicLabel.classify(chroma)
        h2 = AbstractLabel.classify_as("chroma", chroma)
        results_h1.append(int(h1.label == som_classes[i]))
        results_h2.append(int(h2.label == som_classes[i]))

    assert sum(results_h1) / len(results_h1) > 0.95
    assert sum(results_h2) / len(results_h2) > 0.95
    assert sum(results_h1) == sum(results_h2)
