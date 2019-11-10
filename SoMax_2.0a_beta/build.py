import argparse

from somaxlibrary.CorpusBuilder import CorpusBuilder

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="file to parse")
    args = parser.parse_args()
    fp: str = args.file

    c = CorpusBuilder()
    c.build_corpus(fp)