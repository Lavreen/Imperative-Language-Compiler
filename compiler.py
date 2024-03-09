from sly import Lexer, Parser
from symbols import Symbols, Array, Variable, Procedure
from append_commands import CommandAppender
import sys


class GoodLexer(Lexer):
    tokens = {PROGRAM, PROCEDURE, IS, IN, WHILE, ENDWHILE, IF, ENDIF, THEN, ELSE, DO, READ, WRITE, LEE, END, REPEAT, UNTIL, PID, NUM, GETS, NEQ, GEQ, LEQ, EQ, GT, LT}
    literals = {'+', '-', '*', '/', '%', ',', ':', ';', '(', ')', '[', ']'}
    ignore = ' \t'

    @_(r'#[^\n]*\n')
    def ignore_comment(self, t):
        self.lineno += t.value.count(r'\n')

    @_(r'\n+')
    def ignore_newline(self, t):
        self.lineno += len(t.value)

    PROGRAM = r"PROGRAM"
    IS = r"IS"
    IN = r"IN"

    PROCEDURE = r"PROCEDURE"
    LEE = r"\bT\b"

    ENDWHILE = r"ENDWHILE"
    ENDIF = r"ENDIF"
    END = r"END"

    WHILE = r"WHILE"
    DO = r"DO"
    IF = r"IF"

    THEN = r"THEN"
    ELSE = r"ELSE"

    REPEAT = r"REPEAT"
    UNTIL = r"UNTIL"

    READ = r"READ"
    WRITE = r"WRITE"

    GETS = r":="
    NEQ = r"!="
    GEQ = r">="
    LEQ = r"<="
    EQ = r"="
    GT = r">"
    LT = r"<"
    PID = r"[_a-z]+"

    @_(r'\d+')
    def NUM(self, t):
        t.value = int(t.value)
        return t

    def error(self, t):
        raise Exception(f"Illegal character '{t.value[0]}'")


