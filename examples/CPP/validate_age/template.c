/* Return age unchanged, or -1 for a negative age. */
int validate_age(int age) {
    (void)age;
    return 0; /* TODO */
}

#ifndef LETTO_UNIT_TEST
int main(void) { return validate_age(18) == 18 ? 0 : 1; }
#endif
