namespace Bell {
    open Microsoft.Quantum.Intrinsic;
    open Microsoft.Quantum.Diagnostics;

    // The entry point: `dotnet run` in this directory runs it. A Bell pair always
    // measures equal on both qubits, so every shot must agree.
    @EntryPoint()
    operation Main() : Unit {
        mutable agreed = 0;
        for _ in 1..10 {
            let (a, b) = EntangledPair();
            if a == b {
                set agreed += 1;
            }
        }
        Message($"{agreed} of 10 shots agreed");
        EqualityFactI(agreed, 10, "entangled pairs must always agree");
    }
}
