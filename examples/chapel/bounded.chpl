/* Bounded data-parallel map: double 1..n with a forall, then prove the sum.
   Run: chpl bounded.chpl -o bounded && ./bounded */
config const n = 100;

var doubled: [1..n] int;
forall i in 1..n do
  doubled[i] = i * 2;

const total = + reduce doubled;
assert(total == n * (n + 1), "sum of doubled 1..n");
writeln("bounded: 1 assertion held — ", n, " items mapped in parallel, sum verified");
