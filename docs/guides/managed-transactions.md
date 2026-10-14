# Managed applications: transactions and notifications
[中文](managed-transactions.zh-CN.md) · [Manual](../HARNESS.md)

Use type and call-chain analysis for any managed target. The editing, UI and persistence sections apply only when the requested operation has those semantics. For a service, library or batch operation, recover its initialization, receiver, inputs, result and cleanup without creating an editor or transaction it does not use.

## Follow useful types into the business operation

Inventory the actual assembly and runtime, including ReadyToRun/native companions. A managed parser may identify an assembly but fail on large metadata. Retain partial output and use targeted decompilation for candidate types, callers and transaction classes.

Unobfuscated serializers, services or read-only automation components can anchor the route to the required business receiver. Determine whether the method is static, requires a new initialized instance, or must use an existing service/session object. For live editing, follow that owner to the active document: a detached deserialized object is not necessarily the object shown in the application.

Record assembly hash, metadata token/signature, declaring type and binding rules. Obfuscated names and tokens belong to one build. Verify the expected assembly in both the launching process and the in-process bridge where practical.

## Edit through business transactions

Direct property assignment can bypass undo, dirty state, dependent-object updates or notifications. Find the normal mutation path:

1. Read the existing object and the state affected by the operation.
2. Construct the replacement with native constructors/builders and correct document ownership.
3. Create the native edit/command object.
4. Submit it through the editor or workspace transaction API.
5. Query the object and history, then observe dependent state and notifications.

Determine which dependent objects, indexes and derived values the normal operation updates. Reuse that update scope. For a compound operation, establish whether the application groups its mutations into one undo boundary or several.

Views and caches may subscribe to separate model events. Trace subscriptions and notification payloads when state changes without reaching a consumer. Verify the required notifications for the operation and its supported undo/redo paths.

## Preserve object-graph ownership

Complex operations may construct an owned graph of objects. Recover its constructors, factory methods, reference types and installation transaction. Preserve stable IDs and ownership boundaries, and validate referenced objects before submission. Serialization alone may omit runtime registrations and inverse relationships.

For operations that define executable behavior, validate the required branches in the application's execution environment. Exercise invalid references and unsupported expressions as well as successful execution. Keep the generated behavior traceable to its source objects.

## Bridge and UI thread

Use a narrow startup or attachment mechanism appropriate to the runtime. Schedule through the active application's dispatcher. Restrict the delivered bridge to explicit operations and local transports; exploratory reflection remains research tooling.

Keep callbacks/tasks alive through terminal completion. Save before quitting only after committing any pending outer edit, following the native save path. Correlate export completion and inspect the generator's native success result independently of output presence.

## Persistence proof

Retain stable object IDs through save, a different-document switch and reopen. When required, exit the process, start a new one and read those same objects. Confirm further editing still works. Record same-process and cold-start results separately; an in-memory cache can conceal incomplete persistence.

Validate serialized structure and observable behavior independently. Use a reader or runtime appropriate to the output format, and retain source-object references so results can be traced back to editable native state.
