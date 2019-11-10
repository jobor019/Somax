from Parameter import Parameter


class Parametric:

    def __init__(self):
        self.parameters: {str: Parameter} = {}

    def _parse_parameters(self):
        self.parameters = {k: v for k, v in vars(self).items() if isinstance(v, Parameter)}
