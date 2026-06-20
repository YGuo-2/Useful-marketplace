---
name: nature-shared-support
description: Internal support content for the Nature skill collection. Do not use as a standalone workflow; load only when another nature-* skill explicitly references files under skills/_shared.
---

# Nature Shared Support

This directory is a shared dependency for the packaged Nature skills. It exists so
relative references such as `../_shared/core/terminology-ledger.md` continue to work.

Do not route user requests here directly. Choose the relevant `nature-*`
entrypoint, then read files from `_shared/` only when that skill's instructions
require them.
