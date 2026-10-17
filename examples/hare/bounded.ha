// Bounded chunks: 100 items in chunks of at most 8; the sum proves every chunk ran.
// Run: hare run bounded.ha
use fmt;

export fn main() void = {
        const limit = 8;
        const n = 100;
        let total = 0;
        let i = 0;
        for (i < n) {
                const stop = if (i + limit < n) i + limit else n;
                let j = i;
                for (j < stop) {
                        total += (j + 1) * 2;
                        j += 1;
                };
                i = stop;
        };
        assert(total == 10100);
        fmt::println("bounded: 1 assertion held — 100 items in chunks of at most 8, sum verified")!;
};
