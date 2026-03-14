#!/usr/bin/env python3
"""
Sports Tracker Backup Tool
Backs up all your Sports Tracker workouts, GPX tracks, and photos via the API.
"""

import argparse
import asyncio
import json
import os
from pathlib import Path
import aiohttp
import logging
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

API_BASE = "https://api.sports-tracker.com/apiserver/v1"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Backup all your Sports Tracker workouts, GPX tracks, and photos."
    )
    parser.add_argument(
        "--session-key",
        default=os.getenv("SESSION_KEY"),
        help="Sports Tracker session key (or set SESSION_KEY env var)"
    )
    parser.add_argument(
        "--output", "-o",
        default=os.getenv("OUTPUT_DIR", "/app/output" if os.path.exists("/app") else "./output"),
        help="Output directory (default: ./output, or /app/output in Docker)"
    )
    args = parser.parse_args()

    if not args.session_key:
        parser.error(
            "Session key is required.\n\n"
            "Pass it via --session-key or set the SESSION_KEY environment variable.\n\n"
            "To get your session key:\n"
            "  1. Log in to https://www.sports-tracker.com in your browser\n"
            "  2. Open DevTools (F12) → Network tab\n"
            "  3. Click any workout or reload the page\n"
            "  4. Find a request to api.sports-tracker.com\n"
            "  5. Copy the 'STTAuthorization' header value — that's your session key"
        )

    return args


# ============================================================================
# LOGGING
# ============================================================================

def setup_logging(output_dir):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        handlers=[
            logging.FileHandler(f"{output_dir}/scrape.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


# ============================================================================
# HELPERS
# ============================================================================

def setup_dirs(output_dir):
    Path(f"{output_dir}/workouts").mkdir(exist_ok=True)
    Path(f"{output_dir}/gpx").mkdir(exist_ok=True)
    Path(f"{output_dir}/photos").mkdir(exist_ok=True)


def load_checkpoint(checkpoint_file):
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, 'r') as f:
            return json.load(f)
    return {
        "scraped_workouts": [],
        "failed_workouts": [],
        "start_time": datetime.now().isoformat()
    }


def save_checkpoint(checkpoint, checkpoint_file):
    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint, f, indent=2)


# ============================================================================
# API FUNCTIONS
# ============================================================================

async def api_get(session, path, session_key, raw=False):
    """Make authenticated API request"""
    url = f"{API_BASE}/{path}"
    headers = {"STTAuthorization": session_key}
    async with session.get(url, headers=headers, allow_redirects=True,
                           timeout=aiohttp.ClientTimeout(total=30)) as resp:
        if resp.status != 200:
            return None
        if raw:
            return await resp.read()
        return await resp.json()


async def get_all_workouts(session, session_key):
    """Fetch all workout summaries in one call"""
    data = await api_get(session, "workouts?limited=true&limit=1000", session_key)
    if not data or data.get("error"):
        raise RuntimeError(f"Failed to fetch workouts: {data}")
    return data["payload"]


async def get_workout_detail(session, workout_key, session_key):
    """Fetch full workout metadata"""
    data = await api_get(session, f"workouts/{workout_key}", session_key)
    if data and not data.get("error"):
        return data["payload"]
    return None


async def get_workout_data(session, workout_key, session_key):
    """Fetch workout track data (locations, heartrates, etc.)"""
    data = await api_get(session, f"workouts/{workout_key}/data", session_key)
    if data and not data.get("error"):
        return data["payload"]
    return None


async def get_gpx(session, workout_key, session_key):
    """Export workout as GPX"""
    return await api_get(session, f"workout/exportGpx/{workout_key}", session_key, raw=True)


async def get_workout_images(session, workout_key, session_key):
    """Get list of images for a workout"""
    data = await api_get(session, f"images/workout/{workout_key}", session_key)
    if data and not data.get("error"):
        return data["payload"]
    return []


async def download_image(session, image_key, save_path, session_key):
    """Download a full-size photo"""
    if os.path.exists(save_path):
        return True
    data = await api_get(session, f"image/{image_key}.jpg", session_key, raw=True)
    if data:
        with open(save_path, 'wb') as f:
            f.write(data)
        return True
    return False


