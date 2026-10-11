#include <stddef.h>

/* Read UTF-8 lines without CR/LF endings into output[capacity][128].
 * Input lines have at most 127 bytes and fit in capacity rows.
 * Return the line count, or -1 if the file cannot be read. */
int read_lines(const char *path, char output[][128], size_t capacity) {
    (void)path;
    (void)output;
    (void)capacity;
    return 0; /* TODO */
}

#ifndef LETTO_UNIT_TEST
int main(void) {
    char lines[16][128];
    return read_lines("names.txt", lines, 16) == 3 ? 0 : 1;
}
#endif
