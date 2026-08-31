# VT RecSports Occupancy Tracker

Tracks facility occupancy at VT gyms and logs the data to then show
trends and information on when the gyms are empty/full.

Logs occupancy for all facilities on `connect.recsports.vt.edu/facilityoccupancy`
(WMH Service Desk, McComas Hall Service Desk, Esports, Bouldering Wall)
every 30 minutes via GitHub Actions -- runs entirely in the cloud, so your
computer never needs to be on.

## One heads-up before you run this

The site's `robots.txt` disallows automated access for all bots
(`Disallow: /`), which looks like a generic default for this vendor
platform rather than something aimed specifically at the occupancy widget.
A GET request every 30 minutes to a public page is about as light as
automated traffic gets, but it's worth knowing the site has stated that
preference -- your call on how you want to run this long-term.

## Setup (5 minutes, one time)

1. **Create a new GitHub repo.** Public is recommended -- gym occupancy
   isn't sensitive data, and public repos get unlimited free GitHub
   Actions minutes. (Private repos get 2,000 free minutes/month, which
   this should fit into, but a public repo removes any doubt.)

2. **Push these 5 files to it**, keeping the folder structure:
   ```
   occupancy_logger.py
   analyze.py
   excluded_dates.txt
   README.md
   .github/workflows/log.yml
   ```
   From this folder:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<your-repo>.git
   git push -u origin main
   ```

3. **Give the workflow permission to commit back to the repo.** Go to
   your repo's **Settings → Actions → General → Workflow permissions**,
   select **"Read and write permissions"**, and save. (Without this, the
   workflow runs fine but fails to push the updated CSV.)

That's it. The workflow (`.github/workflows/log.yml`) fires every 30
minutes automatically. `occupancy_logger.py` itself decides whether it's
actually a weekday, during operating hours, and not a known holiday
(everything computed in real Eastern time, so it's not thrown off by
GitHub's UTC clock or daylight saving) -- so most of those 30-minute
triggers will just skip instantly and only the ones during real gym hours
will actually log a row and commit.

You can watch it work under the **Actions** tab of your repo, and trigger
a run manually any time with the "Run workflow" button if you want to
confirm it's working before waiting for the next real interval.

## Before you fully trust the data, tune two things

1. **`OPERATING_HOURS` in `occupancy_logger.py`** -- currently 5am-midnight
   Mon-Fri, applied to ALL facilities on the page, including War Memorial Hall,
   which is mid-renovation and has had shifting/reduced hours. Check
   current hours at recsports.vt.edu/facilities/ and adjust. Weekends are
   off by default (matches "track every weekday" from the original ask)
   -- flip `WEEKEND_ENABLED = True` near the top if you want them too.

2. **`excluded_dates.txt`** -- pre-filled with Labor Day, Thanksgiving
   break, an approximate winter break window, and MLK Day from the
   official 2026-2027 academic calendar. Fall Break (Oct 9) and Spring
   Break (Mar 6-14) are deliberately NOT excluded since VT offices stay
   open and the gym likely does too (a different crowd pattern, which is
   real data, not an outlier) -- add them yourself if you find the gym
   actually closes those days. Just edit the file and push -- no code
   changes needed.

## Checking in after a week or two

Pull the repo (or just download `occupancy_log.csv` from GitHub) and run:

```bash
pip install requests beautifulsoup4 pandas matplotlib
python3 analyze.py
```

It prints average occupancy by hour and by weekday per facility, and saves
a heatmap PNG per facility so you can see the best/worst times to go at a
glance.
