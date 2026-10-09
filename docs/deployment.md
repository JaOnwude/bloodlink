# Deploying BloodLink

BloodLink runs on three free services:

| Part | Service | What it does |
|---|---|---|
| Database | **Neon** (PostgreSQL) | Stores everything. |
| API | **Render** (Docker web service) | Runs the FastAPI backend from `backend/Dockerfile`. |
| Web app | **Vercel** (Next.js) | Serves the site and forwards `/api/v1/*` to the API. |

```
Browser ──> https://<your-site>.vercel.app ──(/api/v1/* forwarded)──> https://<your-api>.onrender.com ──> Neon
```

## Why the site forwards API calls

The browser only ever talks to the Vercel address. Vercel forwards anything under `/api/v1`
to Render (see `frontend/next.config.ts`). The session cookie is therefore set by the site's
own address and is an ordinary first-party cookie.

If the browser called the Render address directly, the cookie would belong to a different
site from the page, a third-party cookie. Safari and other privacy-focused browsers block
those, and signing in would fail on many phones.

## What happens automatically on every API start

`backend/Dockerfile` runs three steps, all safe to repeat:

1. `alembic upgrade head` creates or updates the tables.
2. `python -m scripts.seed` loads the blood compatibility chart and component types if they
   are missing.
3. The API starts on the port Render provides, trusting Render's proxy for each visitor's
   address.

No shell access is needed on Render, which matters because the free plan has none.

---

## Step 1. Create the database on Neon

1. Sign in at <https://console.neon.tech>.
2. Click **New project**.
   - **Project name:** `bloodlink`
   - **Postgres version:** the default
   - **Region:** **AWS Europe Central 1 (Frankfurt)**. It is the closest to Nigeria, and the
     API will run in Render's Frankfurt region, so the two sit next to each other.
3. Click **Create project**.
4. On the project dashboard, click **Connect**.
5. In the dialog:
   - leave **Branch** as `main` and **Database** as `neondb`;
   - **turn off "Connection pooling"**. BloodLink uses the direct connection: it is the one
     recommended for migrations, and a demonstration needs far fewer connections than the
     direct limit;
   - click **Show password**, then **Copy snippet**.

   It looks like
   `postgresql://neondb_owner:abc123...@ep-xxxx-xxxx.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require`
   with **no `-pooler`** in the host name.
6. Keep it somewhere private (a password manager or a local note). It is a secret: never put
   it in a file that is committed to Git.

## Step 2. Merge the code into `main`

Render and Vercel deploy the `main` branch. Merge the current work first (pull request from
`day-5-ship` to `main`, merge commit). You can keep working on `day-5-ship` afterwards and
open a second pull request later.

## Step 3. Generate a signing key for the API

In Git Bash, from the `backend` folder:

```bash
uv run python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the output. This is `SECRET_KEY`: it signs session tokens, and anyone holding it could
sign in as any user, so keep it as private as the database string. The API refuses to start
in production with a key shorter than 32 characters.

## Step 4. Deploy the API on Render

1. Sign in at <https://dashboard.render.com>.
2. Click **New** > **Web Service**.
3. Choose **Git Provider**, then the `bloodlink` repository. Click **Connect**.
4. Fill in the form:

   | Field | Value |
   |---|---|
   | Name | `bloodlink-api` (this becomes `https://bloodlink-api.onrender.com`; if taken, Render adds letters, so note the address it shows) |
   | Language / Runtime | **Docker** |
   | Branch | `main` |
   | Region | **Frankfurt (EU Central)** |
   | Root Directory | `backend` |
   | Dockerfile Path | `./Dockerfile` (relative to the root directory, so leave the default if it shows this) |
   | Instance Type | **Free** |

5. Under **Environment Variables**, add these. Click **Add Environment Variable** for each.

   | Key | Value |
   |---|---|
   | `ENVIRONMENT` | `production` |
   | `DATABASE_URL` | the Neon connection string from step 1 |
   | `SECRET_KEY` | the key from step 3 |
   | `CORS_ORIGINS` | `["https://placeholder.vercel.app"]` (replaced in step 6) |
   | `FRONTEND_URL` | `https://placeholder.vercel.app` (replaced in step 6) |
   | `SMS_PROVIDER` | `console` |

6. Open **Advanced** and set **Health Check Path** to `/api/v1/health`.
7. Click **Deploy Web Service**.
8. Watch the log. The first build takes a few minutes. Success looks like:

   ```
   Reference data ready: 27 compatibility pairs and 3 component types added.
   INFO:     Uvicorn running on http://0.0.0.0:10000
   ```

   and the status at the top turns **Live**.
9. Open `https://<your-api>.onrender.com/api/v1/health/ready` in a browser. You should see
   `{"status":"ready","database":"up"}`.

## Step 5. Deploy the web app on Vercel

1. Sign in at <https://vercel.com>.
2. Click **Add New** > **Project**.
3. Find the `bloodlink` repository and click **Import**.
4. On the configuration screen:

   | Field | Value |
   |---|---|
   | Project Name | `bloodlink` (the address becomes `https://bloodlink-xxxx.vercel.app` or similar) |
   | Framework Preset | **Next.js** (detected automatically) |
   | Root Directory | click **Edit**, choose `frontend`, click **Continue** |
   | Build and Output Settings | leave the defaults |

