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

Sports Tracker doesn't offer a public API or OAuth login, so this tool authenticates using a session key from your browser. Here's how to get it:

1. Open your browser and go to [sports-tracker.com](https://www.sports-tracker.com)
2. Log in with your Sports Tracker account
3. Open **Developer Tools**:
   - **Chrome/Edge:** Press `F12`, or right-click anywhere → *Inspect*
   - **Firefox:** Press `F12`, or menu → *More tools* → *Web Developer Tools*
   - **Safari:** Enable the Develop menu in *Preferences → Advanced*, then press `Cmd+Option+I`
4. Click the **Network** tab in Developer Tools
5. With the Network tab open, click on any workout in Sports Tracker (or just reload the page)
6. In the Network tab, look for requests to `api.sports-tracker.com` — click on any one of them
7. In the request details, go to the **Headers** section
8. Under **Request Headers**, find the header named **`STTAuthorization`**
9. Copy the value — it's a long alphanumeric string. That's your session key.

**Tips:**
- You can filter the Network tab by typing `api.sports-tracker` to find the right requests faster
- The session key looks something like: `abn123def456ghi789...`
- Session keys expire after some time (usually a few hours to days). If the backup stops with an authentication error, just grab a fresh key from your browser and re-run — the tool will automatically resume where it left off

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
