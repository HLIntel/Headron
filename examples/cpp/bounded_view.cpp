// A view that REFUSES an out-of-range slice instead of returning a shorter one.
//
// The defect this kills: a slice clamped to what was available, handed back as though it were
// what was asked for. The caller sees a container with elements in it and cannot tell a complete
// answer from a truncated one — the silent break, wearing the shape of success.
//
// Verify: clang++ -std=c++20 -Wall -Wextra -Werror -fsanitize=address,undefined
//         examples/cpp/bounded_view.cpp -o /tmp/bounded_view && /tmp/bounded_view
#include <cassert>
#include <cstddef>
// <cstdio> IS NOT OPTIONAL, and this file passed locally without it. Apple's libc++ pulls it in
// transitively; the runner's standard library does not, so the same source compiled here and
// failed in CI. An absent transitive include is a fact about a standard library, not about the
// program — which is why the runner is the authority and a local green is only evidence.
#include <cstdio>
#include <optional>
#include <span>
#include <vector>

// std::nullopt is the REFUSAL. It is a different type from a short span, so a caller cannot
// accidentally treat "did not fit" as "here is what fitted" — the compiler makes the mistake
// unrepresentable rather than detectable.
static std::optional<std::span<const int>>
slice(std::span<const int> source, std::size_t offset, std::size_t count) {
    if (offset > source.size() || count > source.size() - offset) {
        return std::nullopt;  // never a clamp: the caller decides what a short answer means
    }
    return source.subspan(offset, count);
}

int main() {
    const std::vector<int> data{0, 1, 2, 3, 4, 5, 6, 7};
    const std::span<const int> view{data};

    const auto whole = slice(view, 0, data.size());
    assert(whole.has_value() && whole->size() == data.size());

    const auto middle = slice(view, 2, 3);
    assert(middle.has_value() && middle->size() == 3 && (*middle)[0] == 2 && (*middle)[2] == 4);

    // The three ways a clamp would have lied, each refused instead.
    assert(!slice(view, 0, data.size() + 1).has_value());   // count past the end
    assert(!slice(view, data.size() + 1, 0).has_value());   // offset past the end
    assert(!slice(view, 6, 4).has_value());                 // offset valid, count is not

    // An empty result is a real answer and is NOT a refusal: the two must stay distinguishable.
    const auto empty = slice(view, data.size(), 0);
    assert(empty.has_value() && empty->empty());

    // The overflow a subtraction would have hidden: offset + count wraps, the naive check passes.
    const std::size_t huge = static_cast<std::size_t>(-1);
    assert(!slice(view, 1, huge).has_value());

    std::printf("bounded_view: 7 assertions held — refusal, empty, and an overflow that does not wrap\n");
    return 0;
}
