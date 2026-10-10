#include <stddef.h>
#include <stdio.h>
#include <string.h>

int read_lines(const char *path, char output[][128], size_t capacity) {
    FILE *file = fopen(path, "r");
    if (!file) return -1;
    size_t count = 0;
    char line[130];
    while (fgets(line, sizeof line, file)) {
        size_t length = strlen(line);
        while (length && (line[length - 1] == '\n' || line[length - 1] == '\r')) --length;
        if (count == capacity || length >= 128) {
            fclose(file);
            return -1;
        }
        memcpy(output[count], line, length);
        output[count++][length] = '\0';
    }
    int result = ferror(file) ? -1 : (int)count;
    fclose(file);
    return result;
}

#ifndef LETTO_UNIT_TEST
int main(void) {
    char lines[16][128];
    return read_lines("names.txt", lines, 16) == 3 ? 0 : 1;
}
#endif
