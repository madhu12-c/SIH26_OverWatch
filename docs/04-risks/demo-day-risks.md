# Demo day risks

Everything that can go wrong on stage, and the fallback for each.

**The governing principle:** a broken demo erases everything the deck built, and
there is no recovering from it in the room. Every dependency that *can* be removed
before Tuesday *should* be.

---

## The rules

1. **No live AI call in the demo path.** Ever. Specs are pre-extracted to JSON;
   the demo reads the file.
2. **No server, no backend, no localhost.** The React build opens from a file.
3. **No first-time downloads on venue wifi.** Everything cached in advance.
4. **Test the built folder, not the dev server.** `npm run dev` working proves
   nothing about `dist/index.html`.

---

## Risk table

| # | What | Likelihood | Fallback |
|---|---|---|---|
| 1 | Venue wifi dead or captive-portal | **High** | Nothing needs the network. Verified by running everything in airplane mode. |
| 2 | Gemini rate-limited or down | Medium | No live call exists. `specs.json` is committed. |
| 3 | React build shows a blank page | **High if `base` unset** | `base: './'` in `vite.config.js`. Test by double-clicking `dist/index.html`. |
| 4 | Laptop sleeps / display fails | Medium | Phone copy of the same build, saved locally. Works offline. |
| 5 | Projector resolution mangles layout | Medium | Responsive layout; test at 1024×768 before the day. |
| 6 | Embedding model downloads on first run | High if unprepared | Run `embed.py` once on the demo laptop beforehand. |
| 7 | Someone regenerates data and forgets `results.json` | Medium | Regenerate and re-verify the morning of. Checklist item. |
| 8 | Wrong Python or missing package on the demo machine | Medium | The demo does not run Python at all. It is a built HTML folder. |
| 9 | Nerves — presenter loses the thread | Medium | Screen order *is* the script. Follow the five screens. |
| 10 | Time limit shorter than rehearsed | **Unknown — still unconfirmed** | Know which two screens to cut: 04 and 05. Never cut 02. |

---

## ⚠️ Still unconfirmed

**Is a live demo allowed, and how many minutes do we get?**

This has been open since the start and everything about rehearsal depends on it.
Madhu to confirm with the SPOC.

Plan for both: a 3-minute version (screens 01, 02, 03) and a 6-minute version (all
five).

---

## The morning-of checklist

Run this on the actual demo machine, with **wifi turned off**.

```
[ ] wifi OFF
[ ] open dist/index.html by double-clicking      -> loads, no blank page
[ ] all five screens render
[ ] screen 02 animation plays, replay button works
[ ] numbers on screen match the numbers in the deck
[ ] phone copy opens, comparison is readable stacked
[ ] laptop charged, charger present
[ ] projector tested at venue resolution
[ ] backup: PDF of the deck on a phone
```

If any line fails, fix it before leaving.

---

## What to do if it breaks anyway

**Do not debug on stage.** It looks worse than the failure itself.

1. Switch to the phone copy — one sentence: *"Let me show you this on the phone."*
2. If that fails too, switch to the deck. The screenshots in the deck carry the
   same story.
3. Keep talking. The argument does not depend on the software running — it depends
   on the two cases, and those can be explained from a slide.

Have screenshots of all five screens in the deck for exactly this reason.

---

## Rehearsal

Three full run-throughs Monday evening, with a timer, on the actual demo machine.

Not "clicking through to check it works" — the full spoken version, start to
finish, including the handover between whoever presents and whoever takes
technical questions.

The third one is the one that matters. The first two find the problems.
