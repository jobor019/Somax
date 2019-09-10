import subprocess, os

TEST_FILES = ['debussy.json', 'debussy_h.json', 'debussy_m.json']


if __name__ == '__main__':
    for filename in TEST_FILES:
        print 'File: {}:'.format(filename)
        control_file = os.path.normpath(os.getcwd()) + '/' + filename
        test_file = os.path.normpath(os.getcwd()) + '/../../corpus/' + filename
        subprocess.call(['wc', '-c', control_file])
        subprocess.call(['wc', '-c', test_file])