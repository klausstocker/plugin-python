// C++ helpers for Catch2 teacher tests. Include this file from the test source.
#ifndef LETTO_CPP_TEST_HELPERS_C
#define LETTO_CPP_TEST_HELPERS_C

#include <catch2/catch_test_macros.hpp>
#include <cstdio>
#include <iostream>
#include <streambuf>
#include <string>
#include <unistd.h>

// Catch2 reporters may already redirect std::cout to their own stream buffer.
// Route it through stdout so printf and cout share the same captured byte order.
class StdoutBuffer : public std::streambuf {
protected:
    std::streamsize xsputn(const char *text, std::streamsize length) override {
        return static_cast<std::streamsize>(fwrite(text, 1, static_cast<size_t>(length), stdout));
    }
    int_type overflow(int_type ch) override {
        if (traits_type::eq_int_type(ch, traits_type::eof())) return traits_type::not_eof(ch);
        return fputc(traits_type::to_char_type(ch), stdout) == EOF ? traits_type::eof() : ch;
    }
    int sync() override { return fflush(stdout) == 0 ? 0 : -1; }
};

// Restore stdout and cout even if the student function throws an exception.
class CaptureStdout {
    FILE *file_;
    int saved_;
    StdoutBuffer buffer_;
    std::streambuf *saved_cout_;
public:
    CaptureStdout() : file_(tmpfile()), saved_(-1), saved_cout_(nullptr) {
        REQUIRE(file_ != nullptr);
        std::cout.flush();
        fflush(stdout);
        saved_ = dup(fileno(stdout));
        REQUIRE(saved_ >= 0);
        REQUIRE(dup2(fileno(file_), fileno(stdout)) >= 0);
        saved_cout_ = std::cout.rdbuf(&buffer_);
    }
    ~CaptureStdout() {
        std::cout.flush();
        fflush(stdout);
        std::cout.rdbuf(saved_cout_);
        dup2(saved_, fileno(stdout));
        close(saved_);
        fclose(file_);
    }
    std::string text() {
        std::cout.flush();
        fflush(stdout);
        rewind(file_);
        std::string result;
        char buffer[256];
        while (size_t length = fread(buffer, 1, sizeof buffer, file_)) {
            result.append(buffer, length);
        }
        return result;
    }
};

#endif
