// Bounded chunks: 100 items in chunks of at most 8; the sum proves every chunk ran.
// Run: odin run bounded.odin -file
package main

import "core:fmt"

LIMIT :: 8

main :: proc() {
        n := 100
        total := 0
        i := 0
        for i < n {
                stop := min(i + LIMIT, n)
                for j in i..<stop {
                        total += (j + 1) * 2
                }
                i = stop
        }
        assert(total == 10100, "sum of doubled 1..100")
        fmt.println("bounded: 1 assertion held — 100 items in chunks of at most", LIMIT, ", sum verified")
}
