import logging
import asyncio

from qfl_signals import QFL_signals
from signals import ResearchSignals
from websocket._exceptions import WebSocketConnectionClosedException

logging.basicConfig(
    filename="./binbot-research.log",
    filemode="a",
    format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)
logging.info("Started")


async def signals_main():
    qfl = QFL_signals()
    await asyncio.gather(
        qfl.start_stream(),
    )


if __name__ == "__main__":
    try:
        rs = ResearchSignals()
        rs.start_stream()
        asyncio.run(signals_main())
    except WebSocketConnectionClosedException as error:
        rs = ResearchSignals()
        rs.start_stream()
    except Exception as error:
        print(error)
        asyncio.run(signals_main())
        rs = ResearchSignals()
        rs.start_stream()
