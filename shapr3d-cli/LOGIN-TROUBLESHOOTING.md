# Browser login succeeds, but Shapr3D reports no internet

Observed on Windows with Shapr3D 26.180.11926.0, 2026-10-13.

## Evidence

- System user proxy is enabled at `127.0.0.1:17891`; the proxy listener is running.
- An ordinary desktop Python process can connect to this endpoint.
- The same TCP connection from inside the running Shapr3D process did not complete within two seconds. The probe sends no HTTP data and reads no credentials.
- Package family: `Shapr3D.Shapr3D_dvv5p1vgwv6mp`.
- Derived AppContainer SID: `S-1-15-2-1833511519-4260088916-3199893069-479427774-4252423879-4191258315-1956449096`.
- That SID is absent from the machine's loopback exemptions.
- Adding the package-specific exemption from the current terminal failed with access denied / administrator required. No exemption was added by this session.

These initial observations supported AppContainer loopback isolation as a cause of the application's failed proxy connection; the subsequent test below confirmed recovery.

**Verified resolution:** the user added the package-specific exemption and logged in successfully. The same in-process TCP probe then connected successfully (`selectResult=1`, `socketError=0`, `connected=true`). The exemption was confirmed in `CheckNetIsolation` output. Modeling validation subsequently proceeded normally.

## Targeted fix

In an administrator PowerShell terminal:

```powershell
CheckNetIsolation.exe LoopbackExempt -a '-n=Shapr3D.Shapr3D_dvv5p1vgwv6mp'
```

Then retry the normal browser login from Shapr3D. If necessary, close and reopen the application first. Do not reset or reinstall it as the first troubleshooting step.

Verify the exemption with `CheckNetIsolation.exe LoopbackExempt -s`. Re-run the in-process TCP probe and verify the application reaches its project dashboard. An exemption alone is not proof that authentication succeeded.

To reverse only this change, use an administrator terminal:

```powershell
CheckNetIsolation.exe LoopbackExempt -d '-n=Shapr3D.Shapr3D_dvv5p1vgwv6mp'
```

No global firewall disabling, credential interception, certificate bypass or license changes are needed for this proposed fix.

Microsoft documents the per-package loopback command and administrator requirement:
https://learn.microsoft.com/en-us/windows/apps/develop/communication/interprocess-communication#loopback

Local diagnostic artifacts: `.local/shapr3d/proxy_diagnostics.py`, `.local/shapr3d/probe_proxy.js`, `.local/shapr3d/proxy-before.json` (relative to the repository root; these are machine-specific and not distribution fixtures).
