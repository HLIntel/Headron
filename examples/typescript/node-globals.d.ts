// The one Node global this example touches, declared so the project type-checks with no installed
// @types package — the example proves the language and its checker, not a registry download.
declare const process: { exitCode?: number; argv: string[]; exit(code?: number): never };
