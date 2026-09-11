# Splitting the public repos out of the monorepo

`apps/site/` and `apps/examples/` are developed here but published as separate public
repos. Students fork the examples repo and never see this monorepo — which matters,
because this monorepo contains the exercise solutions, the planted-vulnerability repo,
and the platform's secrets handling.

## Why a monorepo at all

The specs, the autograder result contract, and the platform endpoint that consumes it
change together. Keeping them in one history means a change to the contract touches
producer and consumer in a single commit.

## Publishing

`git subtree` rather than submodules — the public repos stay plain checkouts with no
extra steps for students.

```bash
# first publish
git subtree split --prefix=apps/examples -b publish/examples
git push git@github.com:ORG/agentic-web-course.git publish/examples:main

# subsequent updates
git subtree push --prefix=apps/examples examples-remote main
```

The site publishes to GitHub Pages from its own workflow on push to main; see
`apps/site/` for the workflow.

## Before the first publish — check

- [ ] No secrets anywhere in the history being split out, not just the tip. A secret
      committed three commits ago and removed at the tip is still in the split.
- [ ] `solution/` directories contain no real solutions on `main`. Solutions live on a
      branch that merges after the deadline.
- [ ] `08-security/` planted defects are not described anywhere in the public history.
      The defects must survive a casual read; a commit message explaining them defeats
      the exercise.
- [ ] Dependency versions pinned, so a semester-old clone still builds.