# ============================================================================
# MAIN BACKUP
# ============================================================================

async def backup_workout(session, workout_summary, checkpoint, output_dir, checkpoint_file, session_key, logger):
    """Backup a single workout: metadata + track data + GPX + photos"""
    wk = workout_summary["workoutKey"]

    if wk in checkpoint["scraped_workouts"]:
        return True

    try:
        # Fetch detailed metadata
        detail = await get_workout_detail(session, wk, session_key)
        if not detail:
            logger.warning(f"  Could not fetch detail for {wk}")
            detail = workout_summary

        # Fetch track data
        track_data = await get_workout_data(session, wk, session_key)

        # Save combined JSON
        backup = {
            "workout": detail,
            "track_data": track_data,
            "backed_up_at": datetime.now().isoformat()
        }
        with open(f"{output_dir}/workouts/{wk}.json", 'w') as f:
            json.dump(backup, f, indent=2)

        # Export GPX
        gpx_data = await get_gpx(session, wk, session_key)
        if gpx_data:
            with open(f"{output_dir}/gpx/{wk}.gpx", 'wb') as f:
                f.write(gpx_data)

        # Download photos
        photo_count = 0
        if workout_summary.get("pictureCount", 0) > 0:
            images = await get_workout_images(session, wk, session_key)
            for img in images:
                img_key = img["key"]
                save_path = f"{output_dir}/photos/{img_key}.jpg"
                if await download_image(session, img_key, save_path, session_key):
                    photo_count += 1

        checkpoint["scraped_workouts"].append(wk)
        name = detail.get("workoutName", wk)
        logger.info(f"  done: {name} (gpx={'yes' if gpx_data else 'no'}, photos={photo_count})")
        return True

    except Exception as e:
        logger.error(f"  FAILED {wk}: {e}")
        if wk not in checkpoint["failed_workouts"]:
            checkpoint["failed_workouts"].append(wk)
        return False


async def main():
    args = parse_args()
    output_dir = args.output
    session_key = args.session_key
    checkpoint_file = f"{output_dir}/.checkpoint.json"

    logger = setup_logging(output_dir)

    logger.info("=" * 70)
    logger.info("Sports Tracker Backup")
    logger.info("=" * 70)

    setup_dirs(output_dir)
    checkpoint = load_checkpoint(checkpoint_file)

    if checkpoint["scraped_workouts"]:
        logger.info(f"Resuming: {len(checkpoint['scraped_workouts'])} already done")

    async with aiohttp.ClientSession() as session:
        # Verify session is valid
        test = await api_get(session, "workouts?limited=true&limit=1", session_key)
        if not test or test.get("error"):
            logger.error(
                "Session key is invalid or expired.\n"
                "Get a new one from your browser (see README for instructions)."
            )
            raise SystemExit(1)

        # Get all workouts
        workouts = await get_all_workouts(session, session_key)
        logger.info(f"Total workouts: {len(workouts)}")

        remaining = [w for w in workouts if w["workoutKey"] not in checkpoint["scraped_workouts"]]
        logger.info(f"Remaining: {len(remaining)}")

        for i, workout in enumerate(remaining, 1):
            logger.info(f"[{i}/{len(remaining)}] {workout['workoutKey']}")
            await backup_workout(session, workout, checkpoint, output_dir, checkpoint_file, session_key, logger)
            save_checkpoint(checkpoint, checkpoint_file)
            await asyncio.sleep(0.3)

    # Summary
    logger.info("=" * 70)
    logger.info("BACKUP COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Scraped: {len(checkpoint['scraped_workouts'])}")
    logger.info(f"Failed:  {len(checkpoint['failed_workouts'])}")
    logger.info(f"Output:  {output_dir}")

    checkpoint["end_time"] = datetime.now().isoformat()
    save_checkpoint(checkpoint, checkpoint_file)


if __name__ == "__main__":
    asyncio.run(main())
