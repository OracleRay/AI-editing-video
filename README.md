# 🎬 AI 视频处理工具

一个基于 AI 的视频剪辑和解说生成工具，能够自动识别视频内容、智能剪辑、生成 AI 解说，并一键导出为剪映（CapCut）项目。

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ 主要功能

### 🎯 完整处理流程
从原始视频到剪映项目的一站式处理：
1. **视频转音频** - 提取视频音轨
2. **音频转字幕** - AI 语音识别生成字幕
3. **AI 智能剪辑** - 分析内容自动剪辑
4. **AI 解说生成** - 根据剧情生成解说文案
5. **TTS 语音合成** - 将解说文案转为语音（支持声音克隆、倍速、音量调节）
6. **BGM 背景音乐** - 支持添加背景音乐（单文件或文件夹随机选择）
7. **OCR 字幕识别** - 识别原字幕在影片中的位置并使用模糊蒙版覆盖
8. **剪映项目生成** - 自动生成可导入的项目文件（⚠️ 仅支持最高JianYing Pro 5.9及以下版本）

### ✂️ AI 智能剪辑
- 自动分析视频内容
- 基于 AI 的精彩片段提取
- 根据字幕时间戳精确剪辑

### 🔄 批量生成解说
- 支持多次生成不同风格的解说
- 批量处理多个视频片段
- 自定义解说风格和语音

### 🎵 BGM 背景音乐
- 支持单文件模式：所有视频使用同一BGM
- 支持文件夹随机模式：每个视频随机选择不同BGM
- BGM音量独立调节
- 自动适配视频长度（过长裁剪，过短循环）

## 🖼️ 界面预览

工具提供现代化的图形界面，包含三个功能面板：
- **完整处理流程** - 一键完成所有步骤
- **AI 智能剪辑** - 单独执行剪辑功能
- **批量生成解说** - 批量处理解说任务

### 任务清单
界面右侧显示实时任务清单，清晰展示各项配置状态：
- ✓ 选择视频（必须）- 支持单文件或文件夹批量处理
- ✓ 选择克隆声音（必须）- TTS声音克隆参考音频
- ✓ 选择BGM（可选）- 单文件或文件夹随机模式
- ✓ 选择剪映目录（必须）- 导出目标路径
- ✓ 填写剧情（可选）- 剧情梗概辅助AI生成解说

## 📦 安装

### 环境要求
- Python 3.8+
- Windows 10/11
- FFmpeg（已内置于 `resources/src/ffmpeg/`）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 依赖说明

| 依赖包 | 版本 | 说明 |
|--------|------|------|
| PyYAML | ≥6.0 | 配置文件处理 |
| requests | ≥2.28.0 | HTTP 请求 |
| opencv-python | ≥4.8.0 | 视频处理 |
| Pillow | ≥10.0.0 | 图像处理 |
| paddleocr | ≥3.0.0 | OCR 字幕识别 |
| paddlepaddle | ≥2.5.0 | PaddlePaddle 框架 |

## 🚀 快速开始

### 1. 配置文件

编辑 `configs/config.yaml` 配置文件：

```yaml
# TTS 配置（基础配置，实际参数从UI界面设置）
tts:
  model: "Index-TTS-2"
  # 以下参数在UI中设置，此处作为默认值
  # reference_audio: 从UI选择克隆声音
  # speed: 从UI设置倍速（默认1.0）
  # volume: 从UI设置音量（默认1.0）
  
# ASR 配置
audio_to_subtitles:
  api_url: "your-asr-api-url"
  api_key: "your-asr-api-key"
```

> 💡 **注意**：TTS的克隆声音、倍速、音量等参数现在直接在UI界面中设置，无需修改配置文件。

### 2. 配置 Dify 工作流

编辑 `configs/config.yaml` 中的 `dify` 部分配置 AI 工作流 API：

```yaml
dify:
  user: "your-user-name"
  base_url: "http://your-dify-server/v1"
  workflows:
    commentary:
      api_key: "your-commentary-api-key"
      description: "AI解说工作流"
    editing:
      api_key: "your-editing-api-key"
      description: "AI剪辑工作流"
```

### 3. 启动应用

```bash
# 方式一：直接运行 Python
python UI/main.py

# 方式二：使用打包好的 exe (如果有)
./视频剪辑工具.exe
```


## 📁 项目结构

```
common_video/
├── configs/                # 配置文件
│   └── config.yaml        # 主配置（包含所有配置，包括 Dify API）
├── core/                   # 核心功能
│   ├── gen_json.py        # 剪映项目生成
│   └── video_editing.py   # 视频剪辑
├── dify/                   # Dify AI 工作流
│   ├── base.py            # 基础客户端
│   └── workflows.py       # 工作流调用
├── services/               # 服务层
│   ├── audio_to_subtitles.py  # 音频转字幕
│   ├── tts_client.py      # TTS 客户端（支持倍速、音量控制）
│   └── video_to_audio.py  # 视频转音频
├── UI/                     # 图形界面
│   ├── main.py            # 主界面入口
│   ├── components/        # UI 组件
│   │   ├── full_pipeline_panel.py  # 完整处理流程面板
│   │   ├── ai_editing_panel.py     # AI智能剪辑面板
│   │   └── multi_commentary_panel.py # 批量生成解说面板
│   ├── services/          # UI 服务层
│   │   └── pipeline_service.py     # 流程服务
│   └── utils/             # UI 工具
├── utils/                  # 工具函数
│   ├── config_loader.py   # 配置加载器
│   ├── loggers.py         # 日志系统
│   ├── meta_json.py       # 剪映 JSON 模板（含BGM轨道）
│   ├── audio_processor.py # 音频处理（BGM音量、时长调整）
│   ├── subtitle_detector/ # 字幕检测
│   └── ...
├── resources/              # 资源文件
│   ├── src/
│   │   ├── audios/        # 参考音频（克隆声音素材）
│   │   ├── ffmpeg/        # FFmpeg 可执行文件
│   │   └── srt_files/     # SRT 字幕文件
│   └── ui/
│       └── ai_cut.ico     # 应用图标
├── step.py                 # 处理步骤定义
└── requirements.txt        # 依赖列表
```

