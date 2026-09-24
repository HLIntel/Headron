# Scala

**Status:** production

## Purpose
JVM services and data platforms where a typed functional core has to interoperate with the Java ecosystem.

## Why this route exists
It fills the JVM runtime, which no other route in this atlas reached. A language earns a route here only by contributing a distinct guarantee,
runtime property, ecosystem or performance characteristic — not by being popular.

## Stack
sbt -> scalafmt -> scalac -> sbt test -> ScalaCheck -> async-profiler.

## Common mistakes
- `null` in Scala code instead of `Option`
- `Await.result` on a request path, turning an async edge into a blocked thread
- the global execution context used for blocking I/O
- implicit conversions used as architecture, making a call site unreadable
- an untyped map crossing a service boundary that a sealed type could have described

## AI directive
`null`, unsafe `asinstanceof`, implicit conversions as a design tool, `await.result` on a request path, unbounded `future` fan-out with the global execution context — check for these before generating code, and state the
boundary contract (a sealed trait hierarchy or a schema — never an untyped `Map[String, Any]` crossing a service edge) before writing the logic that crosses it.

## Verify
`scalafmt` → `sbt compile` → `sbt test` → property tests on the invariants that matter

## Learn into
read the types → follow one effect to its edge → change a signature on purpose → test → profile the JVM, never guess at it

Official: https://docs.scala-lang.org/
