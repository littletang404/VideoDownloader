from __future__ import annotations

import json
import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from VideoDownloader.core.cookie_manager import CookieManager
from VideoDownloader.core.downloader import Downloader
from VideoDownloader.core.link_parser import LinkParser
from VideoDownloader.core.runtime import (
    build_js_runtime_args,
    build_js_runtime_config,
    summarize_process_error,
)
from VideoDownloader.core.task_manager import TaskManager, TaskRecord
from VideoDownloader.utils import clean_filename


class LinkParserTests(unittest.TestCase):
    def setUp(self):
        self.parser = LinkParser()

    def test_platform_detection_and_generic_fallback(self):
        self.assertEqual(
            self.parser.identify_platform("https://youtu.be/example"),
            "youtube",
        )
        self.assertEqual(
            self.parser.identify_platform("https://www.bilibili.com/video/BV1"),
            "bilibili",
        )
        self.assertEqual(
            self.parser.identify_platform(
                "https://www.douyin.com/jingxuan?modal_id=7674463960687633317"
            ),
            "douyin",
        )
        self.assertEqual(
            self.parser.identify_platform("https://v.douyin.com/example/"),
            "douyin",
        )
        self.assertEqual(
            self.parser.identify_platform("https://cdn.example.com/a.m3u8?token=1"),
            "m3u8",
        )
        self.assertEqual(
            self.parser.identify_platform("https://example.com/video/123"),
            "generic",
        )
        self.assertIsNone(self.parser.identify_platform("not a url"))

    def test_douyin_jingxuan_normalization(self):
        self.assertEqual(
            self.parser.normalize_url(
                "https://www.douyin.com/jingxuan?modal_id=7674463960687633317"
            ),
            "https://www.douyin.com/video/7674463960687633317",
        )
        self.assertEqual(
            self.parser.normalize_url(
                "https://www.douyin.com/jingxuan/film?modal_id=7674444460905843995"
            ),
            "https://www.douyin.com/video/7674444460905843995",
        )
        unchanged = "https://www.douyin.com/jingxuan?foo=bar"
        self.assertEqual(self.parser.normalize_url(unchanged), unchanged)

    def test_available_heights_are_unique_and_descending(self):
        formats = [
            {"height": 1080, "vcodec": "h264"},
            {"height": 2160, "vcodec": "av1"},
            {"height": 1080, "vcodec": "vp9"},
            {"height": 0, "vcodec": "none"},
        ]
        self.assertEqual(self.parser.available_heights(formats), [2160, 1080])


class RuntimeTests(unittest.TestCase):
    def test_deno_cli_uses_current_combined_syntax(self):
        args = build_js_runtime_args("C:/tools/deno.exe")
        self.assertEqual(args[0], "--js-runtimes")
        self.assertTrue(args[1].startswith("deno:"))
        self.assertNotIn("--js-deno-path", args)

    def test_deno_api_config(self):
        config = build_js_runtime_config("C:/tools/deno.exe")
        self.assertIn("path", config["deno"])
        self.assertEqual(build_js_runtime_config(None), {"deno": {}})

    def test_bilibili_412_has_actionable_message(self):
        message = summarize_process_error(
            "ERROR: [BiliBili] Unable to download JSON metadata: "
            "HTTP Error 412: Precondition Failed"
        )
        self.assertIn("Bilibili", message)
        self.assertIn("HTTP 412", message)
        self.assertIn("Cookie", message)


    def test_douyin_fresh_cookie_error_is_localized(self):
        message = summarize_process_error(
            "ERROR: [Douyin] 123: Fresh cookies (not necessarily logged in) are needed"
        )
        self.assertIn("抖音", message)
        self.assertIn("Cookie", message)

class CookieManagerTests(unittest.TestCase):
    def test_json_cookie_import_and_validation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = CookieManager(temp_dir)
            payload = json.dumps(
                [
                    {
                        "domain": ".youtube.com",
                        "path": "/",
                        "secure": True,
                        "expirationDate": 2_000_000_000,
                        "name": "SID",
                        "value": "test-value",
                    }
                ]
            )
            self.assertTrue(manager.import_from_text("youtube", payload))
            self.assertTrue(manager.is_cookie_valid("youtube"))
            content = manager.load_cookie("youtube")
            self.assertIn("# Netscape HTTP Cookie File", content)
            self.assertIn("\tSID\ttest-value", content)


    def test_douyin_cookie_platform(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = CookieManager(temp_dir)
            payload = json.dumps([
                {
                    "domain": ".douyin.com",
                    "path": "/",
                    "secure": True,
                    "name": "ttwid",
                    "value": "fresh-test-cookie",
                }
            ])
            self.assertTrue(manager.import_from_text("douyin", payload))
            self.assertEqual(
                manager.auto_detect_platform(
                    "https://www.douyin.com/jingxuan?modal_id=1234567890"
                ),
                "douyin",
            )
            self.assertIsNotNone(manager.get_cookie_path_for_yt_dlp("douyin"))

class DownloaderTests(unittest.TestCase):
    def test_progress_hook_payload(self):
        payload = Downloader._progress_payload(
            {
                "status": "downloading",
                "downloaded_bytes": 50,
                "total_bytes": 100,
                "speed": 1024,
                "eta": 65,
            }
        )
        self.assertEqual(payload["progress"], 50)
        self.assertEqual(payload["eta"], "1:05")
        self.assertIn("/s", payload["speed"])


class TaskManagerTests(unittest.TestCase):
    def test_history_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = str(Path(temp_dir) / "history.json")
            manager = TaskManager(history_path)
            manager.add_record(
                TaskRecord(
                    url="https://example.com/video",
                    title="Example",
                    platform="generic",
                    format_id="best",
                    output_path=str(Path(temp_dir) / "video.mp4"),
                    status="completed",
                )
            )
            loaded = TaskManager(history_path)
            self.assertEqual(len(loaded.get_history()), 1)
            self.assertEqual(loaded.get_history()[0].title, "Example")


class UtilityTests(unittest.TestCase):
    def test_clean_filename(self):
        self.assertEqual(clean_filename('a:/b*?"<>|'), "a__b______")


if __name__ == "__main__":
    unittest.main()
