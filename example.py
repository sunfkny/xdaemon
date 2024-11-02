import os
import time

from loguru import logger

from xdaemon import Daemon


def main():
    # 将进程转为后台运行，主程序退出
    with Daemon(max_error_count=0):
        # 以下代码只有子进程会执行
        for _ in range(10):
            logger.info(f"{os.getpid()} {time.time()}")
            time.sleep(1)


if __name__ == "__main__":
    main()
