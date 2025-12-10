XDATA should not be used anywhere outside registers.h and globals.h unless you absolutely need to. Registers should be defined in the headers and used. Add bit defines as apppropriate also.

Functions and registers should not have names like helper_XXXX or handler_XXXX or reg_XXXX. Give them a name based on what the function or register does, but only if you are confident.

extern void should not be used to call functions. The proper header file should be included.

Remove inline assembly and replace it with C code that does the same thing if possible.
