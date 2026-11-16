# Distribution compliance audit — 2026-11-05

Project license: Apache-2.0. Third-party dependency audit: PASS within the package/provenance scope below. Product acceptance remains PARTIAL due to the documented functional and manual-test limits; this audit is not a statement that all acceptance tests passed.

## Inputs and scope

- New original C#/WPF source, tests, installer, chart rendering and 12 original exercise articles; old Typper/Tapper source was not relicensed or copied.
- No application NuGet PackageReference dependencies, no DOC parser, no plotting dependency, no AI/model/weights, no redistributed fonts/images/icons.
- Implicit self-contained runtime packs: Microsoft.NETCore.App.Runtime.win-x64 10.0.14 and Microsoft.WindowsDesktop.App.Runtime.win-x64 10.0.14. Exact NuGet source, SHA-512 content hashes, repository revisions, and file SHA-256 provenance are in SBOM.json.
- Both official NuGet packages passed Microsoft author and NuGet repository signature verification. MIT license declarations read from their actual nuspecs; license originals retained from those same downloaded packages.
- WPF third-party notice text retained from official version tag v10.0.14. Complete .NET runtime and WPF notices are shipped without alteration, including additional permissive grants and copyright statements. The BSD-4 advertising acknowledgement is in NOTICE and README. System Windows DLLs/fonts are not distributed or recharacterized as Apache work.
- Audit.ps1 maps every final portable binary/resource by SHA-256 to official runtime package contents or explicitly identifies original/generated project files; unknown binary files fail packaging. It inventories the complete directory and incorporated notice sections, verifies required legal files, and rejects prohibited license declarations.
- Custom original installer uses the same self-contained runtime packs and embeds the audited portable archive. SDK/tooling is not shipped. No third-party packaging tool is distributed.

## Required legal files

LICENSE (full standard Apache-2.0), NOTICE, THIRD_PARTY_LICENSES.md, licenses/, SBOM.json, this document. User texts/results/private DBs are not licensed or disclosed by the application license.

## Distribution restrictions and remaining validation

No known GPL/AGPL/SSPL, paid commercial, noncommercial-only, or unattributed external application asset dependency is included. Aggregate upstream notices include platform-specific components that may not exist in this Windows runtime; retaining them is intentional. Individual incorporated components keep their original grants and are not relicensed as Apache-2.0.

Builds are unsigned; Windows SmartScreen may prompt. Physical offline, cross-computer, real IME and complete installer UI acceptance are not claimed. See TEST_REPORT.md and package test evidence. The legacy DOC parser is absent and is honestly rejected, not distributed with unverified permission.

## Reproduction

Run build.ps1 with a .NET 10 SDK. It runs core and WPF tests, publishes self-contained files, copies notices, generates SBOM, fails on unmapped files, builds the portable ZIP, and publishes the self-contained installer. Re-run license review when changing runtime/package versions or assets. Release SHA-256 sums are in artifacts/SHA256SUMS.json; source archive is generated separately after reports are complete.
