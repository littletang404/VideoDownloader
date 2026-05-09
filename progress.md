# 会话日志

## 2026-05-07

### 完成的工作

1. **yt-dlp 环境验证**
   - 下载 yt-dlp.exe 到 G: 盘根目录
   - 验证版本：2026.03.17

2. **Bilibili 4K 视频下载**
   - 使用 cookies 认证成功下载 4K 视频
   - 视频：BIGBANG 科切拉舞台完整版
   - 格式：3840x2160 H.264 + AAC
   - 文件大小：4.26 GB
   - 使用 ffmpeg 合并音视频

3. **YouTube 1080p 视频下载**
   - 安装 Deno 运行时处理 JS 签名
   - 使用 youtube_cookies.txt 认证
   - 下载格式：AV1 视频 + AAC 音频
   - 使用 ffmpeg 合并
   - 文件：Unreal Fest Stockholm 2025 Collection

4. **m3u8 直链下载（ikanbot）**
   - 从 vip.lz-cdn8.com 成功下载
   - 使用 ffmpeg 直接处理 m3u8 HLS 流
   - 成功下载约 1.27 GB 视频

### 技术要点记录
- yt-dlp 命令：`./yt-dlp -f "format" --cookies cookies.txt "url"`
- ffmpeg 合并：`ffmpeg -i video.mp4 -i audio.m4a -c copy output.mp4`
- m3u8 下载：`ffmpeg -i "url.m3u8" -c copy output.mp4`

## 2026-05-08

### 项目初始化
- 创建项目文件夹：G:/VideoDownloader/
- 初始化三个规划文件

### 需求确认
| 功能 | 确认 |
|------|------|
| 界面框架 | PyQt6 |
| 目标平台 | Windows |
| 支持平台 | YouTube、Bilibili、m3u8 直链 |
| Cookie 管理 | 界面填写接口（文件选择 + 文本粘贴） |
| 下载路径 | 界面填写接口（带浏览按钮） |
| 画质选择 | 解析后列出所有选项，默认最高画质 |
| ffmpeg 转码 | 内置转码功能 |

### 界面功能确认

**主界面**
- 视频链接输入 + 解析按钮
- 视频信息预览（标题、封面）
- 画质下拉选择（默认最高）
- Cookie 填写（YouTube、Bilibili）
- 下载路径设置（带浏览）
- 任务列表与进度

**转码功能**
- 输入/输出文件选择
- 输出格式选择（MP4/MKV/AVI/MOV）
- 视频编码选择（H.264/H.265/AV1/复制）
- 音频编码选择（AAC/MP3/FLAC/复制）
- 分辨率选择（原始/1080p/720p/自定义）

**设置窗口**
- 默认下载路径
- ffmpeg 路径
- 并发下载数量
- Deno 路径

### 项目结构
已设计项目架构，包含 core/、ui/、utils/、cookies/、config/、bundled/ 等目录

### 待办事项
1. 实现核心模块（downloader、ffmpeg_handler、link_parser、cookie_manager）
2. 开发 PyQt6 界面
3. 实现转码功能
4. 配置 PyInstaller 打包
5. 测试与文档
