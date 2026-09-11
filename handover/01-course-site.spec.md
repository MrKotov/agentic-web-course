# Spec: course site

One static site that is the textbook, the thing presented in the hall, and the interactive
playground. Public, no login, no student data.

## Goal

A single source of truth for course content, with interactive pieces that make the agent
loop visible rather than described, usable as study material by someone who never attends.

## Non-goals

- No separate slide deck. The site is presented full screen. Maintaining slides and notes
  separately guarantees they diverge.
- No authentication, no student data, no quizzes. Those live in the platform.
- No server. Static output only, so it works from a local file if the hall network fails.

## Stack

Astro with Starlight, content in MDX, interactive pieces as React islands, deployed to
GitHub Pages by Actions on push to main. React Flow (xyflow, MIT) for anything showing a
chain or loop.

## Structure

```
src/content/docs/
  lectures/01-models-and-agents.mdx  ... through 10
  exercises/01-mcp-server.mdx        ... through 05
  reference/conspectus.mdx           exam topics 1-24 with resource links
  reference/tooling.mdx              keys, limits, offline fallback
```

Each lecture page carries: the concepts, the live demo script for the instructor, the
predict-then-reveal prompt with its expected wrong answer, and links to the matching repo
folder.

## Interactive components

Ordered by teaching value, build in this order.

1. **Prompt variance runner.** Same prompt N times, side-by-side diff of returned JSON
   schemas. This is lecture 1 and it is the single most convincing artefact in the course:
   nobody predicts how much drift there is.
2. **Context budget.** Drag files into a window, watch what fits and what falls out.
3. **Tokenizer view.** Text in, token boundaries out. Explains a whole class of model
   behaviour in thirty seconds.
4. **Cost calculator.** Tokens and money for a realistic scenario, model switchable.
5. **Agent loop stepper.** Prompt, tool call, observation, next decision, one step at a
   time, drawn with React Flow. **Check VoltAgent's console first.** If its execution
   traces are good enough to present from, do not build this.
6. **MCP handshake inspector.** Shows tools/list and the selection decision.

## API keys in the browser

Key is entered by the viewer, stored in `localStorage`, sent directly from the browser to
the provider. Never proxied, never logged, never committed.

**Verify before committing to this design:** not every provider allows browser-origin calls.
Test the intended provider from a clean browser early. If CORS blocks it, the fallback is a
thin proxy on a free tier, but that changes who holds the keys and must be reflected in what
students are told.

## Recorded mode

Every interactive component must work with pre-recorded responses and no key. This is not a
nice-to-have: it is what makes the site usable as study material, what saves the lecture
when the hall wifi fails, and what lets a student who never gets a key still follow the
course. Build the recorded path first and the live path second.

## Acceptance criteria

1. Builds to static output and runs correctly opened from disk with no network.
2. Every interactive component renders and is usable in recorded mode with no key present.
3. Presented full screen at 1080p, body text is readable from the back of a lecture hall.
4. Works at 400px wide, because students will read it on phones.
5. Dark and light both render correctly, including the React Flow graphs.
6. No student data is collected anywhere on the site.
