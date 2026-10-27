# 电商图片批量处理工具

一个面向内容电商运营场景的图片批处理项目，也是用于展示产品设计与工程实现的作品集项目。它将旧版 Coze 图片处理 Agent 改造成可独立调用的 Python 工作流，并规划通过 Streamlit 提供上传、处理和下载入口。

> **项目状态**：七阶段后端工作流已实现；Streamlit 使用页已有可运行初版，首页仍是占位页，固定样本测评报告尚未完成。网页尚未上线，部署环境行为仍需验证。

## 项目要解决的问题

旧版流程由多个图像处理工具串行组成，阶段之间需要反复上传和下载图片，也缺少独立的批处理入口。项目保留原有七阶段处理思路，将图像在单次任务内以内存方式传递，并为后续网页入口和可复核的固定样本测评预留产品方案。

## 产品方案

产品面向需要处理已有商品图片的内容运营人员。规划中的用户流程是：选择图片并核对、点击开始处理、等待处理、下载结果。对外网页包含产品展示页和图片使用页，顶栏另设跳转到开发者个人网站的外部链接；固定样本测评在内部运行，生成一次性展示报告，不由普通用户上传任务触发。前端规则见 [前端规则评审稿](docs/FRONTEND_RULES.md)。

图片处理的目标是让输出与输入在人眼观感上难以区分，同时在像素层面产生差异。项目不承诺平台查重、审核或推荐结果，也不提供侵权判断。

详细需求见 [产品需求文档](docs/PRD.md)。

## 当前已实现

- 每批处理 1～20 张 JPG、PNG 或 WebP 图片，输出 1280×1706 像素 PNG。
- 按“几何处理、颜色处理、文字图层、贴纸图层、涂鸦图层、合成、导出”的固定顺序处理图片。
- 使用文字检测决定是否水平翻转：确认无字时必定翻转；检测到文字、结果不确定或识别服务不可用时保留原方向。
- 每张图片独立处理并记录结果；单张失败不会阻断同批其他图片，成功结果可打包为 ZIP。
- 上传后立即处理图片，同时在后台随机检索、下载真实照片；下载成功一张，就供下一张运行到贴纸阶段的图片使用，并以 1% 透明度铺满画面。同批在线下载结果只分配一次，不维护跨批次使用记录。
- 单批在线等待达到截止时间或搜索、下载机会用尽后，从四张已下载且验证可读的真实照片中随机选择备用素材。
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

## 本地运行使用页

在项目根目录安装前端及后端依赖，然后启动 Streamlit：

```bash
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

使用页可选择图片、核对缩略图、调用真实后端处理并下载 PNG 或 ZIP；首页和开发者入口目前仅保留位置。前端规则及尚待部署验证的边界见 [前端规则](docs/FRONTEND_RULES.md)。

贴纸阶段使用 [Wikimedia Commons 图片搜索接口](https://commons.wikimedia.org/wiki/Commons:API/MediaWiki)，无需 API key。每批随机搜索并后台预取；最多同时进行一次搜索和两次下载，最多尝试下载图片数的两倍候选照片。贴纸阶段在照片池为空时等待下一张照片，等待窗口按实测取图基准时间的两倍计算。网络不可用时使用项目内已验证的 [Pexels 照片](https://www.pexels.com/legal-pages/license)，来源链接保存在 `image_workflow/stickers.py`。随机搜索不保证跨批次绝对不重复。

运行 `python -m scripts.measure_photo_fetch` 可在目标部署环境分别对 1、5、20 张规模做三次有效实网测量。取各规模耗时中位数，设置环境变量 `PHOTO_FETCH_X_1`、`PHOTO_FETCH_X_5`、`PHOTO_FETCH_X_20`（单位：秒）；其余规模线性插值。未设置时使用仓库内三次本地有效测量的中位数，分别为 30.656、44.722、96.892 秒。测量输出包含下载尝试数、在线成功数和失败原因；部署环境的连通性与等待时间需重新验证。

## 项目结构

```text
image_workflow/           后端工作流、OCR 与真实照片检索
assets/overlay_photos/    已验证的备用照片
tests/                    后端行为测试
docs/PRD.md               产品需求与验收标准
docs/FRONTEND_RULES.md    前端行为与文案
streamlit_app.py          Streamlit 使用页入口
requirements.txt          前端与后端依赖
requirements-workflow.txt 后端依赖
```

公开仓库纳入新代码和产品文档。旧 Coze 导出及本地处理样例未随仓库发布。