5. Open **Environment Variables** and add:

   | Key | Value |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | `/api/v1` |
   | `BACKEND_ORIGIN` | `https://<your-api>.onrender.com` (your exact Render address, no trailing slash) |

6. Click **Deploy**. It takes one to two minutes.
7. When it finishes, click the preview to open the site and copy its address from the browser,
   for example `https://bloodlink-abc.vercel.app`. Use the **Domains** address shown on the
   project page, not a long per-deployment address.

Both variables are read when the site is built. If you change either later, redeploy:
**Deployments** > the latest one > **...** > **Redeploy**.

## Step 6. Tell the API the site's real address

Back on Render, open `bloodlink-api` > **Environment**, edit these two, and click
**Save, rebuild, and deploy**:

| Key | Value |
|---|---|
| `CORS_ORIGINS` | `["https://bloodlink-abc.vercel.app"]` (your address, inside `["..."]`) |
| `FRONTEND_URL` | `https://bloodlink-abc.vercel.app` |

`FRONTEND_URL` is the link put in text-message alerts. `CORS_ORIGINS` is not strictly needed
while calls go through the site, but keeps the API correct if anything calls it directly.

## Step 7. Load the demonstration data into Neon

This runs from your own computer, pointed at Neon for one command. Pick a **new** demo
password for the deployed site, different from the one in `.env.example` (that file is
public in the repository). It must be at least 15 characters and must not contain
"bloodlink" or "demo".

In Git Bash, from the `backend` folder, using single quotes around both values:

```bash
DATABASE_URL='paste-the-neon-string-here' DEMO_PASSWORD='your-new-demo-password' uv run python -m scripts.seed_demo
```

Values given on the command line take priority over `.env`, so your local database is not
touched. You should see `Demonstration data loaded: 34 accounts, 5 hospitals, ...`. Running
it again is harmless: it reports that the data is already present.

To receive real text alerts later, add `DEMO_DONOR_PHONE='+234...'` with your own number to
the same command. It only applies on the first, data-creating run.

## Step 8. Check the main journey on the live site

Open the Vercel address. Wake the API first if it has been idle (see below).

1. **Landing page:** loads; the "Register your hospital" button opens sign-up with "Hospital
   staff" selected.
2. **Donor:** sign in as `donor07@bloodlink.example` with the demo password. "Requests near
   you" lists the critical O- request at Lagoon Specialist Hospital. Pledge to it.
3. **Hospital:** sign out, sign in as `staff.lagos@bloodlink.example`. Open the O- request.
   - The map shows the hospital and nearby donors.
   - The pledged donor is listed with contact details.
   - Press **Donated**.
   - The dashboard figures update.
4. **Administrator:** sign in as `admin@bloodlink.example`. Surulere Family Clinic is waiting
   for review.
5. On a phone, preferably an iPhone with Safari, sign in once to confirm the cookie works
   there too.

---

## Free-plan behaviour to know before a demonstration

- **The API sleeps.** Render's free service stops after 15 minutes without traffic and takes
  up to a minute to wake. **Open `https://<your-api>.onrender.com/api/v1/health` a minute
  or two before presenting** and wait until it shows `"status":"ok"`.
- **The database sleeps too.** Neon pauses an idle free database and resumes it in about a
  second on the next query. Nothing to do.
- **Render's monthly allowance.** Free services share 750 hours a month per account. A
  sleeping service uses none.
- **Text messages.** `SMS_PROVIDER=console` records alerts without sending. When the Termii
  sender ID is approved, add these on Render, then save and redeploy:
  - `SMS_PROVIDER=termii`
  - `TERMII_API_KEY`
  - `TERMII_BASE_URL`
  - `TERMII_SENDER_ID`
  - `TERMII_CHANNEL=dnd`

## Updating the live site

Push or merge to `main`. Render and Vercel both rebuild automatically. Database changes ship
as Alembic migrations and are applied when the API restarts.

## When something goes wrong

| Symptom | Likely cause and fix |
|---|---|
| Render build log: `SECRET_KEY must be set to a random value of at least 32 characters in production` | `SECRET_KEY` is missing or short. Redo step 3. |
| Render log: `connection to server ... failed` or `password authentication failed` | `DATABASE_URL` is wrong. Copy it again from Neon > **Connect**, with **Show password** on, and check there is no space or line break. |
| Render: "No open ports detected" | The start command did not reach Uvicorn. Read the lines above it in the log, usually a database error. |
| Site loads, but signing in says "Unable to reach the server" | `BACKEND_ORIGIN` on Vercel is wrong or the API is asleep. Open the API health address; fix the variable and redeploy on Vercel. |
| Signing in seems to work, but you are sent straight back to the sign-in page | The site is calling Render directly. Check `NEXT_PUBLIC_API_URL` is exactly `/api/v1` and redeploy. |
| Demo accounts do not sign in | Step 7 not run, or a different password. Run step 7 again: it lists the accounts. |
| Pages show old content after a change | Vercel is still building, or a variable changed without a redeploy. |
