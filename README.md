# Sports Tracker Backup

Back up all your [Sports Tracker](https://www.sports-tracker.com) workouts before the data is gone. Downloads workout metadata, GPS tracks (GPX), and photos via the Sports Tracker API.

## What gets backed up

- **Workout metadata** — full JSON with duration, distance, heart rate, calories, etc.
- **GPS tracks** — exported as standard GPX files (importable into Strava, Garmin, etc.)
- **Photos** — full-resolution workout photos

Output structure:
```
output/
├── workouts/    # JSON metadata per workout
├── gpx/         # GPX track files
├── photos/      # Full-size workout photos
├── scrape.log   # Run log
└── .checkpoint.json  # Resume state
```

## Getting your session key

1. Log in to [sports-tracker.com](https://www.sports-tracker.com) in your browser
2. Open DevTools (`F12`) → **Network** tab
3. Click any workout or reload the page
4. Find a request to `api.sports-tracker.com`
5. Look at the request headers and copy the **`STTAuthorization`** value

> **Note:** Session keys expire after some time. If the backup fails with an auth error, just grab a fresh key and re-run — it will resume where it left off.

## Usage

### Docker (recommended)

1. Copy `.env.example` to `.env` and paste your session key:
   ```bash
   cp .env.example .env
   # Edit .env and set SESSION_KEY=your_key_here
   ```

2. Run:
   ```bash
   docker compose up --build
   ```

3. Your backup will be in the `./output` directory.

### Standalone Python

Requirements: Python 3.9+ and `aiohttp`.

```bash
pip install aiohttp

# Using environment variable
export SESSION_KEY=your_key_here
python scrape_sports_tracker.py

# Or using CLI arguments
python scrape_sports_tracker.py --session-key your_key_here --output ./my-backup
```

## Resume support

The tool saves progress to `.checkpoint.json` after each workout. If interrupted, just re-run and it picks up where it left off. No duplicate downloads.

## License

MIT
