# 万能视频下载器

一个面向 Windows 的现代化桌面视频下载工具，基于 PyQt6、yt-dlp 与 ffmpeg。

**当前稳定版：v2.0.4** — 可在 [GitHub Releases](https://github.com/littletang404/VideoDownloader/releases/latest) 下载 Windows 成品。

它会先解析链接，再把复杂的媒体流整理成“最佳画质、1080p、720p、仅音频”等常用选项。YouTube、Bilibili、抖音、微博、小红书、m3u8 直链有专门识别，其他 HTTP(S) 链接会交给 yt-dlp 的通用解析器尝试处理。

> 请只下载你有权保存和使用的内容，并遵守网站条款与当地法律。

## v2.0.4 更新

- 修复 Bilibili HTTP 412 解析问题并更新 yt-dlp
- 支持抖音视频、精选页 modal_id、film 页面和分享短链接
- 增加 YouTube、Bilibili、抖音 Cookie 独立管理
- 增加原创应用图标，并应用到窗口和 Windows EXE
- 优化画质名称：4K、2K、全高清、高清、标清和流畅
- 发布包内置 ffmpeg、ffprobe 与 Deno，开箱即可使用

完整成品请从 Releases 下载；源码仓库不会包含 Cookie、下载历史或个人设置。

## v2.0 主要变化

- 重新设计主界面：链接、媒体摘要、下载设置和任务状态一屏完成
- 画质选项从原始格式 ID 改为用户能理解的常用预设
- 使用内嵌 yt-dlp Python API，不再依赖外部 yt-dlp 命令
- 下载进度使用官方 progress hook，显示百分比、速度和剩余时间
- 修复排队并发、取消后误报失败、历史记录被刷新丢失等问题
- Cookie 移入独立管理窗口，只保存在本机
- 自动检测 ffmpeg、ffprobe 和 Deno，也可在设置中指定路径
- 修复转码默认输出、手动路径、真实进度和运行中关闭问题
- 配置与历史路径不再依赖程序从哪个目录启动
- 新构建流程不会复制 Cookie、历史记录或整套剪映程序目录

## 支持范围

常用平台：

- YouTube
- Bilibili
- 抖音视频、精选页链接与分享短链接
- 微博与微博短链接
- 小红书与分享短链接
- m3u8 / HLS 直链
- yt-dlp 当前支持的其他公开 HTTP(S) 视频页面

“万能”代表尽量复用 yt-dlp 的站点支持能力，并不意味着所有网站都能永久下载。网站规则、登录校验和反爬机制会变化，请保持 yt-dlp 为最新版本。

## 环境要求

- Windows 10/11
- Python 3.10 或更高版本
- ffmpeg 与 ffprobe
- Deno 2.3 或更高版本（YouTube 当前推荐）

程序会依次查找：

1. 设置中选择的自定义工具
2. 程序旁边的 `tools` 目录
3. 开发目录中的常见工具位置
4. 系统 PATH

如果工具缺失，主窗口顶部和设置窗口会明确提示。

## 源码运行

在项目目录的上一级执行，或保持当前包目录名为 `VideoDownloader`：

```powershell
python -m pip install -r VideoDownloader\requirements.txt
python VideoDownloader\main.py
```

也可以在项目目录执行：

```powershell
python -m pip install -r requirements.txt
python main.py
```

## 基本使用

1. 粘贴视频链接，点击“解析视频”
2. 检查标题、来源与时长
3. 选择最佳画质、指定分辨率或仅音频
4. 修改保存名称与保存位置
5. 点击“开始下载”
6. 在任务区查看进度、速度与结果

需要登录的内容：

1. 点击右上角“Cookie”
2. 选择 YouTube、Bilibili 或抖音
3. 导入 Netscape `cookies.txt`，或粘贴浏览器插件导出的 JSON
4. 回到主界面重新解析链接

Cookie 只写入本机 `cookies` 目录。不要把自己的 Cookie 文件发送给他人；它可能等同于账号登录凭据。

抖音经常要求刚从浏览器导出的 Cookie，即使公开视频也可能如此。请先在浏览器打开并播放目标视频，再导出最新 Cookie 后立即导入。

## 视频转换

点击右上角“视频转换”，可以选择：

- MP4、MKV、MOV、AVI 容器
- 保持原编码、H.264、H.265、AV1
- AAC、原音频、MP3、FLAC
- 原始、4K、1080p、720p 或自定义分辨率

调整分辨率时必须重新编码，程序会自动从“保持原编码”切换到 H.264。

## 设置与本地数据

运行后会在程序目录创建：

```text
config/settings.json       用户设置
config/task_history.json   最近下载历史
cookies/                   用户导入的 Cookie
```

这些文件已被 Git 忽略，也不会被新的构建脚本复制进发布包。

## 自动化测试

```powershell
python -m unittest discover -s tests -v
python -m py_compile main.py core\*.py ui\*.py utils\*.py
```

核心测试覆盖链接识别、Deno 参数、Cookie 转换、任务历史、进度计算和文件名清理。

## Windows 打包

```powershell
build.bat
```

构建结果位于：

```text
dist/
├── VideoDownloader.exe
└── tools/
    ├── ffmpeg.exe   可选，找到本地工具时自动复制
    ├── ffprobe.exe  可选
    └── deno.exe     可选
```

打包脚本使用 `VideoDownloader.spec`，会收集 yt-dlp 及匹配的 EJS 组件。它不会复制 `cookies`、`config`、旧 `release` 或 `tools/ffmpeg_bin` 中的第三方程序。

如果 `dist/tools` 中没有工具，用户仍可在设置里选择本机已有的 ffmpeg 与 Deno。

## 项目结构

```text
VideoDownloader/
├── main.py
├── core/
│   ├── downloader.py
│   ├── link_parser.py
│   ├── cookie_manager.py
│   ├── ffmpeg_handler.py
│   ├── runtime.py
│   └── task_manager.py
├── ui/
│   ├── main_window.py
│   ├── cookie_dialog.py
│   ├── settings_dialog.py
│   ├── transcode_dialog.py
│   └── theme.py
├── utils/
│   └── paths.py
├── tests/
├── VideoDownloader.spec
├── build.bat
└── requirements.txt
```

## 常见问题

### YouTube 提示 JavaScript runtime 不可用

安装 Deno 2.3+，然后重启程序；或者在“设置 → 工具”中选择 `deno.exe`。

### 解析成功但高画质下载失败

高画质通常需要分别下载视频和音频再合并，请确认 ffmpeg 与 ffprobe 均可用。

### Bilibili 会员画质缺失

导入仍然有效、且拥有相应权限的 Bilibili Cookie，然后重新解析。

### 某个网站突然不能下载

先更新依赖：

```powershell
python -m pip install -U "yt-dlp[default]"
```

网站支持会随站点规则变化，必要时查看 yt-dlp 项目的最新说明。
