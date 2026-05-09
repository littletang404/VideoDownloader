# 视频下载器 (VideoDownloader)

一个基于 PyQt6 和 yt-dlp 的视频下载工具，支持 YouTube、Bilibili、m3u8 直链等多种视频源的下载。

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![PyQt6](https://img.shields.io/badge/PyQt6-6.4+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 功能特性

- **多平台支持** - 支持 YouTube、Bilibili、微博、小红书、m3u8 直链等多种视频源
- **画质选择** - 自动获取可用画质列表，支持选择不同分辨率
- **Cookie 认证** - 支持导入 Cookie 下载需要登录的视频（如 Bilibili 4K）
- **自动合并** - 支持下载后自动合并音视频流
- **进度显示** - 实时显示下载进度条
- **任务历史** - 下载记录自动保存，重启后可查看
- **自定义命名** - 支持自定义下载文件名
- **深色主题** - 默认深色主题，护眼舒适
- **内置 ffmpeg** - 无需手动配置，开箱即用

## 界面预览

```
┌─────────────────────────────────────────────────────────┐
│  视频下载器                                             │
├─────────────────────────────────────────────────────────┤
│  [文件]  [工具]  [帮助]                                 │
├─────────────────────────────────────────────────────────┤
│  视频链接                                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 输入 YouTube、Bilibili 或 m3u8 链接...          │   │
│  └─────────────────────────────────────────────────┘   │
│  视频信息预览                                           │
│    标题: [可编辑的文件名                              ] │
│    画质: [1080p (最佳)                            ▼]   │
│    详情: 平台: youtube | 时长: 5分30秒 | 格式数: 12    │
├─────────────────────────────────────────────────────────┤
│  下载选项                                               │
│    Cookie: [YouTube     ▼] [导入文件] [粘贴文本] ✓ 已加载 │
│    保存路径: [C:\Users\Downloads            ] [浏览]  │
├─────────────────────────────────────────────────────────┤
│              [下载 >>>]   [转码 >>>]   [设置 >>>]      │
├─────────────────────────────────────────────────────────┤
│  下载任务                                   [清空记录]  │
│  ┌──────┬──────┬──────────┬────────┬───────┐           │
│  │ 标题 │ 画质 │ 进度     │ 状态   │ 操作  │           │
│  ├──────┼──────┼──────────┼────────┼───────┤           │
│  │ xxx  │ 1080 │ ████ 80% │ 下载中 │ [取消]│           │
│  │ yyy  │ 720  │ 100%     │ 已完成 │ [重试]│           │
│  └──────┴──────┴──────────┴────────┴───────┘           │
├─────────────────────────────────────────────────────────┤
│  就绪                                                   │
└─────────────────────────────────────────────────────────┘
```

## 安装运行

### 方式一：直接运行 EXE（推荐）

1. 下载 `VideoDownloader.exe`
2. 确保同目录下有 `tools`、`cookies`、`config` 文件夹
3. 双击运行即可

### 方式二：源码运行

```bash
# 克隆项目
git clone <repository_url>
cd VideoDownloader

# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
```

### 方式三：打包

```bash
# 安装 pyinstaller
pip install pyinstaller

# 运行打包脚本
build.bat
```

## 使用说明

### 1. 下载 YouTube 视频

1. 粘贴 YouTube 视频链接
2. 点击"解析"按钮
3. 选择画质
4. 可自定义文件名
5. 点击"下载 >>>"

### 2. 下载 Bilibili 视频（含 4K）

1. 先导入 Bilibili Cookie：
   - 方法一：点击"导入文件"选择 Cookie 文件
   - 方法二：点击"粘贴文本"直接粘贴 Cookie 内容
2. 粘贴视频链接
3. 解析并选择画质
4. 下载

> **提示**：Cookie 文件需为 Netscape 格式（可用 Chrome 插件"EditThisCookie"导出）

### 3. 下载 m3u8 直链

1. 粘贴 m3u8 链接
2. 点击"解析"（m3u8 会自动识别）
3. 选择"m3u8 直链"选项
4. 下载

### 4. 转码/格式转换

点击"转码 >>>"可以：
- 转换视频格式（MP4、MKV、AVI、MOV）
- 调整分辨率
- 压缩视频/音频
- 修改比特率

## 项目结构

```
VideoDownloader/
├── main.py                 # 程序入口
├── requirements.txt       # Python 依赖
├── build.bat              # 打包脚本
├── VideoDownloader.spec   # PyInstaller 配置
├── VideoDownloader.exe    # 打包后的可执行文件
├── core/                  # 核心模块
│   ├── __init__.py
│   ├── downloader.py      # 下载器（yt-dlp 封装）
│   ├── link_parser.py     # 链接解析
│   ├── cookie_manager.py  # Cookie 管理
│   ├── ffmpeg_handler.py  # ffmpeg 处理
│   └── task_manager.py    # 任务历史管理
├── ui/                    # UI 模块
│   ├── __init__.py
│   ├── main_window.py     # 主窗口
│   ├── settings_dialog.py # 设置对话框
│   └── transcode_dialog.py# 转码对话框
├── tools/                 # 工具目录
│   └── ffmpeg_bin/        # ffmpeg 二进制文件
├── cookies/               # Cookie 存储目录
├── config/                # 配置目录
│   └── settings.json      # 用户配置
└── release/              # 打包输出目录
```

## 配置文件说明

配置文件位于 `config/settings.json`：

```json
{
    "download_path": "下载默认保存路径",
    "max_concurrent": 3,              // 最大并发下载数
    "ffmpeg_custom": false,            // 是否使用自定义 ffmpeg
    "ffmpeg_path": "",                 // 自定义 ffmpeg 路径
    "deno_custom": false,              // 是否使用自定义 Deno
    "deno_path": "",                   // 自定义 Deno 路径
    "cookie_path": "cookies"           // Cookie 存储路径
}
```

## 常见问题

### Q: 下载失败，提示"no such option: --deno-path"
A: 这是 yt-dlp 版本问题，请更新：`pip install -U yt-dlp`

### Q: Bilibili 4K 下载失败
A: 需要导入有效的 Bilibili Cookie，确保 Cookie 未过期且包含必要权限

### Q: m3u8 下载进度不更新
A: 某些 m3u8 流不提供进度信息，这是正常现象，下载完成后会自动更新

### Q: 提示"ffmpeg not found"
A: 确保 `tools/ffmpeg_bin/ffmpeg.exe` 存在，或在设置中配置自定义 ffmpeg

## 技术栈

- **GUI**: PyQt6
- **下载引擎**: yt-dlp
- **视频处理**: ffmpeg
- **编程语言**: Python 3.8+

## 更新日志

### v1.1.0
- 移除抖音平台支持（Cookie 有效期过短，无法稳定使用）
- 新增微博、小红书平台支持
- UI 优化，Cookie 导入区域高度增加

### v1.0.1
- 深色主题 UI
- 任务历史持久化
- 自定义文件名

### v1.0.0
- 初始版本
- 支持 YouTube、Bilibili、m3u8 下载
- 基础下载功能

## 许可证

MIT License