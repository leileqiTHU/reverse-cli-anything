# Search keyword library and content audit

Date: 2026-10-16. Source: a user-supplied ChatGPT response to “我有一个闭源软件叫capcut，我希望让agent通过cli操作它，有没有类似的开源仓库可以参考”, followed by a request for its search steps. This is a reported audit, not a raw tool log independently verified here. The original private attachment is not republished.

## Count and provenance

The response lists **six distinct query strings**, although its closing summary claims nine searches. Three additional queries cannot be recovered from the supplied text. Count only the six explicit strings, in their reported order; page opens and result-length settings are not keywords.

| Stage | Added unique queries | Cumulative | Rule |
| --- | ---: | ---: | --- |
| Reported seeds Q01–Q06 | 6 | 6 | Preserve exact strings |
| Same-need expansion Q07–Q24 | 18 | 24 | Outcome, mechanism, interface, compatibility and Chinese phrasing; 4× seed count |
| Other audiences Q25–Q48 | 24 | 48 | Six audience groups, four queries each; 2× previous total |

[Download the UTF-8 CSV](search-keywords.csv). IDs and parent IDs make the expansion traceable. All expanded queries are hypotheses, not search-volume estimates or claims that the repository ranks for them. A destination answers the underlying task; it does not imply support for every term in a broad query. Named competitor queries remain audit evidence, not keywords to insert into product copy.

## What the reported search path tells us

The first reported `web.run` request searches Q01–Q03 with `fast`, default time range and `long` output. The second opens three candidates, then searches Q04–Q06 and specifies `long`. The third opens four more candidates with `short` output. These are the response's labels, not independently verified tool parameters.

The seven reported opens, in order, are:

