from string import split
import sys, os, importlib
import logging, settings
from ops import OpSomaxStandard, OpSomaxHarmonic, OpSomaxMelodic


class CorpusBuilder:
    """main class to instantiate to achieve corpus construction. Initializes with a path to the files and a corpus name.
        # TODO: Legacy docstring """

    # TODO: Force fg, bg, mel, harm as default input arguments (will render legacy unable to compile)
    def __init__(self, input_path, foreground_channels=None, self_bg_channels=None, mel_bg_channels=None,
                 harm_bg_channels=None, corpus_name=None, **kwargs):
        """ Generates a list of files and operations based on existing files in corpus path required for
            building the corpus.
            # TODO: This documentation is not complete nor necessarily correct """

        self.logger = logging.getLogger(settings.MAIN_LOGGER)
        if 'callback_dic' in kwargs.keys():
            self.callback_dic = kwargs["callback_dic"]
        else:
            self.callback_dic = {'': 'OpSomaxStandard', 'h': 'OpSomaxHarmonic', 'm': 'OpSomaxMelodic'}

        self.input_path = str(input_path)
        if corpus_name is None:
            # without explicit corpus name, take the name of the corpus path
            self.corpus_name = os.path.splitext(os.path.basename(input_path))[0]
        else:
            self.corpus_name = corpus_name

        self.logger.debug('Corpus name set to {}'.format(self.corpus_name))

        # TODO: Clean up! This could be simplified a lot!
        # TODO:   If the lambda expression in generate_ops (super ugly) can be removed, ops_filepaths does not have
        # TODO:   to be global. then self.generate_ops could return ops, i.e. self.ops = self.generate_ops().
        self.ops = dict()  # type: {str: (MetaOp, [str])}
        self.ops_filepaths = dict()  # type: {str: [str]}

        self.generate_ops(input_path, foreground_channels, self_bg_channels, mel_bg_channels, harm_bg_channels)
        # self.debug_print_ops()

    def generate_ops(self, input_path, foreground_channels, self_bg_channels, mel_bg_channels, harm_bg_channels):
        """Generates the dict containing the corresponding `MetaOp`s.

           Always adds OpSomaxStandard, OpSomaxMelodic and OpSomaxHarmonic.
           Will check the folder for separate files with names _h or _m, if either of those exist, OpSomaxHarmonic
           and/or OpSomaxMelodic will be generated with these as input files.
           If they don't exist, the default midi file will be used to generate these.
        """
        # the CorpusBuilder, at initialization, builds a proposition for the operations to be made.
        # the operation dictionary is a dictionary labelled by suffix containing the files to be analyzed.
        # the operation corresponding to a given suffix will be so executed to whole of the files.
        # TODO: Move this to the docstring, legacy
        if os.path.isfile(input_path):
            # if a file, scan the current folder to get the files
            self.ops_filepaths = self.get_linked_files(self.input_path)
        elif os.path.isdir(input_path):
            # if a folder, scan the given folder with files in it
            os.path.walk(input_path, lambda a, d, n: self.store_filepaths(a, d, n), input_path)
        else:
            # TODO: This error should have been caught way eariler.
            self.logger.critical("The corpus file(s) were not found! Terminating script without output.")
            sys.exit(1)

        # Dynamic Generation of SomaxOp objects
        for key, filepaths in self.ops_filepaths.iteritems():
            op_class = getattr(importlib.import_module("ops"), self.callback_dic[key])
            op_object = op_class(filepaths, self.corpus_name)
            self.ops[key] = op_object
            self.logger.debug("Added operator {0} related to file(s) {1}".format(self.callback_dic[key], filepaths))

        if settings.MELODIC_FILE_EXT not in self.ops.keys():
            standard_filepaths = self.ops[settings.STANDARD_FILE_EXT].getFilePaths()
            self.ops[settings.MELODIC_FILE_EXT] = OpSomaxMelodic(standard_filepaths, self.corpus_name)
            self.logger.debug("No _m file found. Added Melodic operator based on standard file(s) ({0})."
                              .format(standard_filepaths))
        if settings.HARMONIC_FILE_EXT not in self.ops.keys():
            standard_filepaths = self.ops[settings.STANDARD_FILE_EXT].getFilePaths()
            self.ops[settings.HARMONIC_FILE_EXT] = OpSomaxHarmonic(standard_filepaths, self.corpus_name)
            self.logger.debug("No _h file found. Added Harmonic operator based on based on standard file(s) ({0})."
                              .format(standard_filepaths))

        for key, op in self.ops.iteritems():
            self.set_channels(op, key, foreground_channels, self_bg_channels, mel_bg_channels, harm_bg_channels)

    def set_channels(self, op_object, key, foreground_channels, self_bg_channels, mel_bg_channels, harm_bg_channels):
        op_object.setFgChannels(foreground_channels)
        if key == settings.STANDARD_FILE_EXT:
            op_object.setBgChannels(self_bg_channels)
        if key == settings.MELODIC_FILE_EXT:
            op_object.setBgChannels(mel_bg_channels)
        if key == settings.HARMONIC_FILE_EXT:
            op_object.setBgChannels(harm_bg_channels)

    def build_corpus(self, output_folder):
        """triggers the corpus computation. This is made in two phases to let the user modify the operations if needed.
            # TODO: This docstring is not necessarily complete or correct"""
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        for key, op in self.ops.iteritems():
            if key != settings.STANDARD_FILE_EXT:
                output_file = output_folder + self.corpus_name + '_' + key + '.json'
            else:
                output_file = output_folder + self.corpus_name + '.json'
            for path in op.getFilePaths():
                if not os.path.splitext(path)[-1] in op.admitted_extensions:
                    # TODO: Handle with logging. Need to cause this error to be able to debug it
                    raise Exception("File " + path + " not understood by operation ", self.callback_dic[key])
            # Run the actual operator
            op.process(output_file)

    # TODO: Remove
    # def debug_print_ops(self):
    #     output_string = "The following operations were automatically deduced:\n"
    #     for k, v in self.ops.iteritems():
    #         output_string += settings.DEBUG_INDENT + '"{0}" for file {1}\n'.format(self.callback_dic[k], v)
    #     self.logger.debug(output_string)

    def store_filepaths(self, corpus_path, dirname, names):
        """function called to build the operation dictionary on every file of a folder."""
        # TODO: This has not been checked (2019-09-06)
        names = filter(lambda x: x[0] != '.', names)  # exclude hidden files
        file_dict = dict()
        Op = getattr(importlib.import_module("ops"), self.callback_dic[''])

        main_files = filter(lambda x: len(x.split('_')) == 1 and os.path.splitext(x)[1] in Op.admitted_extensions,
                            names)
        file_dict[''] = map(lambda x: dirname + '/' + x, main_files)
        # looking
        potential_files = filter(
            lambda x: "".join(x.split('_')[:-1]) in map(lambda x: os.path.splitext(x)[0], main_files), names)
        for f in potential_files:
            suffix = os.path.splitext(f)[0].split('_')[-1]
            try:
                file_dict[suffix].append(dirname + '/' + f)
            except KeyError:
                file_dict[suffix] = [dirname + '/' + f]

        # gerer ca!!!
        for k, v in file_dict.iteritems():
            if k != '':
                if len(v) < len(file_dict[""]):
                    print "missing object"
                elif len(v) > len(file_dict[""]):
                    print "too many object"

        self.ops_filepaths = file_dict

    def get_linked_files(self, input_file):
        # TODO: Note: it's currently unclear what the purpose of _h.mid and _m.mid files is. Perhaps, this part could be removed
        dir_name = os.path.dirname(input_file) + '/'
        corpus_name = os.path.splitext(os.path.basename(input_file))[0]
        if '_' in corpus_name:
            self.logger.critical('Invalid name provided for corpus: the midi file must not contain underscores (_). \n'
                                 + settings.CRITICAL_INDENT +
                                 'Note that script should never be run on _h.mid or _m.mid files: these will\n'
                                 + settings.CRITICAL_INDENT +
                                 'automatically be loaded when running the script on the .mid file.\n'
                                 + settings.CRITICAL_INDENT +
                                 'Terminating the script without output.')
            sys.exit(1)

        files = os.listdir(dir_name)
        file_dict = dict()
        for f in files:
            name, ext = os.path.splitext(f)
            parts = split(name, '_')
            if parts[0] == corpus_name:
                if len(parts) == 1:
                    Op = getattr(importlib.import_module("ops"), self.callback_dic[''])
                    if ext in Op.admitted_extensions:
                        file_dict[''] = [dir_name + f]
                else:
                    Op = getattr(importlib.import_module("ops"), self.callback_dic[parts[-1]])
                    if ext in Op.admitted_extensions:
                        file_dict[parts[-1]] = [dir_name + f]
        self.logger.debug("Relevant files found: {}".format(file_dict))
        return file_dict
