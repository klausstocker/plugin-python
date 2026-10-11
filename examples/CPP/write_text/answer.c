#include <stddef.h>
#include <stdio.h>

int write_names(const char *path, const char *const *names, size_t count) {
    FILE *file = fopen(path, "w");
    if (!file) return -1;
    for (size_t i = 0; i < count; ++i) {
        if (fprintf(file, "%s\n", names[i]) < 0) {
            fclose(file);
            return -1;
        }
    }
    return fclose(file) == 0 ? 0 : -1;
}

#ifndef LETTO_UNIT_TEST
int main(void) {
    const char *names[] = {"Ada", "Renée"};
    return write_names("written.txt", names, 2) == 0 ? 0 : 1;
}
#endif
