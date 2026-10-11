#include <stddef.h>

/* Replace the file's contents with each UTF-8 name followed by a newline.
 * Return 0 on success or -1 on a file error. */
int write_names(const char *path, const char *const *names, size_t count) {
    (void)path;
    (void)names;
    (void)count;
    return 0; /* TODO */
}

#ifndef LETTO_UNIT_TEST
int main(void) {
    const char *names[] = {"Ada", "Renée"};
    return write_names("written.txt", names, 2) == 0 ? 0 : 1;
}
#endif
