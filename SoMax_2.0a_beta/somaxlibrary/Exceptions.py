class InvalidJsonFormat(Exception):
    
    def __init__(self, error):
        super(InvalidJsonFormat, self).__init__(error)
    