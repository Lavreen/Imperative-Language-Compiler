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
# ? 225
# > 15

PROCEDURE sqrt(num) IS
	end, start, mid, guess, check, i
IN
	end := num / 2;
    end := end + 1;
	start := 1;

    i := 0;
    IF num > 1 THEN
        REPEAT
            i := i + 1;
            mid := end + start;
            mid := mid / 2;
            guess := mid * mid;
            
            IF guess > num THEN
                end := mid;
            ENDIF
            IF guess < num THEN
                start := mid;
            ENDIF
            IF i > 70 THEN
                guess := num;
            ENDIF
        UNTIL guess=num; 
    ELSE
        IF num = 1 THEN
            mid := 1;
        ENDIF
    ENDIF
	num := mid;
END	

PROGRAM IS
	i, j
IN
	READ i;
	sqrt(i);
	WRITE i;
END
```

Factorial + Fibonacci:
```
# ? 20
# > 2432902008176640000
# > 6765

PROGRAM IS
    f[100], s[100], i[100], n, j, k, l
IN
    READ n;
    f[0] := 0;
    s[0] := 1;
    i[0] := 0;
    f[1] := 1;
    s[1] := 1;
    i[1] := 1;
    j := 2;
    WHILE j <= n DO
        k := j - 1;
        l := k - 1;
	    i[j] := i[k] + 1;
	    f[j] := f[k] + f[l];
        s[j] := s[k] * i[j];
        j:=j+1;
    ENDWHILE
    WRITE s[n];
    WRITE f[n];
END
```

