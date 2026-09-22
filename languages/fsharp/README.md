# F#

**Status:** mature-specialized

## Purpose
Typed domain modeling, data engineering, quantitative work, mathematics-oriented applications, and .NET services.

## Stack
.NET SDK -> F# compiler/FSharp.Core -> FSharp.Data where useful -> FsCheck for properties -> standard .NET profiling/testing.

## Core strengths
Algebraic data types, pattern matching, units of measure, computation expressions, and concise domain models.

## Domain modeling
Use discriminated unions and units of measure to move domain mistakes into compile-time feedback.

## Common mistakes
- excessive computation-expression abstraction
- hidden async blocking
- mutable state leaking across modules
- using F# merely as shorter C# without using the type system

## Streamline
Keep side effects at the edges. Use immutable pipelines and typed records/DU states.

## AI directive
Ask the agent to encode important domain states in types before adding runtime checks.

## Verify
`dotnet build`, `dotnet test`, F# compiler warnings, FsCheck/property tests, and runtime profiling.

Official: https://learn.microsoft.com/dotnet/fsharp/