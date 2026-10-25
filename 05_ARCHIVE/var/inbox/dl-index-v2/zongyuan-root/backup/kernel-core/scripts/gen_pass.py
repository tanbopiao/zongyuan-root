#!/usr/bin/env python3
"""生成密码的 PBKDF2 摘要令牌（密码不落盘、不打印）。输出请自行保存到安全位置。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kernel.core import crypto


def main():
    pw = input("输入密码（不回显，输入后回车）: ")
    token = crypto.derive(pw)
    print("摘要令牌（保存此令牌，不保存密码）:")
    print(token)
    print("校验方式: python3 -c \"from kernel.core import crypto; print(crypto.verify('你的密码', token))\"")


if __name__ == "__main__":
    main()