1. [renezander030/capcut-cli](https://github.com/renezander030/capcut-cli)
2. [GuanYixuan/pyJianYingDraft](https://github.com/GuanYixuan/pyJianYingDraft)
3. [bytedance/UI-TARS](https://github.com/bytedance/UI-TARS)
4. [LHenri88/capcut-mcp](https://github.com/LHenri88/capcut-mcp) — reported 404
5. [JmsLdrn/capcut-mcp README](https://github.com/JmsLdrn/capcut-mcp/blob/main/README.md)
6. [GuanYixuan/pyCapCut](https://github.com/GuanYixuan/pyCapCut)
7. [Microsoft UFO README](https://github.com/microsoft/UFO/blob/main/ufo/README.md)

The source groups solutions as draft editing, MCP and GUI automation, then recommends combining draft and GUI backends. It does not discuss recovering native business operations. Several queries already include candidate names, making them candidate-validation searches rather than neutral discovery. This supports a content gap diagnosis: connect familiar automation tasks to native control, distinguish the agent interface from the backend, and place evidence next to the answer. It does not prove why an engine omitted this repository: indexing, ranking and initial candidate selection remain unknown. We have not revalidated the competing repositories' present capabilities.

## Expansion logic and editorial decisions

Start from audience → desired result → obstacle → plausible query → evidence-backed answer. Expand “CapCut CLI” into importing, trimming, editable captions and native export; expand “MCP” into tool transport versus operation backend; expand “GUI” into alternative routes and lifecycle constraints. Then transfer the task structure to prototype designers, CAD users, agent builders, QA engineers, reverse engineers and maintainers. Chinese entries express user tasks rather than merely repeat product names.

Keep the general closed-source CLI framework as the homepage subject. Improve existing pages rather than create one page per keyword. README task navigation, bilingual FAQ answers, route guidance and application examples should lead to implementations, exact builds and acceptance records. Preserve that CapCut is not verified for Jianying or headless use; Shapr3D is a scoped pilot; a CLI backend does not itself provide an MCP server.

## Keyword inventory

Stage 1 is reported; stages 2 and 3 are inferred. The CSV additionally includes language and intent fields.

| ID | Stage | Parent | Audience | Query | Answer destination |
| --- | --- | --- | --- | --- | --- |
| Q01 | reported | — | video automation | `github CapCut Jianying draft automation python pyJianYingDraft CLI` | [docs/native-automation-examples.md](../docs/native-automation-examples.md) |
| Q02 | reported | — | video automation | `github CapCut desktop automation agent mcp cli` | [docs/native-automation-examples.md](../docs/native-automation-examples.md) |
| Q03 | reported | — | desktop automation | `github desktop GUI automation agent UI-TARS open interpreter computer use playwright pyautogui` | [docs/desktop-automation.md](../docs/desktop-automation.md) |
| Q04 | reported | — | agent integration | `github CapCut MCP server editor draft automation capcut-mcp` | [docs/desktop-automation.md](../docs/desktop-automation.md) |
| Q05 | reported | — | video automation | `github pyCapCut GuanYixuan CapCut draft` | [docs/native-automation-examples.md](../docs/native-automation-examples.md) |
| Q06 | reported | — | Windows automation | `github microsoft UFO desktop agent Windows UI automation accessibility pywinauto` | [docs/desktop-automation.md](../docs/desktop-automation.md) |
| Q07 | intent-expansion | Q01,Q05 | video automation | `CapCut CLI editable timeline native MP4 export open source` | [docs/native-automation-examples.md](../docs/native-automation-examples.md) |
| Q08 | intent-expansion | Q01,Q05 | video automation | `CapCut draft JSON editing vs native editor automation` | [docs/native-automation-examples.md](../docs/native-automation-examples.md) |
| Q09 | intent-expansion | Q01,Q05 | video automation | `Python CapCut automation import trim captions export` | [docs/native-automation-examples.md](../docs/native-automation-examples.md) |
| Q10 | intent-expansion | Q01,Q05 | video automation | `CapCut command line video editing without mouse clicks` | [docs/native-automation-examples.md](../docs/native-automation-examples.md) |
| Q11 | intent-expansion | Q01,Q05 | video automation | `CapCut CLI Jianying compatibility Windows version` | [docs/native-automation-examples.md](../docs/native-automation-examples.md) |
| Q12 | intent-expansion | Q01,Q05 | video automation | `CapCut agent video editing end to end verification` | [docs/native-automation-examples.md](../docs/native-automation-examples.md) |
| Q13 | intent-expansion | Q02,Q04 | agent integration | `open source AI agent CapCut CLI GitHub` | [docs/desktop-automation.md](../docs/desktop-automation.md) |
| Q14 | intent-expansion | Q02,Q04 | agent integration | `CapCut MCP vs CLI native editing backend` | [docs/desktop-automation.md](../docs/desktop-automation.md) |
| Q15 | intent-expansion | Q02,Q04 | agent integration | `CapCut automation agent shell JSON commands` | [docs/desktop-automation.md](../docs/desktop-automation.md) |
| Q16 | intent-expansion | Q02,Q04 | agent integration | `CapCut reverse engineering internal API Frida` | [docs/desktop-automation.md](../docs/desktop-automation.md) |
| Q17 | intent-expansion | Q03,Q06 | desktop automation | `CapCut automation without public API or GUI scripting` | [docs/desktop-automation.md](../docs/desktop-automation.md) |
| Q18 | intent-expansion | Q03,Q06 | desktop automation | `CapCut native automation running editor vs headless` | [docs/desktop-automation.md](../docs/desktop-automation.md) |
| Q19 | intent-expansion | Q01,Q02,Q04 | video automation | `AI Agent 通过 CLI 操作 CapCut 开源仓库` | [docs/native-automation-examples.zh-CN.md](../docs/native-automation-examples.zh-CN.md) |
| Q20 | intent-expansion | Q01,Q02,Q04 | video automation | `CapCut 自动剪辑 添加可编辑字幕 导出 MP4` | [docs/native-automation-examples.zh-CN.md](../docs/native-automation-examples.zh-CN.md) |
| Q21 | intent-expansion | Q01,Q02,Q04 | video automation | `CapCut 草稿编辑和原生接口自动化区别` | [docs/native-automation-examples.zh-CN.md](../docs/native-automation-examples.zh-CN.md) |
| Q22 | intent-expansion | Q01,Q02,Q04 | video automation | `CapCut 没有公开 API 怎么自动化` | [docs/native-automation-examples.zh-CN.md](../docs/native-automation-examples.zh-CN.md) |
| Q23 | intent-expansion | Q01,Q02,Q04 | video automation | `CapCut CLI 是否支持剪映 Jianying` | [docs/native-automation-examples.zh-CN.md](../docs/native-automation-examples.zh-CN.md) |
| Q24 | intent-expansion | Q01,Q02,Q04 | video automation | `CapCut 原生导出 不用鼠标点击` | [docs/native-automation-examples.zh-CN.md](../docs/native-automation-examples.zh-CN.md) |
| Q25 | audience-expansion | Q02,Q08,Q12 | agent builders | `build CLI for closed source desktop software AI agents` | [docs/desktop-automation.md](../docs/desktop-automation.md) |
| Q26 | audience-expansion | Q02,Q08,Q12 | agent builders | `agent tools proprietary application no public API` | [docs/desktop-automation.md](../docs/desktop-automation.md) |
| Q27 | audience-expansion | Q02,Q08,Q12 | agent builders | `MCP tool wrapper for reverse engineered CLI` | [docs/desktop-automation.md](../docs/desktop-automation.md) |
| Q28 | audience-expansion | Q25 | agent builders | `闭源软件没有 API 如何让 Agent 操作` | [docs/desktop-automation.zh-CN.md](../docs/desktop-automation.zh-CN.md) |
| Q29 | audience-expansion | Q03,Q06,Q11 | automation and QA engineers | `desktop RPA vs native application automation` | [docs/desktop-automation.md](../docs/desktop-automation.md) |
| Q30 | audience-expansion | Q03,Q06,Q11 | automation and QA engineers | `verify desktop automation save reopen native export` | [docs/desktop-automation.md](../docs/desktop-automation.md) |
| Q31 | audience-expansion | Q03,Q06,Q11 | automation and QA engineers | `Windows desktop automation internal API without source code` | [docs/desktop-automation.md](../docs/desktop-automation.md) |
| Q32 | audience-expansion | Q29 | automation and QA engineers | `桌面自动化 GUI 点击之外的原生控制方案` | [docs/desktop-automation.zh-CN.md](../docs/desktop-automation.zh-CN.md) |
| Q33 | audience-expansion | Q07,Q11 | prototype designers | `Axure RP CLI AI agent prototype automation` | [docs/native-automation-examples.md](../docs/native-automation-examples.md) |
| Q34 | audience-expansion | Q07,Q11 | prototype designers | `Axure generate interactive HTML command line` | [docs/native-automation-examples.md](../docs/native-automation-examples.md) |
| Q35 | audience-expansion | Q07,Q11 | prototype designers | `Axure automation create pages buttons click interactions` | [docs/native-automation-examples.md](../docs/native-automation-examples.md) |
| Q36 | audience-expansion | Q33 | prototype designers | `Agent 自动生成 Axure 可编辑原型 导出 HTML` | [docs/native-automation-examples.zh-CN.md](../docs/native-automation-examples.zh-CN.md) |
| Q37 | audience-expansion | Q07,Q11 | CAD users | `Shapr3D CLI AI agent CAD automation` | [docs/native-automation-examples.md](../docs/native-automation-examples.md) |
| Q38 | audience-expansion | Q07,Q11 | CAD users | `Shapr3D scripting edit model parameters export STL` | [docs/native-automation-examples.md](../docs/native-automation-examples.md) |
| Q39 | audience-expansion | Q07,Q11 | CAD users | `Shapr3D native mounting plate thickness hole spacing automation` | [docs/native-automation-examples.md](../docs/native-automation-examples.md) |
| Q40 | audience-expansion | Q37 | CAD users | `Shapr3D 自动建模 修改孔距 导出 STL` | [docs/native-automation-examples.zh-CN.md](../docs/native-automation-examples.zh-CN.md) |
| Q41 | audience-expansion | Q16,Q17 | reverse engineers | `wrap reverse engineered internal functions in CLI` | [docs/HARNESS.md](../docs/HARNESS.md) |
| Q42 | audience-expansion | Q16,Q17 | reverse engineers | `Frida native desktop application automation CLI` | [docs/HARNESS.md](../docs/HARNESS.md) |
| Q43 | audience-expansion | Q16,Q17 | reverse engineers | `dotnet desktop automation UI thread native edit transactions` | [docs/HARNESS.md](../docs/HARNESS.md) |
| Q44 | audience-expansion | Q41 | reverse engineers | `逆向闭源软件 内部接口封装 Agent 命令行工具` | [docs/HARNESS.zh-CN.md](../docs/HARNESS.zh-CN.md) |
| Q45 | audience-expansion | Q11,Q18 | adapter maintainers | `maintain reverse engineered CLI after software update` | [docs/workflows.md](../docs/workflows.md) |
| Q46 | audience-expansion | Q11,Q18 | adapter maintainers | `agent reverse engineering research handoff recovery` | [docs/workflows.md](../docs/workflows.md) |
| Q47 | audience-expansion | Q11,Q18 | adapter maintainers | `version pinned desktop adapter workflow acceptance` | [docs/workflows.md](../docs/workflows.md) |
| Q48 | audience-expansion | Q45 | adapter maintainers | `软件升级后逆向 CLI 失效 如何适配验证` | [docs/workflows.zh-CN.md](../docs/workflows.zh-CN.md) |

## Verification and evaluation

Check unique query counts and valid destinations, bilingual parity, page links and fragments, canonical/hreflang metadata and sitemap coverage. Preserve ownership-verification tags and project-level Pages URLs. No paid tool, new hosting project, domain or account-wide crawler setting is required.

For later discovery sampling, use Q07, Q19, Q25, Q28, Q33, Q36, Q37, Q40, Q41 and Q45 as a fixed cross-audience set. Record date, search product, exact query, whether browsing was enabled, returned URL, citation and capability accuracy. Record index coverage separately. Do not claim a ranking gain from edits or from a single model response. See the [search intent plan](search-intent.md) for ongoing evaluation.
