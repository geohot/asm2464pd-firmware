/*
 * Simple test file for Keil C51 build verification
 */
#include "types.h"
#include "sfr.h"

/* Test function */
void test_func(void)
{
    ACC = 0x55;
    P0 = ACC;
}

/* Main entry */
void main(void)
{
    SP = 0x72;
    test_func();
    while(1);
}
