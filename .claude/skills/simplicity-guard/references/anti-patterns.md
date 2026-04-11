# Anti-patterns — what NOT to create

**Read this file before writing any code in this project.** These rules override your defaults. Your defaults were trained on enterprise codebases and blog posts; this project is not that.

## Verbatim from GSD-2 VISION.md (MIT-licensed; attributed to gsd-build/gsd-2)

**Enterprise patterns.** Dependency injection containers, abstract factories, strategy-pattern-for-the-sake-of-it, over-engineered config systems. This is not a Spring application.

**Framework swaps.** Rewriting working code in a different library or framework without a clear, measurable improvement. "I prefer X" is not sufficient motivation.

**Cosmetic refactors.** Renaming variables to your preferred style, reordering imports, reformatting code that works. This is pure churn that creates merge conflicts and review burden for zero user value.

**Complexity without user value.** If a change adds abstraction, indirection, or configuration but doesn't improve something a user can see or feel, it doesn't belong here.

**Heavy orchestration layers.** Don't duplicate what the agent infrastructure already provides. Build on top of it, don't wrap it.

## mikrós additions

**No interface with a single implementation.** If there is one impl, inline it. Interfaces earn their place when there are at least two consumers and a real reason to swap.

**No dataclass for internal data.** Use dicts or tuples unless validation is required. A 17-field dataclass for a result object is a code smell, not a solution.

**No nested config > 1 level deep.** Flat structures win. `config.database.pool.max_size` → `config.db_pool_max_size`.

**No directory depth > 2 in small projects.** `src/` plus one level. Anything deeper has to earn its place.

**Three-strikes rule.** Do not create an abstraction until you have three concrete uses of the pattern. Duplication of two is acceptable; three is the signal.

**No new file without justification.** If the code fits in an existing file, it goes there. New files are a cost, not a benefit.

**Boring is a feature.** Clever code loses to boring code that the next reader (human or AI) can understand in ten seconds.

## The iron rule

**A task must fit in one context window. If it can't, split the task, don't compress the context.**

This is the single operational test for task granularity in mikrós. There is no judgment call.