class GoodParser(Parser):

    tokens = GoodLexer.tokens
    symbols = Symbols()
    code = None
    consts = set()

    @_('procedures main')
    def program_all(self, p):
        return self.code

    @_('PROGRAM IS declarations IN commands END')
    def main(self, p):
        self.code = CommandAppender(p.commands, self.symbols)
        return self.code

    @_('PROGRAM IS IN commands END')
    def main(self, p):
        self.code = CommandAppender(p.commands, self.symbols)
        return self.code

    @_('procedures PROCEDURE proc_head IS declarations_proc IN commands END')
    def procedures(self, p):
        self.symbols.add_procedure(p[2], p[6], p[4])
        # proc_head, commands, declarations

    @_('procedures PROCEDURE proc_head IS IN commands END')
    def procedures(self, p):
        self.symbols.add_procedure(p[2], p[5])
        # proc_head, commands

    @_('')
    def procedures(self, p):
        pass

    @_('commands command')
    def commands(self, p):
        return p[0] + [p[1]]

    @_('command')
    def commands(self, p):
        return [p[0]]

    @_('identifier GETS expression ";"')
    def command(self, p):
        return "assign", p[0], p[2]

    @_('IF condition THEN commands ELSE commands ENDIF')
    def command(self, p):
        resp = "ifelse", p[1], p[3], p[5], self.consts.copy()
        self.consts.clear()
        return resp

    @_('IF condition THEN commands ENDIF')
    def command(self, p):
        resp = "if", p[1], p[3], self.consts.copy()
        self.consts.clear()
        return resp

    @_('WHILE condition DO commands ENDWHILE')
    def command(self, p):
        resp = "while", p[1], p[3], self.consts.copy()
        self.consts.clear()
        return resp

    @_('REPEAT commands UNTIL condition ";"')
    def command(self, p):
        return "until", p[3], p[1]

    @_('proc_call')
    def command(self, p):
        return "proc_call", p[0]

    @_('READ identifier ";"')
    def command(self, p):
        return "read", p[1]

    @_('WRITE value ";"')
    def command(self, p):
        if p[1][0] == "const":
            self.consts.add(int(p[1][1]))
        return "write", p[1]

    @_('PID "(" args_decl ")"')
    def proc_head(self, p):
        return (p[0], p[2])  # name, args_decl[]

    @_('PID "(" args ")" ";"')  
    def proc_call(self, p):
        if p[0] in self.symbols and type(self.symbols[p[0]]) is Procedure:
            return p[0], p[2]
        else:
            raise Exception(f"Undeclared procedure {p[0]}")

    @_('declarations_proc "," PID')
    def declarations_proc(self, p):
        self.symbols.add_proc_vars(p[2])
        return p[0] + [p[2]]

    @_('declarations_proc "," PID "[" NUM "]" ')
    def declarations_proc(self, p):
        self.symbols.add_proc_vars(p[2])
        return p[0] + [(p[2], p[4])]

    @_('PID')
    def declarations_proc(self, p):
        self.symbols.add_proc_vars(p[0])
        return [p[0]]

    @_('PID "[" NUM "]"')
    def declarations_proc(self, p):
        self.symbols.add_proc_vars(p[0])
        return [(p[0], p(2))]

    @_('declarations "," PID', 'PID')
    def declarations(self, p):
        self.symbols.add_variable(p[-1])

    @_('declarations "," PID "[" NUM "]" ')
    def declarations(self, p):
        self.symbols.add_array(p[2], p[4])

    @_('PID "[" NUM "]"')
    def declarations(self, p):
        self.symbols.add_array(p[0], p[2])

    @_('args_decl "," PID')
    def args_decl(self, p):
        self.symbols.add_arg_decl(p[2])
        return p[0] + [p[2]]

    @_('args_decl "," LEE PID')
    def args_decl(self, p):
        self.symbols.add_arg_decl(p[3])
        return p[0] + [(p[3], "table")]

    @_('PID')
    def args_decl(self, p):
        self.symbols.add_arg_decl(p[0])
        return [p[0]]

    @_('LEE PID')
    def args_decl(self, p):
        self.symbols.add_arg_decl(p[1])
        return [(p[1], "table")]

    @_('args "," PID')
    def args(self, p):
        return p[0] + [p[2]]

    @_('PID')
    def args(self, p):
        return [p[0]]

    @_('value')
    def expression(self, p):
        return p[0]

    @_('value "+" value')
    def expression(self, p):
        return "add", p[0], p[2]

    @_('value "-" value')
    def expression(self, p):
        return "sub", p[0], p[2]

    @_('value "*" value')
    def expression(self, p):
        return "mul", p[0], p[2]

    @_('value "/" value')
    def expression(self, p):
        return "div", p[0], p[2]

    @_('value "%" value')
    def expression(self, p):
        return "mod", p[0], p[2]

    @_('value EQ value')
    def condition(self, p):
        return "eq", p[0], p[2]

    @_('value NEQ value')
    def condition(self, p):
        return "ne", p[0], p[2]

    @_('value LT value')
    def condition(self, p):
        return "lt", p[0], p[2]

    @_('value GT value')
    def condition(self, p):
        return "gt", p[0], p[2]

    @_('value LEQ value')
    def condition(self, p):
        return "le", p[0], p[2]

    @_('value GEQ value')
    def condition(self, p):
        return "ge", p[0], p[2]

    @_('NUM')
    def value(self, p):
        return "const", p[0]

    @_('identifier')
    def value(self, p):
        return "load", p[0]

    @_('PID')
    def identifier(self, p):
        if p[0] in self.symbols or p[0] in self.symbols.args_decl or p[0] in self.symbols.proc_vars:
            return p[0]
        else:
            return "undeclared", p[0]

    @_('PID "[" PID "]"')
    def identifier(self, p):
        if (p[0] in self.symbols or p[0] in self.symbols.proc_args) and type(self.symbols[p[0]]) is Array:
            if p[2] in self.symbols and type(self.symbols[p[2]]) is Variable:
                return "array", p[0], ("load", p[2])
            elif p[0] in self.symbols.args_decl or p[0] in self.symbols.proc_vars:
                return "array", p[0], ("load", p[2])
            else:
                return "array", p[0], ("load", ("undeclared", p[2]))
        elif p[0] in self.symbols.args_decl or p[0] in self.symbols.proc_vars:
            return "array", p[0], ("load", p[2])
        else:
            raise Exception(f"Undeclared array {p[0]}")

    @_('PID "[" NUM "]"')
    def identifier(self, p):
        if p[0] in self.symbols and type(self.symbols[p[0]]) is Array:
            return "array", p[0], p[2]
        elif p[0] in self.symbols.args_decl or p[0] in self.symbols.proc_vars:
            return "array", p[0], p[2]
        else:
            raise Exception(f"Line {self.line_position(self)}:Undeclared array {p[0]}")

    def error(self, token):
        print(self.code)
        raise Exception(f"Syntax error: '{token.value}' in line {token.lineno}")


sys.tracebacklimit = 0
lexed = GoodLexer()
parsed = GoodParser()
with open(sys.argv[1]) as in_f:
    text = in_f.read()

parsed.parse(lexed.tokenize(text))
output = parsed.code
output.output_code()
with open(sys.argv[2], 'w') as out_f:
    for line in output.code:
        print(line, file=out_f)
