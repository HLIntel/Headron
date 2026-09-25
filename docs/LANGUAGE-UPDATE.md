# Language Update Protocol

Use this every time a language is added or materially changed.

## Update sequence
1. Verify the official language source.
2. Update the language guide using [docs/LANGUAGE-SPEC.md](LANGUAGE-SPEC.md).
3. Update `languages/ATLAS.md`.
4. Update `docs/PACKAGE-CATALOG.md` if tools changed.
5. Update relevant routing rules.
6. Add one small executable example when the concept is distinctive.
7. Update version only if the repository contract or routing behavior changed.
8. Run link/path consistency checks.

## Required questions
- What problem does this language solve?
- What does the language make safer/easier?
- What does it make harder?
- What is its actual current maturity?
- What are the dangerous defaults?
- What are the common AI-generation mistakes?
- What should the agent verify first?
- What should remain in the host language?

## Do not
- duplicate the same package list in three places
- repeat outdated version claims
- use popularity as the main selection criterion
- call a framework a language
- call an experimental language production-ready
- state benchmark numbers without methodology/source
