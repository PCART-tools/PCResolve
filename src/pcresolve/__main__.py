## @package pcresolve.__main__
#  Command-line entry point for the PCResolve package.
#  PCResolve 包的命令行入口。

from .cli import main

# Keep module execution behavior aligned with the installed console script.
# 保持模块执行行为与安装后的控制台脚本一致。
main()
