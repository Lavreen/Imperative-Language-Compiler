class Array:
    def __init__(self, name, memory_offset, size):
        self.name = name
        self.memory_offset = memory_offset
        self.size = size

    def __repr__(self):
        return f"[{self.memory_offset}, {self.size}]"

    def get_at(self, index):
        # print(index)
        if index < self.size:
            return self.memory_offset + index
        else:
            raise Exception(f"Index {index} out of range for array {self.name}")


class Procedure:
    def __init__(self, name, memory_offset, args, commands, local_variables=None):
        self.name = name
        self.memory_offset = memory_offset
        self.args = args
        self.commands = commands
        self.local_variables = local_variables
    

class Variable:
    def __init__(self, memory_offset):
        self.memory_offset = memory_offset
        self.initialized = False

    def __repr__(self):
        return f"{'Uni' if not self.initialized else 'I'}nitialized variable at {self.memory_offset}"


class Symbols(dict):
    def __init__(self):
        super().__init__()
        self.PROC_AFFIX = "__PROCEDURE__"
        self.memory_offset = 0
        self.consts = {}
        self.iterators = {}
        self.proc_args = []
        self.args_decl = set()
        self.proc_vars = set()

    def replace_strings(self, data, old_string, new_string):
        if isinstance(data, tuple):
            modified_data = tuple(self.replace_strings(item, old_string, new_string) for item in data)
            return modified_data
        elif isinstance(data, list):
            modified_data = list(self.replace_strings(item, old_string, new_string) for item in data)
            return modified_data
        elif isinstance(data, str) and data == old_string:
            return new_string
        return data

    def add_proc_vars(self, name):
        self.proc_vars.add(name)

    def add_arg_decl(self, name):
        self.args_decl.add(name)

    def add_procedure(self, name_n_args_decl, commands, local_variables=None):
        name = name_n_args_decl[0]
        args = name_n_args_decl[1]
        offset = self.memory_offset
        self.memory_offset += 1
        if name in self:
            raise Exception(f"Repeated declaration of {name} procedure")
        if local_variables is not None:
            for loc in local_variables:
                if type(loc) is tuple:
                    pid = self.PROC_AFFIX + loc[0] + self.PROC_AFFIX + name
                    self.add_array(pid, loc[1])
                    for i in range(len(commands)):
                        commands[i] = self.replace_strings(commands[i], str(loc[0]), str(pid))
                else:
                    pid = self.PROC_AFFIX + loc + self.PROC_AFFIX + name
                    self.add_variable(pid)
                    for i in range(len(commands)):
                        commands[i] = self.replace_strings(commands[i], str(loc), str(pid))
        self.setdefault(name, Procedure(name, offset, args, commands, local_variables))
      
    def add_variable(self, name, is_proc_arg=False):
        if name in self:
            if not is_proc_arg:
                if name in self.proc_args:
                    self.setdefault(name, Variable(self.memory_offset))
                    self.memory_offset += 1
                else:
                    raise Exception(f"Repeated declaration of {name} variable")
        else:
            self.setdefault(name, Variable(self.memory_offset))
            self.memory_offset += 1

    def add_array(self, name, size, is_proc_arg=False):
        if name in self:
            if not is_proc_arg:
                if name in self.proc_args:
                    self.setdefault(name, Array(name, self.memory_offset, size))
                    self.memory_offset += size + 2
                else:
                    raise Exception(f"Repeated declaration of {name} variable")
        else:
            self.setdefault(name, Array(name, self.memory_offset, size))
            self.memory_offset += size + 2

    def add_constant(self, value):
        self.consts.setdefault(value, self.memory_offset)
        self.memory_offset += 1
        return self.memory_offset - 1

    def get_procedure(self, name):
        if name in self:
            return self[name]
        else:
            raise Exception(f"Undeclared procedure {name}")

    def get_variable(self, name):
        if name in self:
            return self[name]
        else:
            raise Exception(f"Undeclared variable {name}")

    def get_array_at_index(self, name, index):
        if name in self:
            try:
                return self[name].get_at(index)
            except AttributeError:
                raise Exception(f"Not {name} used as an array")
        else:
            raise Exception(f"Undeclared array {name}")

    def get_address(self, target):
        if type(target) is str:
            return self.get_variable(target).memory_offset
        else:
            return self.get_array_at_index(target[0], target[1])

    def get_constant(self, val):
        if val in self.consts:
            return self.consts[val]
