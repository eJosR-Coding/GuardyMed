# Demo walkthrough

A five-minute tour. Start the app with `make demo` and open <http://127.0.0.1:8000/app>.
The sample data is generated relative to today, so there is always a draft month, an approved
previous month, and a shift for the demo worker today.

## As the manager (Elena Cruz)

1. **Today.** Two items wait for a decision: a replacement request from Ana Ruiz and a manual check-in from Marta Vega.
   Approve Ana's request: the shift moves to Marta Vega and the action is recorded in **Activity**.
2. **Schedule.** Open the draft month, pick a day, add a shift, then **Submit for review** and **Approve**.
   Switch the month selector to the previous month, choose *Attendance evidence* and export a CSV.
3. **Attendance.** Enroll a person for face check-in (the demo runtime offers a reference photo with one click).
4. **Activity.** See who changed what, newest first.

## As the worker (Ana Ruiz)

1. **My shifts.** Today's shift is at the top. Choose **Check in**.
2. In the demo runtime pick *Clear capture of the same person* to get **Verified**, *Poor lighting* to get **Needs review**
   (a manager confirms it on Today), or *A different person* to get **Not verified**. These captures are simulated, see
   [AI_SERVICES.md](AI_SERVICES.md).
3. **Request a change** on any upcoming shift, optionally naming a colleague to cover.
4. **My requests** shows the decision once the manager acts.

## Sign-in

Demo accounts (only when `GUARDYMED_DEMO_MODE=true`, the default): `manager@guardymed.local` and
`worker@guardymed.local`, password `password123`.
