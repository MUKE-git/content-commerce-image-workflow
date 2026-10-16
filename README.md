# 电商图片批量处理工具

一个面向内容电商运营场景的图片批处理项目，也是用于展示产品设计与工程实现的作品集项目。它将旧版 Coze 图片处理 Agent 改造成可独立调用的 Python 工作流，并规划通过 Streamlit 提供上传、处理和下载入口。

> **项目状态**：七阶段后端工作流已实现；Streamlit 前端和固定样本测评报告尚未完成。当前仓库可运行后端工作流，不应将规划中的网页功能误认为已上线能力。

## 项目要解决的问题

旧版流程由多个图像处理工具串行组成，阶段之间需要反复上传和下载图片，也缺少独立的批处理入口。项目保留原有七阶段处理思路，将图像在单次任务内以内存方式传递，并为后续网页入口和可复核的固定样本测评预留产品方案。

## 产品方案

产品面向需要处理已有商品图片的内容运营人员。规划中的用户流程是：上传图片、等待自动处理、下载结果。对外网页分为产品展示页和图片使用页；固定样本测评在内部运行，生成一次性展示报告，不由普通用户上传任务触发。

图片处理的目标是让输出与输入在人眼观感上难以区分，同时在像素层面产生差异。项目不承诺平台查重、审核或推荐结果，也不提供侵权判断。

详细需求见 [产品需求文档](docs/PRD.md)。

## 当前已实现

- 每批处理 1～20 张 JPG、PNG 或 WebP 图片，输出 1280×1706 像素 PNG。
- 按“几何处理、颜色处理、文字图层、贴纸图层、涂鸦图层、合成、导出”的固定顺序处理图片。
- 使用文字检测辅助决定是否水平翻转；检测到文字、结果不确定或识别服务不可用时保留原方向。
- 每张图片独立处理并记录结果；单张失败不会阻断同批其他图片，成功结果可打包为 ZIP。
- 每张图独立随机检索真实照片，并以 1% 透明度铺满画面；不维护跨批次去重列表。
- 在线检索或下载失败时，从四张已下载且验证可读的真实照片中随机选择备用素材。
- 七个阶段以内存传递图像，不需要阶段间远程对象存储上传和下载。

上述描述是当前代码行为，不代表测评已经证明所有输入下都能达到预期视觉效果。测评方案和报告状态见 PRD 的“测试”部分。

## 本地运行后端

建议使用 Python 3.12 或更新版本。在项目根目录安装依赖：

```bash
python -m pip install -r requirements-workflow.txt
```

运行示例：

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

贴纸阶段使用 [Wikimedia Commons 图片搜索接口](https://commons.wikimedia.org/wiki/Commons:API/MediaWiki)。每张图片重新随机选择搜索词、结果偏移和候选照片，无需 API key。网络不可用时使用项目内已验证的 [Pexels 照片](https://www.pexels.com/legal-pages/license)，来源链接保存在 `image_workflow/stickers.py`。随机搜索不承诺所有任务绝对不重复；部署环境的在线检索仍需验证。

## 项目结构

```text
image_workflow/           后端工作流、OCR 与真实照片检索
assets/overlay_photos/    已验证的备用照片
tests/                    后端行为测试
docs/PRD.md               产品需求与验收标准
requirements-workflow.txt 后端依赖
```

公开仓库纳入新代码和产品文档。旧 Coze 导出及本地处理样例未随仓库发布。
