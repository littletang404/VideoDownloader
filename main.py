"""VideoDownloader - 视频下载器

支持 YouTube、Bilibili、m3u8 直链下载
内置 ffmpeg 转码功能
"""
import sys
import os
import json
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from VideoDownloader.ui.main_window import MainWindow


def load_config() -> dict:
    """加载配置"""
    config_path = Path('config/settings.json')
    default_config = {
        'download_path': str(Path.home() / 'Downloads'),
        'max_concurrent': 3,
        'ffmpeg_custom': False,
        'ffmpeg_path': '',
        'deno_custom': False,
        'deno_path': '',
        'cookie_path': 'cookies',
    }

    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 合并默认配置
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        except Exception as e:
            print(f"加载配置失败: {e}")

    return default_config


def main():
    """主函数"""
    # 创建应用
    app = QApplication(sys.argv)
    app.setApplicationName("视频下载器")
    app.setOrganizationName("VideoDownloader")

    # 加载配置
    config = load_config()

    # 创建并显示主窗口
    window = MainWindow(config)
    window.show()

    # 运行应用
    sys.exit(app.exec())


if __name__ == '__main__':
    main()