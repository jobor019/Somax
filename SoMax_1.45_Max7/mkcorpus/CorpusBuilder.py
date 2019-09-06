from string import split
import sys, os, importlib
import logging, settings


class CorpusBuilder:
    """main class to instantiate to achieve corpus construction. Initializes with a path to the files and a corpus name.
        # TODO: Legacy docstring """

    def __init__(self, input_path, corpus_name=None, **kwargs):
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

        self.ops = dict()  # type: {str: (MetaOp, [str])}

        # the CorpusBuilder, at initialization, builds a proposition for the operations to be made.
        # the operation dictionary is a dictionary labelled by suffix containing the files to be analyzed.
        # the operation corresponding to a given suffix will be so executed to whole of the files.
        if os.path.isfile(input_path):
            # if a file, scan the current folder to get the files
            self.ops_keys = self.get_linked_files(self.input_path)
        elif os.path.isdir(input_path):
            # if a folder, scan the given folder with files in it
            os.path.walk(input_path, lambda a, d, n: self.browse_folder(a, d, n), input_path)
        else:
            self.logger.critical("The corpus file(s) were not found! Terminating script without output.")
            sys.exit(1)

        for key, filepaths in self.ops_keys.iteritems():
            op_class = getattr(importlib.import_module("ops"), self.callback_dic[key])
            op_object = op_class(filepaths, self.corpus_name)
            self.ops[key] = (op_object, filepaths)

        self.print_ops_debug()

    def build_corpus(self, output_folder):
        """triggers the corpus computation. This is made in two phases to let the user modify the operations if needed.
            # TODO: This docstring is not necessarily complete or correct"""
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        for key, op_and_paths_tuple in self.ops.iteritems():
            if key != settings.STANDARD_EXT:
                output_file = output_folder + self.corpus_name + '_' + key + '.json'
            else:
                output_file = output_folder + self.corpus_name + '.json'
            for path in op_and_paths_tuple[1]:
                if not os.path.splitext(path)[-1] in op_and_paths_tuple[0].admitted_extensions:
                    # TODO: Handle with logging. Need to cause this error to be able to debug it
                    raise Exception("File " + path + " not understood by operation ", self.callback_dic[key])
            # Run the actual operator
            op_and_paths_tuple[0].process(output_file)

    def print_ops_debug(self):
        output_string = "The following operations were automatically deduced:\n"
        for k, v in self.ops.iteritems():
            output_string += settings.DEBUG_INDENT + '"{0}" for file {1}\n'.format(self.callback_dic[k], v[1])
        self.logger.debug(output_string)

    def browse_folder(self, corpus_path, dirname, names):
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

        self.ops_keys = file_dict

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
                        file_dict[''] = [dir_name + '/' + f]
                else:
                    Op = getattr(importlib.import_module("ops"), self.callback_dic[parts[-1]])
                    if ext in Op.admitted_extensions:
                        file_dict[parts[-1]] = [dir_name + '/' + f]
        self.logger.debug("Relevant files found: {}".format(file_dict))
        return file_dict
