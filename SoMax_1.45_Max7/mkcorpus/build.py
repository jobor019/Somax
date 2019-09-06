import os
import argparse
import logging
import settings
from CorpusBuilder import CorpusBuilder


class Main:

    def __init__(self, input_file, output_folder, is_verbose):
        self.logger = self.init_logger(is_verbose)
        self.logger.debug('Script was initialized with the following parameters:\n'
                          'Input file: {0}\n'
                          'Output folder: {1}'.format(input_file, output_folder))
        # TODO: Improve this: Currently only checks if folder is named 'corpus', insufficient verification
        if os.path.normpath(os.path.basename(output_folder)) != settings.CORPUS_FOLDER_NAME:
            self.logger.warn('Output folder is not set to default and will likely not be available inside SoMax, '
                             'is this intentional?\n'
                             'To ensure correct behaviour, please either run the script directly inside\n'
                             'the folder SoMax/corpus or use the -o option to point to this directory.')

        builder = CorpusBuilder(input_file)
        builder.build_corpus(output_folder)

    @staticmethod
    def path_if_valid(path):
        if os.path.exists(path):
            return path
        else:
            raise argparse.ArgumentTypeError('"{0}" is not a valid path'.format(path))

    @staticmethod
    def is_midi_file(path):
        Main.path_if_valid(path)
        _, file_ext = os.path.splitext(path)
        if file_ext in settings.MIDI_FILE:
            return path
        else:
            raise argparse.ArgumentTypeError('"{0}" is not a midi file.'.format(path))

    @staticmethod
    def is_folder(path):
        Main.path_if_valid(path)
        if os.path.isdir(path):
            return path
        else:
            raise argparse.ArgumentTypeError('"{0}" is not a directory file.'.format(path))

    def init_logger(self, is_verbose):
        # TODO: Format logger properly
        logger = logging.getLogger(settings.MAIN_LOG)
        ch = logging.StreamHandler()
        if is_verbose:
            logger.setLevel(logging.DEBUG)
            ch.setLevel(logging.DEBUG)  # Set output logging level, needs to be set twice (?)
        else:
            logger.setLevel(logging.WARNING)
            ch.setLevel(logging.WARNING)
        formatter = logging.Formatter('[%(levelname)s]: %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        return logger


if __name__ == '__main__':
    # TODO: Handle legacy input arguments -i in a meaningful way
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", help="Path to the midi file to parse", type=Main.is_midi_file)
    parser.add_argument("-o", "--output_folder", help="Path to the corpus folder", type=Main.is_folder,
                        default=settings.DEFAULT_CORPUS_PATH)
    parser.add_argument("-v", "--verbose", help="Verbose output", action='store_true', default=True)

    args = parser.parse_args()
    input_file = args.input_file
    output_folder = args.output_folder
    verbose = args.verbose

    Main(input_file, output_folder, verbose)
