# 电商图片批量处理工具

将旧版 Coze 图片处理 Agent 改写为可独立调用的 Python 工作流，并计划通过 Streamlit 提供简洁的网页入口。用户侧流程是上传图片、等待处理、下载结果；内部另有一次性测评系统，用固定样本生成展示报告。

> 当前进度：后端工作流已实现；Streamlit 双页面和固定测评报告尚未开发。本项目不承诺通过任何平台的重复内容检测，也不提供侵权判断。

## 产品设计

- [PRD：前端网页、后端工作流与内部测评系统](docs/PRD.md)
- 对外网页规划为产品展示页和图片使用页两个页面。
- 后端沿用七阶段顺序：几何处理、颜色处理、文字图层、贴纸图层、涂鸦图层、合成、导出。

## 已实现的后端

- 一次处理 1～20 张 JPG、PNG 或 WebP 图片，输出 1280×1706 像素的 PNG。
- 自动检测文字：有字或判断不确定时保留原方向；判断无字时才可能水平翻转。
- 每张图片独立处理、独立记录错误；成功结果可合并下载为 ZIP。
- 每批只检索一次 Openverse 素材并复用候选图片；无需 API key，检索失败时使用内置图案。
- 七个阶段在内存中传递图像，无需旧版的阶段间对象存储上传下载。

## 本地运行后端

建议使用 Python 3.12 或更新版本。在项目根目录安装依赖：

```bash
python -m pip install -r requirements-workflow.txt
```

贴纸阶段通过 [Openverse 图片接口](https://api.openverse.org/v1/)检索 CC0 或公有领域素材，无需申请 API key。在线接口不可用时自动使用内置图案。部署后仍需验证运行环境能否访问 Openverse。

```python
from pathlib import Path
from image_workflow import ImageInput, process_batch

source = Path("example.jpg")
batch = process_batch([ImageInput(source.name, source.read_bytes())])
if batch.successful:
    Path("processed.zip").write_bytes(batch.to_zip())
for result in batch.failed:
    print(result.input_name, result.stage, result.error)
```

运行测试：

```bash
python -m pytest tests -q
```

## 目录

```text
image_workflow/          后端工作流、OCR 与 Openverse 素材获取
tests/                   后端行为测试
docs/PRD.md              产品需求文档
requirements-workflow.txt  后端依赖
```

公开仓库只纳入新代码和产品文档。旧 Coze 导出及本地处理样例留在本地，未随仓库发布。
