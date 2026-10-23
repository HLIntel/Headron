namespace Bell {
    open Microsoft.Quantum.Intrinsic;

    operation EntangledPair() : (Result, Result) {
        use (a, b) = (Qubit(), Qubit());
        H(a);
        CNOT(a, b);
        return (M(a), M(b));
    }
}
