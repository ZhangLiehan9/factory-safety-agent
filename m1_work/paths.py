#!/usr/bin/env python3
"""视频 URI 与本地绝对路径之间的解析。

事件卡里只保存与机器无关的 URI：

    saferaw://test/0_safe_walkway_violation/0_te21.mp4

解析时用当前 DATASET_ROOT 拼接。目录名含空格（如 2_opened_panel cover）
在 URI 中做百分号编码，因此 JSON 里不会出现裸空格。
"""
import os
from urllib.parse import quote, unquote

try:
    from . import config
except ImportError:  # 以脚本方式直接运行本文件时
    import config


def to_rel(abs_path, root=None):
    """绝对路径 -> 相对数据集根的 posix 路径。"""
    root = os.path.abspath(root or config.DATASET_ROOT)
    rel = os.path.relpath(os.path.abspath(abs_path), root)
    if rel.startswith(".."):
        raise ValueError("路径不在数据集根目录内: {}".format(abs_path))
    return rel.replace(os.sep, "/")


def to_uri(abs_path, root=None):
    """绝对路径 -> saferaw:// URI。"""
    return "{}://{}".format(config.URI_SCHEME, quote(to_rel(abs_path, root), safe="/"))


def resolve_uri(uri, root=None):
    """URI -> {ok, abs_path, rel_path, error}。不抛异常，错误以字段返回。"""
    root = os.path.abspath(root or config.DATASET_ROOT)
    prefix = config.URI_SCHEME + "://"
    if not isinstance(uri, str) or not uri.startswith(prefix):
        return {
            "ok": False,
            "error": "invalid_uri",
            "abs_path": None,
            "rel_path": None,
            "detail": "URI 必须以 {}// 开头: {}".format(config.URI_SCHEME, uri),
        }
    rel = unquote(uri[len(prefix):]).lstrip("/")
    if not rel or ".." in rel.split("/"):
        return {"ok": False, "error": "invalid_uri", "abs_path": None,
                "rel_path": None, "detail": "URI 路径非法: {}".format(uri)}
    abs_path = os.path.join(root, *rel.split("/"))
    if not os.path.isfile(abs_path):
        return {"ok": False, "error": "not_found", "abs_path": abs_path,
                "rel_path": rel, "detail": "文件不存在: {}".format(abs_path)}
    return {"ok": True, "error": None, "abs_path": abs_path, "rel_path": rel}


def check_root(root=None):
    """检查数据集根目录是否可用，返回 (ok, message)。"""
    root = os.path.abspath(root or config.DATASET_ROOT)
    if not os.path.isdir(root):
        return False, "数据集根目录不存在: {}\n可用环境变量 DATASET_ROOT 指定".format(root)
    missing = [s for s in config.SPLITS if not os.path.isdir(os.path.join(root, s))]
    if missing:
        return False, "根目录 {} 下缺少划分目录: {}".format(root, ", ".join(missing))
    return True, root
