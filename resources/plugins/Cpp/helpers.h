#pragma once

typedef struct variable {
    float value;
    const char *unit;
} variable;

typedef struct dataset_entry {
    const char *name;
    variable data;
} dataset_entry;
