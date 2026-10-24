// The one Node global this Worker's self-check touches, declared so the project type-checks with no
// installed @types package; the Workers runtime itself has no `process`.
declare const process: { argv: string[] };
