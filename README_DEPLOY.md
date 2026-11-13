# 24/7 Cloud Deployment Guide (Laptop Closed / 100% Autonomous)

This directory contains everything needed to run your **Apex Prop Firm Signal Bot** in the cloud 24/7 without needing your laptop to be open.

---

## Why PythonAnywhere Free Tier Failed
1. **Interactive Console Sleep:** On PythonAnywhere Free Tier, when you open a Bash console and run a script, that console is tied to your browser tab. Closing your laptop or browser terminates the console.
2. **Proxy Whitelist Block:** PythonAnywhere Free Tier blocks all outbound connections to `query1.finance.yahoo.com`. Outbound internet is restricted to a small whitelist. Therefore, live CME futures prices could not be fetched.
3. **Delayed Signals:** Signals only reached you when you messaged in chat because the local development environment ran a market scan on your PC during that prompt.

---

## 24/7 Deployment on Render.com (100% Free Forever)

Render.com provides free cloud hosting with **unrestricted outbound internet access** (live CME futures fetch in ~1 second).

### Step 1: Push This Folder to GitHub (Takes 1 minute)
1. Go to [github.com](https://github.com) and create a free new repository (e.g., `apex-cme-bot`).
2. Upload the 3 files from this folder:
   - `phone_signal_bot.py`
   - `requirements.txt`
   - `Procfile`

### Step 2: Deploy on Render.com (Takes 2 minutes)
1. Go to [render.com](https://render.com) and sign up / log in with your GitHub account (Free).
2. Click **New +** $\rightarrow$ select **Web Service**.
3. Select your GitHub repository (`apex-cme-bot`).
4. Configure settings:
   - **Name:** `apex-cme-bot`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python phone_signal_bot.py`
   - **Plan:** Select **Free** ($0 / month).
5. Click **Create Web Service**.

### Step 3: Done!
* Render will build and launch your bot in ~60 seconds.
* The bot will scan live CME futures feeds every 5 seconds 24/7.
* Your laptop can be turned off, closed, or without power — your phone will receive alerts within 4–5 seconds.

---

## Alternative: PythonAnywhere (If Upgrading to Hacker Plan $5/mo)
If you prefer staying on PythonAnywhere:
1. Upgrade your account to the **Hacker Plan** ($5/month). This unlocks:
   - Unrestricted internet access (Yahoo Finance works).
   - "Always-on tasks" (background daemons).
2. Open the **Tasks** tab in PythonAnywhere.
3. Under **Always-on tasks**, enter:
   `python3 /home/yourusername/phone_signal_bot.py`
4. Click **Create**. It will run non-stop 24/7/365.
