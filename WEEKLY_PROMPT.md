# Weekly workout update (no API key, no cost)

Do this once a week (or whenever you like) using any free chat LLM — Claude.ai,
ChatGPT's free tier, etc. Nothing here talks to an API; you're just copying
JSON in and out of a chat window by hand.

## 1. Export your data

Visit this in a browser, or `curl` it, from a machine on the home LAN:

```
http://10.0.0.10:2222/export
```

Copy the full JSON response. It contains your current `routine.json` plus your
recent logged sets (reps/weight) per exercise.

## 2. Paste this prompt into a chat LLM, then paste the JSON straight after it

```
You are helping update a strength-training program using progressive overload.

Rules:
- For each exercise, look at its most recent sessions in "history".
- If every set in the last 2 sessions hit or exceeded the exercise's target
  reps, increase "weight" by roughly 2.5-5%, rounded to a sensible increment
  for that kind of equipment (dumbbells often jump in 2.5kg steps; cables and
  machines can be finer).
- If sets fell short of target reps, leave "weight" unchanged so the user can
  work back up to it.
- If weight and reps have been flat for 3+ sessions with no missed reps,
  increase "reps" by 1 instead (up to about 12-15) before the next weight
  increase.
- Do not add, remove, reorder, or rename exercises or workout days. Only
  adjust "sets", "reps" and "weight".
- Output ONLY a JSON array in exactly the same shape as the "routine" field
  you were given: a list of {key, name, exercises: [{name, sets, reps,
  weight}]}. No commentary, no markdown code fences, no explanation.

Here is the current routine and recent history:
<paste the JSON from step 1 here>
```

## 3. Sanity-check the result

Before committing, make sure it's valid JSON and nothing structural changed
(same exercise names, same number of workouts):

```sh
python3 -m json.tool routine.json > /dev/null && echo OK
```

If a suggested jump looks off for an exercise, just hand-edit that one number
in `routine.json` — you don't have to accept the whole thing as-is.

## 4. Commit and deploy

```sh
git add routine.json
git commit -m "Update routine weights"
git push
```

Then on the server, same as any other update:

```sh
cd /opt/gym-app
git pull
docker compose up -d --build
```
