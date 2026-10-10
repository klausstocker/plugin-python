#include <stdio.h>
int read_file(void) {
    FILE *file = fopen("number.txt", "r");
    if (!file)
        return -1;
    int value = 0;
    if (fscanf(file, "%d", &value) != 1) {
        fclose(file);
        return -1;
    }
    fclose(file);
    return value;
}

#ifndef LETTO_UNIT_TEST
int main(void) {
    printf("Number: %d\n", read_file());
    return 0;
}
#endif
