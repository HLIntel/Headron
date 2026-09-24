/* A read with a DECLARED cap, and a refusal instead of a truncation.
 *
 * The defect this kills: a fixed buffer filled by a length the caller controls, returning success
 * with a silently truncated result. Truncation that reports success is the silent break — the
 * caller cannot tell a short answer from a complete one.
 *
 * Verify: clang -std=c17 -Wall -Wextra -Werror -fsanitize=address,undefined examples/c/bounded_read.c
 *         -o /tmp/bounded_read && /tmp/bounded_read
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>

enum { CAPACITY = 16 };

/* Returns the number of bytes copied, or -1 when the input does not FIT. Never a partial copy
 * reported as a whole one. */
static int copy_bounded(char *out, size_t out_size, const char *in) {
    size_t needed = strlen(in) + 1;
    if (needed > out_size) {
        return -1; /* refuse: the caller decides what to do with an input that does not fit */
    }
    memcpy(out, in, needed);
    return (int)(needed - 1);
}

int main(void) {
    char buffer[CAPACITY];

    assert(copy_bounded(buffer, sizeof buffer, "fits") == 4);
    assert(strcmp(buffer, "fits") == 0);

    /* The case a truncating implementation would report as success. */
    assert(copy_bounded(buffer, sizeof buffer, "far longer than the capacity") == -1);
    assert(strcmp(buffer, "fits") == 0); /* and it did not touch the buffer on refusal */

    puts("bounded_read: 3 assertions held — a refusal is not a truncation");
    return 0;
}
