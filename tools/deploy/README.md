# Deployment toolchain

The API deployment workflow installs this toolchain with `npm ci --prefix
tools/deploy`. It uses Vercel CLI 58.11.0, the version already verified in the
deployment workflow, with every transitive `tar` dependency overridden to
7.5.22. The committed lockfile makes this resolution reproducible instead of
installing an unpinned dependency tree through `npx vercel@58` on each run.

When updating either version, regenerate the lockfile, run `npm ci`, check the
CLI version, and inspect `npm audit --prefix tools/deploy --json` for tar
advisories. A successful deployment and smoke test are still required to
validate deployment compatibility.

This override addresses tar specifically. Other CLI dependency audit findings
and the upstream stream-to-promise deprecation are not resolved by this change.
