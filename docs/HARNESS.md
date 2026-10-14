# Engineering a CLI from a closed-source application

[中文](HARNESS.zh-CN.md) · [Task modes](workflows.md) · [SOP overview](SOP.md)

This is the development manual for the agent doing the work. The user names software and a useful operation set through conversation. The agent investigates, implements and verifies that set, then delivers reusable tools. Installation alone does not start target research. An existing adapter is a starting point when its build and scope match.

Choose the analysis and integration route from the target's shipped artifacts, runtime and required operations. Recover both the call contract and the state transitions needed to execute it reliably.

## 1. Turn the request into an operation set

Write down the actual input, intended native result, constraints and unchanged state. Derive the workflow's constituent operations and dependencies. Identify each operation by its postcondition and ownership scope; similarly named functions may affect different objects or stages of a transaction.

Create a research workspace with [the development tools](development-tools.md). `task.json` records scope, and `operations.json` tracks each requested operation separately. Use the supplied records as working documents, not as forms to hand back to the user.

For each operation record:

- public automation coverage and the concrete missing behavior;
- target object, input units, observable postcondition and unaffected objects;
- execution model, state lifetime, effect (observation, computation or mutation), and prerequisites such as inputs, permissions or session resources;
- current status: planned, researching, implemented, verified or blocked;
- links to the experiment and acceptance evidence; a blocker includes the next missing condition.

Reuse an adequate public interface. Label public calls, recovered internals, file-format operations, external helpers and framework infrastructure separately. An application's closed-source license alone does not prove that a requested operation needs reverse engineering.

**Exit:** a bounded operation set and one meaningful combined workflow. Keep the full request in scope after the first successful experiment.

## 2. Establish the target and research route

Record the build, architecture, relevant artifact hashes, runtime and actual storage paths. Establish readiness for the requested operation: this may require a readable artifact, callable library, initialized process or reachable service. Record activation or session requirements where applicable. A running process alone does not prove readiness, and a headless or offline target need not have a window. Preserve affected user data before mutations or use a dedicated fixture.

Use [reconnaissance](guides/reconnaissance.md) to choose between native analysis, managed decompilation, metadata, packaged scripts, protocols and file formats. Start with a useful clue: command registration, method metadata, an error string, serializer, export service or UI handler. Search from the requested behavior outward. Large-module whole-program analysis is optional; do not repeatedly restart an analysis that cannot finish.

Record tool provenance and coverage. A parser reporting partial metadata is not a completed decompilation. Switching from REA to a targeted decompiler is valid; preserve which tool produced each observation. Normal runtime execution should not need to repeat research.

**Exit:** exact target identity, chosen route, candidate entry points and a first discriminating experiment. Unknown calling conventions remain unknown.

## 3. Recover the complete business operation

Prefer an entry point that preserves the application's invariants. An internal command can be useful, but its name or help text does not establish that it works in the active session mode. Follow the business handler far enough to understand its prerequisites and completion.

Fill an [entry-point card](../templates/research/entrypoint.json) for each adopted entry. Include:

| Concern | What must be established |
| --- | --- |
| Identity | Exact module/build, discovery evidence, receiver acquisition and stable business IDs |
| Call | Argument types, order, encoding, units, layout and calling convention |
| Execution | Required call context, thread or event loop, initialization and applicable session mode |
| Ownership | Borrowed/owned objects, retains/releases, callback and buffer lifetime |
| Business semantics | Result meaning, side effects, consistency and dependent resources; transactions and notifications where used |
| Completion | Request-correlated terminal signal, failure signal and state query |
| Scope | Known unsupported states, version limits, undo and recovery behavior |

Choose the relevant guide: [native and embedded runtimes](guides/native-runtime.md), [managed transactions](guides/managed-transactions.md), or [WinRT and object lifecycle](guides/winrt-lifecycle.md). A target can require more than one route. Never infer arbitrary supported calls from an interface inventory.

**Exit:** enough knowledge for a bounded call on the correct object, including how to observe completion and stop safely if it does not finish.

## 4. Prove a vertical slice

Execute one requested operation through the intended business path with known input and an independent result check. For a query, verify returned values and scope. For a computation, compare a known result and check its output. For a mutation, capture the baseline, read back the change and verify the restoration or persistence required by the task. UI synchronization and undo apply only when the target and operation provide them.

Maintain an experiment record with hypothesis, input, baseline, invocation, observations, counterevidence, outcome and next decision. Useful outcomes include observed, rejected, partial, unknown and not-run. A crashed or hung call is evidence about the candidate, not permission to retry the same mutation.

Keep these observations separate:

1. The bridge accepted the request.
2. The correct native business operation completed.
3. The returned data, computed result or changed state matches the intended postcondition.
4. Other observable surfaces synchronize, when this is part of the task.
5. Required persistent state or generated artifacts contain the result; otherwise record why this layer does not apply.

A single coherent experiment can cover several layers, but a return code cannot substitute for them. When several lifecycle changes jointly resolve a crash, record the successful combination; do not attribute causality to one unisolated change.

