from copy import deepcopy

from somaxlibrary.Labels import AbstractLabel


###############################################################################
# AbstractEvent is a encapsulation of a label and and contents.

class AbstractEvent(object):
    def __init__(self, label, contents):
        self.label = label  # supposed to be an AbstractLabel subclass
        self.contents = contents  # supposed to be a AbstractContents subclass

    def __repr__(self):
        return "<Abstract Event with " + self.label.__repr__() + ' and ' + self.contents.__repr__() + '>'

    @classmethod
    def __desc__(self):
        return "Abstract Event"

    def get_label(self):
        return deepcopy(self.label)

    def get_contents(self):
        return deepcopy(self.contents)

    def __eq__(self, a):
        if a == None:
            if self.label == None:
                return True
            else:
                return False
        if isinstance(a, AbstractLabel):
            return self.get_label() == a
        elif isinstance(a, AbstractEvent):
            return self.get_label() == a.get_label()
        else:
            try:
                return self.label == a
            except:
                raise TypeError("Failed comparing " + str(type(self.label)) + " and " + str(type(a)))