## 🔧 处理流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                        完整处理流程                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐     │
│  │  原始视频  │───▶│ 提取音频  │───▶│ 语音识别  │───▶│ AI剪辑   │     │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘     │
│                                                         │          │
│                                                         ▼          │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐     │
│  │ 剪映项目  │◀───│ TTS合成   │◀───│ AI解说   │◀───│ 视频剪辑  │     │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 🎨 特色功能

### 智能字幕检测
- 使用 PaddleOCR 自动检测视频中的字幕位置
- 自动生成字幕蒙版（模糊效果）
- 支持多种视频比例（16:9、4:3、9:16 等）

### 剪映项目生成
- 自动生成 `draft_content.json` 和 `draft_meta_info.json`
- 支持视频轨道、音频轨道、字幕轨道、BGM轨道
- 自动添加转场效果
- 可直接导入剪映专业版

### TTS 语音合成
- 支持声音克隆（从UI直接选择参考音频）
- 可调节语速（0.1-2.0倍速）
- 可调节音量（0.1-2.0）
- 批量生成音频文件

### BGM 背景音乐处理
- 使用 FFmpeg 进行音频处理
- 自动调整BGM音量
- 智能适配视频长度：
  - BGM过长：在视频结束处裁剪
  - BGM过短：自动循环播放
- 支持随机选择模式（文件夹内随机）

## 📝 使用示例

### GUI 界面使用

1. **选择视频**：点击"选择视频（文件/文件夹）"按钮
   - 单文件模式：处理单个视频
   - 文件夹模式：批量处理文件夹内所有视频

2. **选择克隆声音**：选择TTS参考音频文件（必须）

3. **设置TTS参数**：
   - 倍速：调整语音速度（默认1.0）
   - 音量：调整语音音量（默认1.0）

4. **选择BGM**（可选）：
   - 单文件模式：所有视频使用同一BGM
   - 文件夹模式：每个视频随机选择BGM

5. **选择剪映目录**：设置导出目标路径

6. **填写剧情**（可选）：提供剧情梗概帮助AI生成更好的解说

7. **开始处理**：点击"开始单次处理"或"开始循环处理"

### 代码调用

```python
from step import (
    step1_video_to_audio,
    step2_audio_to_subtitles,
    step3_ai_editing_workflow,
    step4_editing_text_to_srt,
    step5_edit_video,
    step6_refresh_timeline,
    step7_ai_commentary_workflow,
    step8_commentary_text_to_srt,
    step9_generate_capcut_project,
    step10_copy_project_to_destination
)

# 步骤 1：视频转音频
result1 = step1_video_to_audio()

# 步骤 2：音频转字幕
result2 = step2_audio_to_subtitles(
    result1["audio_output_path"],
    result1["video_src_path"]
)

# 步骤 3：AI 智能剪辑
result3 = step3_ai_editing_workflow(result2["original_text"])

# 步骤 9：生成剪映项目（支持BGM）
result9 = step9_generate_capcut_project(
    edited_video="path/to/video.mp4",
    commentary_srt_file="path/to/commentary.srt",
    reference_audio="path/to/voice.mp3",  # 克隆声音
    tts_speed=1.0,                         # TTS倍速
    tts_volume=1.0,                        # TTS音量
    bgm_path="path/to/bgm.mp3",           # BGM文件（可选）
    bgm_volume=0.5                         # BGM音量（可选）
)

# ... 后续步骤
```

### 自定义字幕样式

参考 `docs/字幕样式修改示例.md` 和 `examples/customize_subtitle_style.py`。

## ⚠️ 注意事项

1. **API 配置**：使用前请确保已正确配置 Dify API 和 TTS API
2. **FFmpeg**：项目已内置 FFmpeg，无需额外安装
3. **GPU 加速**：PaddleOCR 支持 GPU 加速，可安装 `paddlepaddle-gpu` 提升性能
4. **视频格式**：支持常见视频格式（mp4、avi、mkv、mov、flv、wmv 等）
5. **音频格式**：BGM支持常见音频格式（mp3、wav、m4a、flac、aac 等）
6. **剪映版本**：生成的项目仅支持 JianYing Pro 5.9 及以下版本
7. **TTS参数**：克隆声音、倍速、音量等参数在UI界面中设置，无需修改配置文件

## 🔨 打包

使用 PyInstaller 打包为可执行文件（以下命令执行其一即可）：

```bash
pyinstaller --onefile --windowed --icon=resources/ui/ai_cut.ico --name=视频剪辑工具 UI/main.py
pyinstaller ai_editing.spec
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

