from hdfs.client import Client
import queue
from threading import Thread, Lock
import config
from utils.log import logger
import aiofiles


class LocalStorage:

    async def write(self, data: str, path: str):
        async with aiofiles.open(path, 'a+', encoding="utf-8") as f:
            await f.write(data)
            await f.write("\n")
        logger.debug(f"Written {len(data)} byets to {path}")


class HdfsStorage(Thread):

    def __init__(self) -> None:
        super(HdfsStorage, self).__init__()
        self._client = Client(
            url=config.HDFS.get("host"),
            root=config.HDFS.get("root_path")
        )
        # self._lock = Lock()
        self._is_stop = False
        self._msg_queue = queue.Queue()

    def write(self, data: str, path: str):
        self._msg_queue.put({
            "data": data,
            "path": path
        })

    def _write_to_hdfs(self, data: str, path: str):
        # TODO: batch write request
        try:
            with self._client.write(path, append=False, encoding="utf-8") as writer:
                writer.write(data)
                writer.write("\n")
            logger.info(f"Written {len(data)} byets to {path}")
        except Exception as e:
            print(e)

    def wait_finish(self):
        self._is_stop = True
        self.join()

    def run(self) -> None:
        logger.info("HdfsStorage Thread running")
        while not self._is_stop or not self._msg_queue.empty():
            while not self._msg_queue.empty():
                kwargs = self._msg_queue.get()
                self._write_to_hdfs(**kwargs)
        logger.info("HdfsStorage Thread stopped")


# global storage
storage = LocalStorage()
# storage.start()

if __name__ == "__main__":
    storage.write("hello world", "test.txt")
    storage.wait_finish()
