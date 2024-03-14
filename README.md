# Imperative-Language-Compiler
A compiler of an imperative language for a simple virtual machine.
The virtual machine was provided by the lecturer and anything inside the /vm folder was NOT written by me.

# Language grammar
![compiler_grammar](https://github.com/Lavreen/Imperative-Language-Compiler/assets/37329745/e1359e9c-9df1-4b05-8fcc-c95ce0b52fe3)

Specification in further details provided by the lecturer in [pdf](https://github.com/Lavreen/Imperative-Language-Compiler/files/14602040/compiler_specification.pdf).

# Requirements
Python 3.11+
[Sly](https://pypi.org/project/sly/)

# Usage
Compilation of a program written in the specified imperative language (.imp file):
```
python3 compiler.py <input.imp> <output.mr>
```
For VM setup use `make`.
Running the compiled program on the VM:
```
./maszyna-wirtualna <program.mr>
```

# Example programs
Binary search for finding square root:
```

```

Factorial + Fibonacci:
```

```