**Exit:** one working slice with honest limits. Continue through the rest of the requested operation set.

## 5. Build the target adapter

Use the framework scaffold only after the target and scope are known. Keep the native implementation, version map and dependencies in an independent adapter. Register its manifest using the [adapter contract](adapter-contract.md); adding a target must not add a software-name branch to the core.

A useful separation is:

```text
CLI / schema validation
  → request and target binding
  → narrow bridge / session controller
  → application business operation
  → native observation and correlated result
```

The adapter may use a persistent bridge, a one-shot worker, an existing local service or a file transport. Select by object lifetime and operation semantics. A Python worker can isolate Python failures; it cannot contain a crash in an injected application process.

Implement inspection before broad mutation. Expose stable object IDs and explicit target selectors. Resolve names only when unambiguous. Define units, coordinate systems, source versus destination positions, rounding and unsupported combinations. Validate a complete batch before its first write, then retain per-step results because native batches may be non-atomic.

Production interfaces should expose reviewed operations. Research-only arbitrary reflection/evaluation probes remain in ignored research storage. Keep module guards, native address mapping and ownership logic in the adapter. Do not weaken a build guard just to make a new version run.

**Exit:** callable commands, matching schemas, meaningful errors and observations; development probes are separated from the delivered tool surface.

## 6. Make state and recovery explicit

Use [state and recovery](guides/state-and-recovery.md). Bind requests to the identities the operation actually uses: artifact/input revision, build, process lifetime, job, session or document. A reused PID or matching title is insufficient identity. Invalidate handles after lifecycle transitions according to the target's behavior; stateless operations need no invented project or session.

Use the framework journal for submission, locking and retained receipts. These are not native transactions. Define how each adapter reports rejection before submission, partial changes and unknown outcomes. Preserve input digests, created IDs and completed steps. A timeout does not cancel native work. Read status before deciding whether to resume, compensate or stop.

Treat temporary preview/export changes as writes. Save the relevant baseline, apply temporary state, run the operation and restore only after confirming it is safe. If restoration cannot be confirmed, report that fact and block conflicting writes rather than silently releasing protection.

**Exit:** a later agent can distinguish what was submitted, what is known to have changed and what remains uncertain without blindly repeating the request.

## 7. Verify native results and useful feedback

Follow [verification and observation](guides/verification-and-observation.md) and the [acceptance layers](../acceptance/README.md). Plan the checks before expanding implementation; they should distinguish a correct result from a plausible-looking false positive.

Use small diagnostic fixtures with known values, identifiers, encodings and expected structure. Then, when in scope, use realistic input to expose format variations, numerical limits, dependent resources and compound behavior. Record input provenance. Attribute externally prepared inputs and helper-generated outputs separately from recovered native execution.

For each requested operation, verify its native postcondition and applicable unaffected state. Test the combined workflow through the delivered CLI, with real target behavior and independently inspected output. If persistence is required, distinguish reopening data in the same session from starting a fresh process. Check native editability only when the task requires it; read-only or stateless tasks need no save/reopen cycle.

Record each check's execution time, build, inputs and result. Mark checks without execution evidence as unverified. Evidence from a different build or configuration requires an explicit compatibility assessment. Report structure and hashes establish record integrity; native assertions establish behavior.

**Exit:** operation-level coverage, workflow evidence and explicit unverified or inapplicable items. No promotion from static candidates or scaffold checks to native support.

## 8. Deliver for the next agent

Supply the implementation, manifest, catalog, target Skill, commands, tested builds, dependencies, limitations and recovery instructions. The [documentation generator](development-tools.md) renders the saved catalog and coverage without importing hooks or contacting applications. Review generated instructions and supplement native semantics that a schema cannot express.

Use [delivery and maintenance](guides/delivery.md) to prepare installation, upgrade and handoff. The next agent should be able to discover the commands, identify the required inputs and execution context, inspect readiness, execute the task and check the result. Do not require the original research conversation or transient memory addresses.

Include the dependencies, licenses and required attribution with the deliverable. Keep target binaries, local configuration and working research data outside the distribution.

## Loading map

| Current problem | Read next |
| --- | --- |
| Starting, extending, recovering, upgrading or reviewing | [Task modes](workflows.md) |
| Choosing analysis tools or dealing with incomplete decompilation | [Reconnaissance](guides/reconnaissance.md) |
| Native ABI, Qt/embedded commands, IPC and file formats | [Native/runtime guide](guides/native-runtime.md) |
| .NET object edits, undo, notifications and native output | [Managed guide](guides/managed-transactions.md) |
| WinMD, COM, UI dispatch and project switching | [WinRT guide](guides/winrt-lifecycle.md) |
| Partial writes, timeouts and restoring temporary state | [Recovery guide](guides/state-and-recovery.md) |
| State observations, persistence and independent output checks | [Verification guide](guides/verification-and-observation.md) |
| Installing, generating instructions and supporting a new build | [Delivery guide](guides/delivery.md) |

