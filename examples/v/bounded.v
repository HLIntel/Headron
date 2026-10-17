// Bounded waves: 16 jobs in waves of at most 4; every thread joined, every result collected.
// Run: v run bounded.v
fn worker(id int, ch chan int) {
        ch <- id * 2
}

fn main() {
        limit := 4
        n := 16
        ch := chan int{cap: n}
        mut wave := []thread{}
        for i in 0 .. n {
                if i > 0 && i % limit == 0 {
                        // join the full wave before starting the next: at most `limit` in flight
                        for t in wave {
                                t.wait()
                        }
                        wave = []thread{}
                }
                wave << go worker(i, ch)
        }
        for t in wave {
                t.wait()
        }
        mut total := 0
        for _ in 0 .. n {
                total += <-ch
        }
        // sum of 2*i for i in 0..15 = 240
        assert total == 240
        println('bounded: 1 assertion held — ${n} jobs in waves of at most ${limit}, every thread joined')
}
