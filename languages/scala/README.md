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

The avoid list, boundary contract, verify loop and learning loop live in `OPERATING.md` beside this guide.

Official: https://docs.scala-lang.org/
