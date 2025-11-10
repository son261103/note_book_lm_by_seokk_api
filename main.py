import argparse
import logging
import multiprocessing
import signal
import sys

import uvicorn
from dotenv import load_dotenv

from app.config.uvicorn import load_uvicorn_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

load_dotenv()


def start_celery_worker():
    """Start Celery worker in a separate process."""
    try:
        from app.celery_app import celery_app

        logging.info("🚀 Starting Celery Worker...")

        # Start Celery worker with arguments
        celery_app.worker_main(
            argv=[
                "worker",
                "--loglevel=info",
                "--pool=solo",  # Use solo pool for Windows compatibility
                "--concurrency=1",
            ]
        )
    except Exception as e:
        logging.error(f"❌ Celery Worker failed to start: {e}")
        sys.exit(1)


def start_celery_beat():
    """Start Celery Beat scheduler in a separate process."""
    try:
        from app.celery_app import celery_app

        logging.info("⏰ Starting Celery Beat Scheduler...")

        # Start Celery beat
        celery_app.start(
            argv=[
                "celery",
                "beat",
                "--loglevel=info",
            ]
        )
    except Exception as e:
        logging.error(f"❌ Celery Beat failed to start: {e}")
        sys.exit(1)


def start_fastapi_server(args):
    """Start FastAPI server."""
    try:
        logging.info("🌐 Starting FastAPI Server...")

        config_kwargs = load_uvicorn_config(args)
        config = uvicorn.Config(**config_kwargs)
        server = uvicorn.Server(config)

        server.run()
    except Exception as e:
        logging.error(f"❌ FastAPI Server failed to start: {e}")
        sys.exit(1)


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    logging.info("\n🛑 Shutting down all processes...")
    sys.exit(0)


if __name__ == "__main__":
    # Set multiprocessing start method for Windows compatibility
    if sys.platform.startswith("win"):
        multiprocessing.set_start_method("spawn", force=True)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    parser = argparse.ArgumentParser(description="Run the SurfSense application")
    parser.add_argument("--reload", action="store_true", help="Enable hot reloading")
    parser.add_argument("--no-celery", action="store_true", help="Run without Celery worker")
    parser.add_argument("--no-beat", action="store_true", help="Run without Celery Beat scheduler")
    args = parser.parse_args()

    processes = []

    try:
        # Start Celery Worker
        if not args.no_celery:
            celery_worker_process = multiprocessing.Process(
                target=start_celery_worker,
                name="CeleryWorker"
            )
            celery_worker_process.start()
            processes.append(celery_worker_process)
            logging.info("✅ Celery Worker process started")

        # Start Celery Beat Scheduler
        if not args.no_beat and not args.no_celery:
            celery_beat_process = multiprocessing.Process(
                target=start_celery_beat,
                name="CeleryBeat"
            )
            celery_beat_process.start()
            processes.append(celery_beat_process)
            logging.info("✅ Celery Beat process started")

        # Start FastAPI Server in main process
        logging.info("=" * 60)
        logging.info("🎉 All services starting...")
        logging.info("=" * 60)

        start_fastapi_server(args)

    except KeyboardInterrupt:
        logging.info("\n🛑 Received shutdown signal...")
    except Exception as e:
        logging.error(f"❌ Error in main process: {e}")
    finally:
        # Cleanup: terminate all child processes
        logging.info("🧹 Cleaning up processes...")
        for process in processes:
            if process.is_alive():
                logging.info(f"Terminating {process.name}...")
                process.terminate()
                process.join(timeout=5)
                if process.is_alive():
                    logging.warning(f"Force killing {process.name}...")
                    process.kill()

        logging.info("👋 Shutdown complete!")
