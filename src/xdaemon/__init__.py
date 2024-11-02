import os
import subprocess
import sys
import time
from typing import TypeAlias

from loguru import logger

StrOrBytesPath: TypeAlias = str | bytes | os.PathLike[str] | os.PathLike[bytes]

# 环境变量名称
ENV_NAME = "XW_DAEMON_IDX"
# 运行时调用 background 的次数
run_idx = 0


class Daemon:
    def __init__(
        self,
        log_file: StrOrBytesPath = "daemon.log",
        max_error_count: int | None = None,
    ):
        """
        守护进程配置

        :param log_file: 日志文件路径, 记录守护进程和子进程的标准输出和错误输出
        :param max_error_count: 连续启动失败或异常退出的最大次数, 超过此数守护进程退出, 不再重启子进程
        """
        self.log_file = log_file
        self.max_error_count = max_error_count

    def run(self):
        """
        启动后台守护进程
        """
        # 启动一个守护进程后退出
        self.background(is_exit=True)

        # 守护进程启动一个子进程, 并循环监视
        error_count = 0
        while True:
            # 启动时间戳
            start_time = time.time()
            cmd = self.background(is_exit=False)
            if cmd is None:  # 子进程
                logger.info(
                    f"daemon: {os.getppid()}, child process: {os.getpid()} started"
                )
                break

            # 父进程: 等待子进程退出
            cmd.wait()
            elapsed_time = time.time() - start_time  # 子进程运行秒数
            logger.info(
                f"daemon: {os.getpid()}, child process: {cmd.pid} exited {cmd.returncode}, elapsed time: {elapsed_time:.2f}"
            )
            if cmd.returncode == 0:
                sys.exit(0)  # 正常退出

            error_count += 1
            if self.max_error_count is not None and error_count > self.max_error_count:
                logger.info(
                    f"daemon: {os.getpid()}, child process: {cmd.pid} max error count reached"
                )
                sys.exit(1)
            # 根据错误次数指数退避
            sleep_time = 2**error_count
            logger.info(f"daemon: {os.getpid()} restarting in {sleep_time} seconds")
            time.sleep(sleep_time)

    def background(self, is_exit: bool) -> subprocess.Popen | None:
        """
        把本身程序转化为后台运行(启动一个子进程, 然后自己退出)

        :param is_exit: 启动子进程后是否直接退出主程序, 若为 False, 主程序返回 Popen 对象, 子程序返回 None
        :return: 如果是主进程, 返回子进程的 Popen 对象; 如果是子进程, 返回 None
        """
        global run_idx
        run_idx += 1

        try:
            env_idx = int(os.getenv(ENV_NAME, "0"))
        except ValueError:
            env_idx = 0

        if run_idx <= env_idx:  # 子进程, 退出
            return None

        # 设置子进程环境变量
        env = os.environ.copy()
        env[ENV_NAME] = str(run_idx)
        args = [sys.executable] + sys.argv

        with open(self.log_file, "a") as f:
            # 启动子进程
            cmd = subprocess.Popen(
                args=args,
                env=env,
                stdout=f,
                stderr=f,
                close_fds=True,
            )

        if is_exit:
            print(f"daemon: {cmd.pid} started")
            sys.exit(0)

        return cmd

    def __enter__(self):
        self.run()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            logger.exception(exc_val)
            sys.exit(1)
        sys.exit(0)
