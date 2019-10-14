class InvalidJsonFormat(Exception):
    
    def __init__(self, error):
        super(InvalidJsonFormat, self).__init__(error)
        
class InvalidLabelInput(Exception):
    
    def __init__(self, error):
        super(InvalidLabelInput, self).__init__(error)
    