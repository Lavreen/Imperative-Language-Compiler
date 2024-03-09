from symbols import Variable, Array
import copy


class CommandAppender:
    def __init__(self, commands, symbols):
        self.commands = commands
        self.symbols = symbols
        self.code = []
        self.PROC_AFFIX = '__PROCEDURE__'
        self.BAK_REG1 = 'g'
        self.BAK_REG2 = 'h'

    def append_command(self, command):
        self.code.append(command)

    def output_code(self):
        self.append_commands(self.commands)
        self.append_command("HALT")

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

    def get_procedure_commands(self, name, variables, symbols):
        proc = symbols.get_procedure(name)
        commands = copy.deepcopy(proc.commands)
        args = proc.args

        mark = "---replaced---"
        if len(args) != len(variables):
            raise Exception(f"Procedure {proc.name} takes {len(args)} arguments. {len(variables)} were given")
        else:
            for i in range(len(args)):
                if type(args[i]) is tuple and type(symbols[variables[i]]) is Array:
                    for j in range(len(commands)):
                        commands[j] = self.replace_strings(commands[j], str(args[i][0]), str(variables[i] + mark))
                elif type(args[i]) is not tuple and type(symbols[variables[i]]) is Variable:
                    for j in range(len(commands)):
                        commands[j] = self.replace_strings(commands[j], str(args[i]), str(variables[i] + mark))
                else:
                    raise Exception("Mismatched types in called procedure arguments")

            for i in range(len(args)):
                for j in range(len(commands)):
                    commands[j] = self.replace_strings(commands[j], str(variables[i] + mark), str(variables[i]))

        return commands

    def append_commands(self, commands):
        for command in commands:
            if command[0] == "proc_call":
                self.append_commands(self.get_procedure_commands(command[1][0], command[1][1], self.symbols))
            elif command[0] == "write":
                value = command[1]
                first_reg = 'c'
                second_reg = 'b'

                if value[0] == "load":
                    if type(value[1]) is tuple:
                        if value[1][0] == "undeclared":
                            var = value[1][1]
                            self.get_variable_address(var, first_reg, declared=False)
                        elif value[1][0] == "array":
                            self.get_array_address(value[1][1], value[1][2], first_reg, second_reg)
                    else:
                        if self.symbols[value[1]].initialized:
                            self.get_variable_address(value[1], first_reg)
                        else:
                            raise Exception(f"Uninitialized variable: {value[1]}")

                elif value[0] == "const":
                    address = self.symbols.get_constant(value[1])
                    if address is None:
                        address = self.symbols.add_constant(value[1])
                        self.generate_constant(address, first_reg)
                        self.generate_constant(value[1], second_reg)
                        self.append_store(second_reg, first_reg)
                    else:
                        self.generate_constant(address, first_reg)
                self.append_command(f"PUT {self.BAK_REG2}")
                self.append_command(f"LOAD {first_reg}")
                self.append_command("WRITE")
                self.append_command(f"GET {self.BAK_REG2}")

            elif command[0] == "read":
                target = command[1]
                first_reg = 'a'
                second_reg = 'b'
                if type(target) is tuple:
                    if target[0] == "undeclared":
                        raise Exception(f"Reading to undeclared variable {target[1]}")
                    elif target[0] == "array":
                        self.get_array_address(target[1], target[2], first_reg, second_reg)
                else:
                    self.get_variable_address(target, first_reg)
                    self.symbols[target].initialized = True
                self.append_command(f"PUT {self.BAK_REG2}")
                self.append_command("READ")
                self.append_command(f"STORE {self.BAK_REG2}")
                self.append_command(f"GET {self.BAK_REG2}")

            elif command[0] == "assign":
                target = command[1]
                expression = command[2]
                second_reg = 'b'
                third_reg = 'c'

                self.calculate_equation(expression)
                if type(target) is tuple:
                    if target[0] == "undeclared":
                        raise Exception(f"Assigning to undeclared variable {target[1]}")
                    elif target[0] == "array":
                        self.get_array_address(target[1], target[2], second_reg, third_reg)
                else:
                    if type(self.symbols[target]) is Variable:
                        self.get_variable_address(target, second_reg)
                        self.symbols[target].initialized = True
                    else:
                        raise Exception(f"Assigning to array {target} with no index provided")
                self.append_command(f"STORE {second_reg}")

            elif command[0] == "if":
                condition = self.reduce_condition(command[1])
                if isinstance(condition, bool):
                    if condition:
                        self.append_commands(command[2])
                else:
                    self.generate_block_constants(command[-1])
                    condition_start = len(self.code)
                    self.calculate_condition(condition)
                    command_start = len(self.code)
                    self.append_commands(command[2])
                    command_end = len(self.code)
                    for i in range(condition_start, command_start):
                        self.code[i] = self.code[i].replace('finish', str(command_end))

            elif command[0] == "ifelse":
                condition = self.reduce_condition(command[1])
                if isinstance(condition, bool):
                    if condition:
                        self.append_commands(command[2])
                    else:
                        self.append_commands(command[3])
                else:
                    self.generate_block_constants(command[-1])
                    condition_start = len(self.code)
                    self.calculate_condition(command[1])
                    if_start = len(self.code)
                    self.append_commands(command[2])
                    self.append_command("JUMP finish")
                    else_start = len(self.code)
                    self.append_commands(command[3])
                    command_end = len(self.code)
                    self.code[else_start - 1] = self.code[else_start - 1].replace('finish', str(command_end))
                    for i in range(condition_start, if_start):
                        self.code[i] = self.code[i].replace('finish', str(else_start))

            elif command[0] == "while":
                condition = self.reduce_condition(command[1])
                if isinstance(condition, bool):
                    if condition:
                        self.generate_block_constants(command[-1])
                        loop_start = len(self.code)
                        self.append_commands(command[2])
                        self.append_command(f"JUMP {loop_start}")
                else:
                    self.generate_block_constants(command[-1])
                    condition_start = len(self.code)
                    self.calculate_condition(command[1])
                    loop_start = len(self.code)
                    self.append_commands(command[2])
                    self.append_command(f"JUMP {condition_start}")
                    loop_end = len(self.code)
                    for i in range(condition_start, loop_start):
                        self.code[i] = self.code[i].replace('finish', str(loop_end))

            elif command[0] == "until":
                loop_start = len(self.code)
                self.append_commands(command[2])
                condition_start = len(self.code)
                self.calculate_condition(command[1])
                condition_end = len(self.code)
                for i in range(condition_start, condition_end):
                    self.code[i] = self.code[i].replace('finish', str(loop_start))

    def generate_constant(self, const, reg='a'):
        self.append_command(f"RST {reg}")
        if const > 0:
            bits = bin(const)[2:]
            for bit in bits[:-1]:
                if bit == '1':
                    self.append_command(f"INC {reg}")
                self.append_command(f"SHL {reg}")
            if bits[-1] == '1':
                self.append_command(f"INC {reg}")

    def calculate_equation(self, expr, reg1='a', reg2='b', reg3='c', reg4='d',
                           reg5='e', reg6='f'):
        if expr[0] == "const":
            self.generate_constant(expr[1], reg1)

        elif expr[0] == "load":
            if type(expr[1]) is tuple:
                if expr[1][0] == "undeclared":
                    self.get_variable(expr[1][1], reg1, declared=False)
                elif expr[1][0] == "array":
                    self.get_array(expr[1][1], expr[1][2], reg1, reg2)
            else:
                if self.symbols[expr[1]].initialized:
                    self.get_variable(expr[1], reg1)
                else:
                    raise Exception(f"Use of uninitialized variable {expr[1]}")

        else:
            if expr[1][0] == 'const':
                const, var = 1, 2
            elif expr[2][0] == 'const':
                const, var = 2, 1
            else:
                const = None

            if expr[0] == "add":
                if expr[1][0] == expr[2][0] == "const":
                    self.generate_constant(expr[1][1] + expr[2][1], reg1)

                elif expr[1] == expr[2]:
                    self.calculate_equation(expr[1], reg5, reg2)
                    self.append_command(f"GET {reg5}")
                    self.append_command(f"ADD {reg5}")

                else:
                    self.calculate_equation(expr[1], reg5, reg2)
                    self.calculate_equation(expr[2], reg6, reg2)
                    self.append_command(f"GET {reg5}")
                    self.append_command(f"ADD {reg6}")

            elif expr[0] == "sub":
                if expr[1][0] == expr[2][0] == "const":
                    val = max(0, expr[1][1] - expr[2][1])
                    if val:
                        self.generate_constant(val, reg1)
                    else:
                        self.append_command(f"RST {reg1}")

                elif expr[1] == expr[2]:
                    self.append_command(f"RST {reg1}")

                elif const and const == 1 and expr[const][1] == 0:
                    self.append_command(f"RST {reg1}")

                else:
                    self.calculate_equation(expr[1], reg5, reg2)
                    self.calculate_equation(expr[2], reg6, reg2)
                    self.append_command(f"GET {reg5}")
                    self.append_command(f"SUB {reg6}")

            elif expr[0] == "mul":
                if expr[1][0] == expr[2][0] == "const":
                    self.generate_constant(expr[1][1] * expr[2][1], reg1)
                    return

                if const:
                    val = expr[const][1]
                    if val == 0:
                        self.append_command(f"RST {reg1}")
                        return

                if expr[1] == expr[2]:
                    self.calculate_equation(expr[1], reg5, reg2)
                    self.append_command(f"GET {reg5}")
                    self.append_command(f"PUT {reg2}")
                    self.append_command(f"PUT {reg3}")
                else:
                    self.calculate_equation(expr[1], reg5, reg2)
                    self.calculate_equation(expr[2], reg6, reg2)
                    self.append_command(f"GET {reg5}")
                    self.append_command(f"PUT {reg2}")
                    self.append_command(f"GET {reg6}")
                    self.append_command(f"PUT {reg3}")

                self.append_command(f"RST {reg5}")
                temp = len(self.code)
                self.append_command(f"GET {reg2}")
                self.append_command(f"PUT {reg6}")
                self.append_command(f"SHR {reg2}")
                self.append_command(f"SHL {reg2}")
                self.append_command(f"GET {reg6}")
                self.append_command(f"SUB {reg2}")
                self.append_command(f"JZERO {len(self.code) + 4}")
                self.append_command(f"GET {reg5}")
                self.append_command(f"ADD {reg3}")
                self.append_command(f"PUT {reg5}")
                self.append_command(f"SHR {reg2}")
                self.append_command(f"SHL {reg3}")
                self.append_command(f"GET {reg2}")
                self.append_command(f"JPOS {temp}")  # nie koncze, jesli jest wiekszy od zera
                self.append_command(f"GET {reg5}")

            elif expr[0] == "div":
                if expr[1][0] == expr[2][0] == "const":
                    if expr[2][1] > 0:
                        self.generate_constant(expr[1][1] // expr[2][1], reg1)
                    else:
                        self.append_command(f"RST {reg1}")
                    return
                elif const and const == 1 and expr[const][1] == 0:
                    self.append_command(f"RST {reg1}")
                    return
                self.calculate_equation(expr[1], reg3, reg2)
                self.calculate_equation(expr[2], reg4, reg2)
                self.calculate_division(reg1, reg2, reg3, reg4, reg5)

            elif expr[0] == "mod":
                if expr[1][0] == expr[2][0] == "const":
                    if expr[2][1] > 0:
                        self.generate_constant(expr[1][1] % expr[2][1], reg1)
                    else:
                        self.append_command(f"RST {reg1}")
                    return

                elif expr[1] == expr[2]:
                    self.append_command(f"RST {reg1}")
                    return

                elif const and const == 1 and expr[const][1] == 0:
                    self.append_command(f"RST {reg1}")
                    return
                self.calculate_equation(expr[1], reg3, reg2)
                self.calculate_equation(expr[2], reg4, reg2)
                self.calculate_division(reg2, reg1, reg3, reg4, reg5)

    def calculate_division(self, quotient_reg='e', remainder_reg='b', dividend_reg='c',
                           divisor_reg='d', temp_reg='a'):
        swapped = None
        if quotient_reg == 'a':
            quotient_reg, temp_reg = temp_reg, quotient_reg
            swapped = quotient_reg
        elif remainder_reg == 'a':
            remainder_reg, temp_reg = temp_reg, remainder_reg
            swapped = remainder_reg

        start = len(self.code)
        self.append_command(f"RST {quotient_reg}")
        self.append_command(f"RST {remainder_reg}")
        self.append_command(f"GET {divisor_reg}")
        self.append_command(f"JZERO finish")
        self.append_command(f"RST {temp_reg}")
        self.append_command(f"ADD {dividend_reg}")
        self.append_command(f"PUT {remainder_reg}")

        self.append_command(f"RST {temp_reg}")
        self.append_command(f"ADD {divisor_reg}")
        self.append_command(f"PUT {dividend_reg}")

        self.append_command(f"RST {temp_reg}")
        self.append_command(f"ADD {remainder_reg}")
        self.append_command(f"SUB {dividend_reg}")

        self.append_command(f"JZERO block_start")
        self.append_command(f"RST {temp_reg}")
        self.append_command(f"ADD {dividend_reg}")
        self.append_command(f"SUB {remainder_reg}")

        self.append_command(f"JZERO {len(self.code) + 3}")
        self.append_command(f"SHR {dividend_reg}")

        self.append_command(f"JUMP {len(self.code) + 3}")
        self.append_command(f"SHL {dividend_reg}")
        self.append_command(f"JUMP {len(self.code) - 7}")

        block_start = len(self.code)
        self.append_command(f"RST {temp_reg}")
        self.append_command(f"ADD {dividend_reg}")
        self.append_command(f"SUB {remainder_reg}")
        self.append_command(f"JZERO {len(self.code) + 2}")
        self.append_command("JUMP finish")
        self.append_command(f"RST {temp_reg}")
        self.append_command(f"GET {remainder_reg}")
        self.append_command(f"SUB {dividend_reg}")
        self.append_command(f"PUT {remainder_reg}")
        self.append_command(f"INC {quotient_reg}")

        midblock_start = len(self.code)
        self.append_command(f"RST {temp_reg}")
        self.append_command(f"ADD {dividend_reg}")
        self.append_command(f"SUB {remainder_reg}")
        self.append_command(f"JZERO block_start")
        self.append_command(f"SHR {dividend_reg}")
        self.append_command(f"RST {temp_reg}")
        self.append_command(f"ADD {divisor_reg}")
        self.append_command(f"SUB {dividend_reg}")
        self.append_command(f"JZERO {len(self.code) + 2}")
        self.append_command("JUMP finish")
        self.append_command(f"SHL {quotient_reg}")
        self.append_command(f"JUMP midblock_start")
        end = len(self.code)

        if swapped is not None:
            self.append_command(f"GET {swapped}")

        for i in range(start, end):
            self.code[i] = self.code[i].replace('midblock_start', str(midblock_start))
            self.code[i] = self.code[i].replace('block_start', str(block_start))
            self.code[i] = self.code[i].replace('finish', str(end))

    def reduce_condition(self, condition):
        if condition[1][0] == "const" and condition[2][0] == "const":
            if condition[0] == "le":
                return condition[1][1] <= condition[2][1]
            elif condition[0] == "ge":
                return condition[1][1] >= condition[2][1]
            elif condition[0] == "lt":
                return condition[1][1] < condition[2][1]
            elif condition[0] == "gt":
                return condition[1][1] > condition[2][1]
            elif condition[0] == "eq":
                return condition[1][1] == condition[2][1]
            elif condition[0] == "ne":
                return condition[1][1] != condition[2][1]

        elif condition[1][0] == "const" and condition[1][1] == 0:
            if condition[0] == "le":
                return True
            elif condition[0] == "gt":
                return False
            else:
                return condition

        elif condition[2][0] == "const" and condition[2][1] == 0:
            if condition[0] == "ge":
                return True
            elif condition[0] == "lt":
                return False
            else:
                return condition

        elif condition[1] == condition[2]:
            if condition[0] in ["ge", "le", "eq"]:
                return True
            else:
                return False

        else:
            return condition

    def calculate_condition(self, cond, reg1='b', reg2='c', reg3='d'):
        if cond[1][0] == "const" and cond[1][1] == 0:
            if cond[0] == "ge" or cond[0] == "eq":
                self.calculate_equation(cond[2], reg1, reg2)
                self.append_command(f"GET {reg1}")
                self.append_command(f"JZERO {len(self.code) + 2}")
                self.append_command("JUMP finish")

            elif cond[0] == "lt" or cond[0] == "ne":
                self.calculate_equation(cond[2], reg1, reg2)
                self.append_command(f"GET {reg1}")
                self.append_command(f"JZERO finish")

        elif cond[2][0] == "const" and cond[2][1] == 0:
            if cond[0] == "le" or cond[0] == "eq":
                self.calculate_equation(cond[1], reg1, reg2)
                self.append_command(f"GET {reg1}")
                self.append_command(f"JZERO {len(self.code) + 2}")
                self.append_command("JUMP finish")

            elif cond[0] == "gt" or cond[0] == "ne":
                self.calculate_equation(cond[1], reg1, reg2)
                self.append_command(f"GET {reg1}")
                self.append_command(f"JZERO finish")

        else:
            self.calculate_equation(cond[1], reg1, reg3)
            self.calculate_equation(cond[2], reg2, reg3)

            if cond[0] == "le":
                self.append_command(f"GET {reg1}")
                self.append_command(f"SUB {reg2}")
                self.append_command(f"PUT {reg1}")
                self.append_command(f"JZERO {len(self.code) + 2}")
                self.append_command("JUMP finish")

            elif cond[0] == "ge":
                self.append_command(f"GET {reg2}")
                self.append_command(f"SUB {reg1}")
                self.append_command(f"PUT {reg2}")
                self.append_command(f"JZERO {len(self.code) + 2}")
                self.append_command("JUMP finish")

            elif cond[0] == "lt":
                self.append_command(f"GET {reg2}")
                self.append_command(f"SUB {reg1}")
                self.append_command(f"PUT {reg2}")
                self.append_command(f"JZERO finish")

            elif cond[0] == "gt":
                self.append_command(f"GET {reg1}")
                self.append_command(f"SUB {reg2}")
                self.append_command(f"PUT {reg1}")
                self.append_command(f"JZERO finish")

            elif cond[0] == "eq":
                self.append_command(f"RST a")
                self.append_command(f"ADD {reg1}")
                self.append_command(f"PUT {reg3}")

                self.append_command(f"GET {reg1}")
                self.append_command(f"SUB {reg2}")
                self.append_command(f"PUT {reg1}")
                self.append_command(f"JZERO {len(self.code) + 2}")
                self.append_command(f"JUMP finish")

                self.append_command(f"GET {reg2}")
                self.append_command(f"SUB {reg3}")
                self.append_command(f"JZERO {len(self.code) + 2}")
                self.append_command(f"JUMP finish")

            elif cond[0] == "ne":
                self.append_command(f"RST {reg3}")
                self.append_add(reg3, reg1)
                self.append_sub(reg1, reg2)
                self.append_command(f"JZERO {len(self.code) + 2}")
                self.append_command(f"JUMP {len(self.code) + 3}")
                self.append_sub(reg2, reg3)
                self.append_command(f"PUT {self.BAK_REG1}")
                self.append_command(f"GET {reg2}")
                self.append_command(f"JZERO finish")
                self.append_command(f"GET {self.BAK_REG1}")

    def append_add(self, reg1, reg2):
        if reg1 == 'a':
            self.append_command(f"ADD {reg2}")
        elif reg2 == 'a':
            self.append_command(f"PUT {self.BAK_REG2}")
            self.append_command(f"GET {reg1}")
            self.append_command(f"ADD {self.BAK_REG2}")
            self.append_command(f"PUT {reg1}")
        else:
            self.append_command(f"GET {reg1}")
            self.append_command(f"ADD {reg2}")
            self.append_command(f"PUT {reg1}")

    def append_sub(self, reg1, reg2):
        if reg1 == 'a':
            self.append_command(f"SUB {reg2}")
        elif reg2 == 'a':
            self.append_command(f"PUT {self.BAK_REG2}")
            self.append_command(f"GET {reg1}")
            self.append_command(f"SUB {self.BAK_REG2}")
            self.append_command(f"PUT {reg1}")
        else:
            self.append_command(f"GET {reg1}")
            self.append_command(f"SUB {reg2}")
            self.append_command(f"PUT {reg1}")

    def append_store(self, reg1, reg2):
        self.append_command(f"PUT {self.BAK_REG2}")
        self.append_command(f"GET {reg1}")
        if reg2 != 'a':
            self.append_command(f"STORE {reg2}")
        else:
            self.append_command(f"STORE {self.BAK_REG2}")
        self.append_command(f"GET {self.BAK_REG2}")

    def get_array_address(self, array, index, reg1, reg2):
        if type(index) is int:
            address = self.symbols.get_address((array, index))
            self.generate_constant(address, reg1)
        elif type(index) is tuple:
            if type(index[1]) is tuple:
                self.get_variable(index[1][1], reg1, declared=False)
            else:
                if not self.symbols[index[1]].initialized:
                    raise Exception(f"Use of {array}({index[1]}) where variable {index[1]} is uninitialized")
                self.get_variable(index[1], reg1)
            var = self.symbols.get_variable(array)
            self.generate_constant(var.memory_offset, reg2)
            self.append_command(f"PUT {self.BAK_REG2}")
            self.append_command(f"GET {reg1}")
            # self.appendCommand(f"WRITE")
            self.append_command(f"ADD {reg2}")
            # self.appendCommand(f"WRITE")
            self.append_command(f"PUT {reg1}")
            self.append_command(f"GET h")

    def get_array(self, array, index, reg1, reg2):
        self.get_array_address(array, index, reg1, reg2)
        if reg1 != 'a':
            self.append_command(f"PUT {self.BAK_REG2}")
        self.append_command(f"LOAD {reg1}")
        if reg1 != 'a':
            self.append_command(f"PUT {reg1}")
            self.append_command(f"GET {self.BAK_REG2}")

    def get_variable(self, name, reg, declared=True):
        self.get_variable_address(name, reg, declared)
        if reg != 'a':
            self.append_command(f"PUT {self.BAK_REG2}")
        self.append_command(f"LOAD {reg}")
        if reg != 'a':
            self.append_command(f"PUT {reg}")
            self.append_command(f"GET {self.BAK_REG2}")

    def get_variable_address(self, name, reg, declared=True):
        if declared:
            address = self.symbols.get_address(name)
            self.generate_constant(address, reg)
        else:
            raise Exception(f"Undeclared variable {name}")

    def generate_block_constants(self, consts, reg1='a', reg2='b'):
        for c in consts:
            address = self.symbols.get_constant(c)
            if address is None:
                address = self.symbols.add_constant(c)
                self.generate_constant(address, reg1)
                self.generate_constant(c, reg2)
                self.append_store(reg2, reg1)
