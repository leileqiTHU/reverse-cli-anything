# WinMD, C++/WinRT and object lifecycle
[中文](winrt-lifecycle.zh-CN.md) · [Manual](../HARNESS.md)

## Metadata is an ABI lead

WinMD can expose interface IDs, method order, signatures and enums even when the implementation is closed-source. Derive candidate vtable positions with inherited interface slots accounted for. Verify HRESULT handling, out parameters, pointer width, value layout and HSTRING conversion. Do not treat a metadata slot candidate as a proven call.

Use targeted native analysis for implementation details absent from metadata. Record which facts came from metadata, disassembly and runtime observation. A whole-module decompiler timeout does not invalidate verified metadata-based work; neither does metadata success imply complete decompilation.

## Obtain genuine objects

Acquire the component or service objects required by the operation through the actual runtime. Distinguish an activation factory from an instance and a resource access object from an arbitrary ID string. Never manufacture access tokens or pretend a stale pointer is a durable identifier. Application, editor or project objects are required only when the selected operation uses them.

For every interface pointer document whether it is borrowed or retained, what release is owed and which lifecycle transition invalidates it. Temporary wrappers can change reference counts. Do not blindly release borrowed pointers or retain every object forever.

Delegate objects and native callbacks need pinned implementations until the application has finished using them. A host that exits after submitting asynchronous work can leave a dangling callback. Session-close should wait for pending callbacks and release them in the observed order.

## Dispatch and edit modes

Determine each interface's apartment and thread requirements. Use the owning dispatcher for thread-affine objects and the runtime's supported marshaling mechanism for cross-apartment access. Do not block a dispatcher on completion work that needs the same dispatcher. Record the application state required for each call.

Units may have both numeric storage and expression representations. Record base units and explicit expression units; do not infer them from the current UI language. Localized parameter labels need discovery, while durable IDs should be preferred for identity.

## Recover lifecycle transitions

Trace the application's callers to recover valid states and transition ordering. For each transition, record its precondition, asynchronous completion signal, newly acquired objects and invalidated handles. Model pending and failed transitions explicitly.

Different services can hold separate representations of an active context. Query their identities after a transition when the operation depends on agreement between them. Reacquire interfaces from their owner instead of reusing pointers across an unverified lifetime boundary.

Investigate dependencies with bounded experiments. If several changes are required for a working sequence, retain the complete supported sequence and its evidence until the dependencies can be isolated.

## Packaged-app boundaries

A path readable by Python may be inaccessible to a packaged app. Probe a valid app-owned staging directory, preserve its actual resolved location and copy final output with byte/hash verification. Do not relabel an external re-render as native output.

Record the package identity, activation state and capabilities needed by the operation. Diagnose an access failure in the application's own context rather than inferring permissions from the controlling process.

## Validate interface results

Check the HRESULT or exception channel, out-parameter initialization, asynchronous terminal state and resulting native state separately. A successful ABI call may only have submitted work.

Verify that returned objects remain usable for their documented lifetime and become invalid at the documented boundary. For persisted or exported results, use the checks defined by the operation's data model and output format.
