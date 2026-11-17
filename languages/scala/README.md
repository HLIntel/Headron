# Scala

**Status:** production

## Purpose
JVM services and data platforms where a typed functional core has to interoperate with the Java ecosystem.

## Why this route exists
It fills the JVM runtime, which no other route in this atlas reached.

## Stack
sbt -> scalafmt -> scalac -> sbt test -> ScalaCheck -> async-profiler.

## Common mistakes
- `null` in Scala code instead of `Option`
- `Await.result` on a request path, turning an async edge into a blocked thread
- the global execution context used for blocking I/O
- implicit conversions used as architecture, making a call site unreadable
- an untyped map crossing a service boundary that a sealed type could have described

The avoid list, boundary contract, verify loop and learning loop live in the [operating card](#operating-card) below.

Official: https://docs.scala-lang.org/

## Operating card

**Route:** JVM services, typed functional cores, data pipelines, Java interop.

**Fast path:** `scalafmt` → `sbt compile` → `sbt test` → property tests on the invariants that matter.

**Native authority:** scalac, sbt, the JVM, and the Scala 3 type system.

**Pair with:** Python for orchestration and analysis; SQL for persistence; Go or Rust where a JVM start-up cost or a GC pause cannot be paid.

**Boundary:** a sealed trait hierarchy or a schema — never an untyped `Map[String, Any]` crossing a service edge.

**Avoid:** `null`, unsafe `asInstanceOf`, implicit conversions as a design tool, `Await.result` on a request path, unbounded `Future` fan-out with the global execution context.

**Reliability:** explicit execution contexts, bounded parallelism, timeouts on every effect, and a back-pressured stream rather than a queue nobody bounded.

**Verify:** the fast path above, every step.

**AI learning loop:** read the types → follow one effect to its edge → change a signature on purpose → test → profile the JVM, never guess at it.

**Research:** https://docs.scala-lang.org/scala3/reference/ · https://docs.scala-lang.org/ · https://www.scala-sbt.org/1.x/docs/
