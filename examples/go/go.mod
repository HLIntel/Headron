// A real module, so the example can be vetted, tested and FUZZED rather than only run.
//
// WHY IT EXISTS: OpenSSF Scorecard reported "project is not fuzzed", and the honest way to change
// that is to fuzz something. Go's native fuzzing needs a module; the standard library needs
// nothing else, which is why this file has no require block and never will unless a dependency
// earns one.
module example.com/bounded

go 1.24
