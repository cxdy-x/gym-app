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
You are helping update a strength-training program using progressive overload,
with occasional exercise variation.

Weight/rep progression rules:
- For each exercise, look at its most recent sessions in "history".
- If every set in the last 2 sessions hit or exceeded the exercise's target
  reps, increase "weight" by roughly 2.5-5%, rounded to a sensible increment
  for that kind of equipment (dumbbells often jump in 2.5kg steps; cables and
  machines can be finer; barbells usually jump in 2.5-5kg per side, i.e.
  5-10kg total).
- If sets fell short of target reps, leave "weight" unchanged so the user can
  work back up to it.
- If weight and reps have been flat for 3+ sessions with no missed reps,
  increase "reps" by 1 instead (up to about 12-15) before the next weight
  increase.

Exercise variation rules:
- Most weeks, leave exercise selection unchanged — only adjust the numbers
  above.
- About once every 4-6 weeks, OR for any exercise whose weight has been
  completely flat for 4+ consecutive sessions despite hitting target reps
  (a plateau), you may swap ONE exercise in ONE workout for a different,
  well-known gym exercise that targets the same muscle group/movement
  pattern. Prefer the exercise pool below, but a different well-known
  exercise for that same movement pattern is fine if nothing in the pool
  fits.
- Never swap more than one exercise across the whole routine in a single
  update.
- Keep the same four workout keys/names ("upper-push", "lower",
  "upper-pull", "full-body") and the same number of exercises in each
  workout — this is a straight swap, not an addition.
- When you introduce an exercise with no history, pick a conservative
  starting weight (estimate from a comparable movement already in the
  history, erring low) and set reps to the low end of a sensible range
  (e.g. 8-10) rather than guessing aggressively — the user will adjust
  after the first session.
- For bodyweight moves (e.g. pull-ups, dips) with no added load, set
  "weight" to 0.

Exercise pool (grouped by workout type — pick from here first when
swapping, but not required if another popular exercise fits better):
- upper-push: Barbell Bench Press, Dumbbell Bench Press, Incline Barbell
  Bench Press, Incline Dumbbell Bench Press, Seated Dumbbell Shoulder
  Press, Standing Overhead Barbell Press, Machine Chest Press, Dips,
  Cable Lateral Raise, Dumbbell Lateral Raise, Tricep Rope Pushdown,
  Overhead Rope Extension, Close-Grip Bench Press
- lower: Barbell Back Squat, Front Squat, Leg Press, Romanian Barbell
  Deadlift, Conventional Barbell Deadlift, Bulgarian Split Squat, Walking
  Lunges, Hip Thrust, Leg Curl, Leg Extension, Calf Raise
- upper-pull: Lat Pulldown, Pull-Up, Chin-Up, Seated Cable Row, Barbell
  Row, Dumbbell Row, Face Pull, Barbell Curl, Dumbbell Curl, Preacher
  Curl, Hammer Curl
- full-body: draw 1-2 exercises from each of the pools above, favouring
  compound lifts (squat/press/row/pulldown pattern)

Output rules:
- Output ONLY a JSON array in exactly the same shape as the "routine" field
  you were given: a list of {key, name, exercises: [{name, sets, reps,
  weight}]}. No commentary, no markdown code fences, no explanation.

Here is the current routine and recent history:
<paste the JSON from step 1 here>
```

## 3. Sanity-check the result

Before committing, make sure it's valid JSON and nothing structural broke
(same 4 workouts, same exercise count per workout, and any swapped-in
exercise actually makes sense for that workout's muscle group):

```sh
python3 -m json.tool routine.json > /dev/null && echo OK
```

If a suggested jump — or a swap — looks off, hand-edit `routine.json`
directly. You don't have to accept the whole thing as-is. Brand-new
exercises start with no logged history, which is expected — just treat the
first session's numbers as a starting estimate and let the following week's
export pick up real data for it.

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

Note: a workout that's already *pending* when you deploy keeps whatever
exercises it was created with — the new mix only shows up starting from the
workout generated after you next complete one.
