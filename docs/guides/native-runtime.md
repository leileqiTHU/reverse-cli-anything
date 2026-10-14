# Native code, internal commands and embedded runtimes
[中文](native-runtime.zh-CN.md) · [Manual](../HARNESS.md)

## Choose the highest useful business entry

Investigate supported automation, internal command dispatch, native services and frontend business handlers. This is a search preference, not a universal precedence rule. A low-level function may be easy to call but omit project registration, material ownership, dirty state or export setup.

An internal help entry establishes syntax clues, not availability in every session mode. Probe a read-only command in the intended mode first. When a command rejects external sessions, inspect how the real frontend creates the business context. Do not force a lower-level mode flag whose invariants are unknown.

Identify creation, registration, activation and destruction as separate lifecycle transitions where the application distinguishes them. Resolve the owning context and readiness after each transition before using acquired objects.

## ABI notebook

For each adopted function record the module hash, RVA or symbol, pointer width, ABI, receiver, return/error convention, parameter sizes/alignment, string encoding and ownership. Apply an RVA to the loaded module base only for its pinned build. A demangled signature or guessed structure offset needs runtime evidence.

Buffers must remain alive for the actual native consumer lifetime. Record whether strings are copied or borrowed, how results are freed and whether callbacks outlive the initiating call. Do not mix C++ strings, Qt values, WinRT handles and plain UTF-8 pointers.

Use metadata and decompiled callers to select a narrow experiment. A one-shot helper is appropriate for an independently owned service; use a retained session where business objects or callbacks outlive a CLI process. A persistent agent host must serialize mutations and reject stale sessions.

## Thread and frontend coordination

Dispatch to the software's established thread mechanism. GUI-thread code must not block waiting for completion that requires that same event loop. Request acceptance, job creation and job completion need separate observations.

After operations that change active context, query business identity and readiness. If a command promises visible synchronization, include the required activation and notification paths and verify the corresponding view state.

## Export is a workflow

A typical export path may involve preparation, options, task creation, a job-specific terminal event, postprocessing and final publication. Bind completion to the requested job and output path. Do not accept an old file, an unrelated job's success event or file existence while writing is ongoing.

Validate temporary output before publishing. Recheck the source document after export; postprocessing can mutate it even after a successful render. If a narrowly scoped runtime guard is necessary, record its pinned module, exact intercepted behavior, restoration and evidence. Avoid broadly suppressing application callbacks.

## Script and protocol paths

For bundled scripts, trace a tool definition through message transport to the live handler; a function name in a bundle is not proof of reachability. Record project/session routing and asynchronous acknowledgments.

For IPC, correlate request IDs and verify sender/receiver identity. For a file-format route, account for concurrent editor writes, native serializers and reload behavior. Offline file modification may be valid, but it must be labeled distinctly from live editing. Avoid direct database writes merely because the format is readable.

## Narrow production surface

Keep exploratory arbitrary-call probes outside the distributed adapter. Expose semantic operations with stable selectors and validated inputs. Report exact unsupported properties or modes instead of silently ignoring them. The adapter's CLI should be usable without knowledge of function addresses.
