import os
import argparse
import logging
import settings
import ast
from CorpusBuilder import CorpusBuilder


class Main:
    """ New build script. Designed without support for interactive mode"""

    def __init__(self, input_path, output_folder, is_verbose, foreground, self_bg, mel_bg, harm_bg):
        self.logger = Main.init_logger(is_verbose)

        if not os.path.isabs(input_path):
            input_path = os.path.normpath(os.getcwd() + '/' + input_path)

        self.logger.debug('Script was initialized with the following parameters:\n'
                          + settings.DEBUG_INDENT + 'Input file/folder: {0}\n'.format(input_path)
                          + settings.DEBUG_INDENT + 'Output folder: {0}\n'.format(output_folder)
                          + settings.DEBUG_INDENT + 'Foreground channel(s): {0}\n'.format(foreground)
                          + settings.DEBUG_INDENT + 'Self Background channel(s): {0}\n'.format(self_bg)
                          + settings.DEBUG_INDENT + 'Melodic Background channel(s): {0}\n'.format(mel_bg)
                          + settings.DEBUG_INDENT + 'Harmonic Background channel(s): {0}\n'.format(harm_bg))
        # TODO: Improve this: Currently only checks if folder is named 'corpus', insufficient verification
        if os.path.normpath(os.path.basename(output_folder)) != settings.CORPUS_FOLDER_NAME:
            self.logger.warn('Output folder is not set to default and will likely not be available inside SoMax, '
                             'is this intentional?\n'
                             'To ensure correct behaviour, please either run the script directly inside\n'
                             'the folder SoMax/corpus or use the -o option to point to this directory.')

        builder = CorpusBuilder(input_path, foreground_channels=foreground, self_bg_channels=self_bg,
                                mel_bg_channels=mel_bg, harm_bg_channels=harm_bg)
        builder.build_corpus(os.path.normpath(output_folder) + '/')

    @staticmethod
    def path_if_valid(path):
        if os.path.exists(path):
            return path
        else:
            raise argparse.ArgumentTypeError('"{0}" is not a valid path'.format(path))

    @staticmethod
    def is_midi_file_or_folder(path):
        Main.path_if_valid(path)
        _, file_ext = os.path.splitext(path)
        if file_ext in settings.MIDI_FILE:
            return path
        elif os.path.isdir(path):
            return path
        else:
            raise argparse.ArgumentTypeError('"{0}" is not a midi file or a valid folder.'.format(path))

    @staticmethod
    def is_folder(path):
        Main.path_if_valid(path)
        if os.path.isdir(path):
            return path
        else:
            raise argparse.ArgumentTypeError('"{0}" is not a directory file.'.format(path))

    @staticmethod
    def init_logger(is_verbose):
        # TODO: Format logger properly
        logger = logging.getLogger(settings.MAIN_LOGGER)
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

    @staticmethod
    def parse_list(arg_name, list_as_string):
        """ Note: Parsing brackets from command line is fairly complicated, this function will hence attempt to parse
                  it as a tuple. # TODO: Proper docstring"""
        try:
            maybe_list = ast.literal_eval(list_as_string)
            if isinstance(maybe_list, tuple) and all([isinstance(v, int) for v in maybe_list]):
                return list(maybe_list)
            elif isinstance(maybe_list, int):
                return [maybe_list]
            else:
                Main.throw_list_parse_error(arg_name, list_as_string)
        except (SyntaxError, ValueError) as e:
            Main.throw_list_parse_error(arg_name, list_as_string)

    @staticmethod
    def throw_list_parse_error(arg_name, list_as_string):
        raise argparse.ArgumentTypeError('Error while parsing "{0}": formatting should only be a list of '
                                         'integers without spaces.\n '
                                         'Example: 1,2,3,6\n'
                                         'Your input was: {1}.'.format(arg_name, list_as_string))

    @staticmethod
    def parse_fg(list_as_string):
        return Main.parse_list("Foreground", list_as_string)

    @staticmethod
    def parse_sbg(list_as_string):
        return Main.parse_list("Self Background", list_as_string)

    @staticmethod
    def parse_mbg(list_as_string):
        return Main.parse_list("Melodic Background", list_as_string)

    @staticmethod
    def parse_hbg(list_as_string):
        return Main.parse_list("Harmonic Background", list_as_string)


if __name__ == '__main__':
    # TODO: Handle legacy input arguments -i in a meaningful way
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", help="Path to the midi file or folder to parse", type=Main.is_midi_file_or_folder)
    parser.add_argument("-o", "--output_folder", help="Path to the corpus folder", type=Main.is_folder,
                        default=settings.DEFAULT_CORPUS_PATH)
    parser.add_argument("-v", "--verbose", help="Verbose output", action='store_true', default=False)
    parser.add_argument("-f", "--foreground",
                        help="Specify which midi channel(s) that will be used as foreground"
                             "(output) by Somax. Channels must be specified as a comma separated"
                             "list without spaces.\n"
                             "EXAMPLE: 1,2,8 will result in channels 1, 2 and 8 as output channels.",
                        type=Main.parse_fg, default=settings.DEFAULT_FOREGROUND)
    parser.add_argument("-sb", "--self_bg",
                        help="Specify which midi channel(s) Somax will listen to when mode is set to SELF.\n"
                             "Formatting: see --foreground",
                        type=Main.parse_sbg, default=settings.DEFAULT_SELF_BACKGROUND)
    parser.add_argument("-mb", "--mel_bg",
                        help="Specify which midi channel(s) Somax will listen to when mode is set to MELODIC.\n"
                             "Formatting: see --foreground",
                        type=Main.parse_mbg, default=settings.DEFAULT_MEL_BACKGROUND)
    parser.add_argument("-hb", "--harm_bg",
                        help="Specify which midi channel(s) Somax will listen to when mode is set to HARMONIC.\n"
                             "Formatting: see --foreground",
                        type=Main.parse_hbg, default=settings.DEFAULT_HARM_BACKGROUND)

    args = parser.parse_args()
    input_file = args.input_file
    output_folder = args.output_folder
    verbose = args.verbose
    foreground = args.foreground
    self_bg = args.self_bg
    mel_bg = args.mel_bg
    harm_bg = args.harm_bg

    Main(input_file, output_folder, verbose, foreground, self_bg, mel_bg, harm_bg)
