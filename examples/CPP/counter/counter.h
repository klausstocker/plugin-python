#ifndef EXAMPLE_COUNTER_H
#define EXAMPLE_COUNTER_H

#if !defined(__cplusplus) || defined(LETTO_COUNTER_C)
typedef struct Counter { int count; } Counter;
#ifdef __cplusplus
extern "C" {
#endif
void counter_init(Counter *counter);
void counter_increment(Counter *counter);
int counter_value(const Counter *counter);
#ifdef __cplusplus
}
#endif
#else
class Counter {
public:
    Counter();
    void increment();
    int value() const;
private:
    int count_;
};
#endif

#endif
