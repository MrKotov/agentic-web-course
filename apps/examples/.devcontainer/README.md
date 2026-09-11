# .devcontainer

Identical environment for every student: Node 24.12.0 and Python 3.13 on Ubuntu 24.04.
Base image and both features are pinned by version so a clone made at the end of the
semester still builds the same container.

## Open question — lab machines

Whether the university lab machines can run devcontainers at all is **not settled**
(`handover/06-decisions-and-constraints.md`, open question 1: lab machine policy). A
devcontainer needs a working Docker or Podman daemon and the ability to pull images from
`mcr.microsoft.com` and `ghcr.io`. On a locked-down image any of these can be blocked:

- no container runtime installed, or no permission to start one,
- registry hosts blocked by the proxy,
- no writable space for image layers in the roaming profile.

This has to be tested on a real lab machine before the first lab. It is deliberately left
unresolved here.

**Fallback if the devcontainer cannot run:** everything in `00-setup`, `01-variance` and
`02-mcp-server` uses nothing but the Node standard library and runs on a plain Node 24
install (`nvm install 24.12.0`), and Codespaces runs the same `devcontainer.json` in the
browser on the free tier. Neither fallback is a substitute for testing the real machines.

## Not verified

The container in this directory has **not been built or started**. Docker was not available
on the machine where these files were written. Treat the config as reviewed-but-unrun until
someone builds it.
