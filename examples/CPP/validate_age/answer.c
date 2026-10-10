int validate_age(int age) { return age < 0 ? -1 : age; }

#ifndef LETTO_UNIT_TEST
int main(void) { return validate_age(18) == 18 ? 0 : 1; }
#endif
