import atexit
import logging
import os
import sys
import threading
import time
import asyncio

from apscheduler.schedulers.background import BackgroundScheduler

from algorithms.new_tokens import NewTokens
from qfl_signals import QFL_signals
from signals import ResearchSignals

root = logging.getLogger()
root.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)

# if os.getenv("ENV") != "ci":
#     scheduler = BackgroundScheduler()
#     # nt = NewTokens()
#     # scheduler.add_job(
#     #     func=nt.run,
#     #     timezone="Europe/London",
#     #     trigger="interval",
#     #     hours=6,
#     # )
#     scheduler.start()
#     atexit.register(lambda: scheduler.shutdown())

try:
    rs = ResearchSignals()
    rs.start_stream()
except Exception as error:
        print(error)
        rs = ResearchSignals()
        rs.start_stream()

async def signals_main():
    qfl = QFL_signals()
    await asyncio.gather(
        qfl.start_stream(),
    )

if __name__ == "__main__":
    try:
        asyncio.run(signals_main())
    except Exception as error:
        print(error)
        asyncio.run(signals_main())

