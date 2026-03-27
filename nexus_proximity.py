#!/usr/bin/env python3
import asyncio
import colorama
import logging
import platform
from argparse import ArgumentParser, Namespace
from asyncio import Queue, TimeoutError
from colorama import Fore, Style
from logging import Formatter, LogRecord, Logger, StreamHandler
from socket import socket as Socket
from typing import Any, Dict, List, Optional, Tuple

colorama.init(autoreset=True)
handler: StreamHandler = StreamHandler()

class ColorFormatter(Formatter):
      COLORS: Dict[int, str] = {
                logging.DEBUG: Fore.BLUE,
                logging.INFO: Fore.GREEN,
                logging.WARNING: Fore.YELLOW,
                logging.ERROR: Fore.RED,
                logging.CRITICAL: Fore.MAGENTA,
      }
      def format(self, record: LogRecord) -> str:
                color: str = self.COLORS.get(record.levelno, "")
                prefix: str = f"{color}[{record.levelname}:{record.name}]{Style.RESET_ALL}"
                return f"{prefix} {record.getMessage()}"

  handler.setFormatter(ColorFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger: Logger = logging.getLogger("nexus_proximity")

PROXIMITY_KEY_TYPES: Dict[int, str] = {0x01: "IRK", 0x04: "ENC_KEY"}

def parse_nexus_proximity_response(data: bytes) -> Optional[List[Tuple[str, bytes]]]:
      if len(data) < 7 or data[4] != 0x31: return None
            key_count: int = data[6]
    keys: List[Tuple[str, bytes]] = []
    offset: int = 7
    for _ in range(key_count):
              if offset + 3 >= len(data): break
                        key_type: int = data[offset]
        key_length: int = data[offset + 2]
        offset += 4
        if offset + key_length > len(data): break
                  key_bytes: bytes = data[offset:offset + key_length]
        keys.append((PROXIMITY_KEY_TYPES.get(key_type, f"TYPE_{key_type:02X}"), key_bytes))
        offset += key_length
    return keys

def hexdump(data: bytes) -> str:
      return " ".join(f"{b:02X}" for b in data)

async def run_bumble(bdaddr: str) -> int:
      try:
                from bumble.transport import open_transport
                from bumble.device import Device
                from bumble.host import Host
                from bumble.pairing import PairingConfig, PairingDelegate
                from bumble.hci import HCI_Error
                from bumble.l2cap import ClassicChannelSpec
                from bumble.core import PhysicalTransport
except ImportError:
        logger.error("Bumble not installed")
        return 1

    PSM_PROXIMITY: int = 0x1001
    HANDSHAKE: bytes = bytes.fromhex("00 00 04 00 01 00 02 00 00 00 00 00 00 00 00 00")
    KEY_REQ: bytes = bytes.fromhex("04 00 04 00 30 00 05 00")

    class KeyStore:
              async def delete(self, name: str) -> None: pass
                        async def update(self, name: str, keys: Any) -> None: pass
                                  async def get(self, _name: str) -> Optional[Any]: return None
                                            async def get_all(self) -> List[Tuple[str, Any]]: return []
                                                      async def get_resolving_keys(self) -> List[Tuple[bytes, Any]]: return []

    async def exchange_keys(channel: Any, timeout: float = 5.0) -> Optional[List[Tuple[str, bytes]]]:
              recv_q: Queue = Queue()
        channel.sink = lambda sdu: recv_q.put_nowait(sdu)
        logger.info("Sending handshake...")
        channel.send_pdu(HANDSHAKE)
        await asyncio.sleep(0.5)
        logger.info("Requesting keys...")
        channel.send_pdu(KEY_REQ)
        try:
                      pkt: bytes = await asyncio.wait_for(recv_q.get(), timeout)
                      return parse_nexus_proximity_response(pkt)
except TimeoutError:
            return None

    transport, device = await open_transport("usb:0"), None # Simplified for the repo
    # ... more logic from the source ...
    print("Nexus Proximity Engine Active")
    return 0

def main() -> None:
      parser = ArgumentParser()
    parser.add_argument("bdaddr")
    args = parser.parse_args()
    print(f"Connecting to {args.bdaddr}...")

if __name__ == "__main__":
      main()
