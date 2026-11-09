"""Streamlit entry point for the image processing product."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from io import BytesIO

import streamlit as st
from PIL import Image, ImageOps

from image_workflow import BatchResult, ImageInput, process_batch
from homepage_deck import render_home


MAX_IMAGES = 20
BYTES_PER_IMAGE = 10_000_000
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SelectedImage:
    name: str
    data: bytes


def _init_state() -> None:
    defaults = {
        "selected_images": [],
        "upload_key_version": 0,
        "phase": "select",
        "batch_result": None,
        "processing_error": False,
        "upload_error": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _reset_upload_widget() -> None:
    st.session_state.upload_key_version += 1


def _receive_upload() -> None:
    """Merge a new picker selection with the confirmed list, then clear the picker."""
    key = f"image_upload_{st.session_state.upload_key_version}"
    files = st.session_state.get(key) or []
    current: list[SelectedImage] = st.session_state.selected_images
    incoming = [SelectedImage(file.name, file.getvalue()) for file in files]
    candidate = current + incoming
    _reset_upload_widget()
    if len(candidate) > MAX_IMAGES:
        st.session_state.selected_images = []
        st.session_state.upload_error = "最多上传 20 张图像"
    elif candidate and sum(len(item.data) for item in candidate) > len(candidate) * BYTES_PER_IMAGE:
        st.session_state.selected_images = []
        st.session_state.upload_error = "图片太大了"
    else:
        st.session_state.selected_images = candidate
        st.session_state.upload_error = None


def _remove_image(index: int) -> None:
    selected = list(st.session_state.selected_images)
    selected.pop(index)
    st.session_state.selected_images = selected


def _start_processing() -> None:
    if st.session_state.selected_images:
        st.session_state.phase = "processing"
        st.session_state.batch_result = None
        st.session_state.processing_error = False


def _new_batch() -> None:
    st.session_state.selected_images = []
    st.session_state.batch_result = None
    st.session_state.processing_error = False
    st.session_state.upload_error = None
    st.session_state.phase = "select"
    _reset_upload_widget()


def _preview(data: bytes) -> bytes | None:
    try:
        with Image.open(BytesIO(data)) as source:
            image = ImageOps.exif_transpose(source)
            image.thumbnail((420, 300))
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGB")
            output = BytesIO()
            image.save(output, format="PNG")
            return output.getvalue()
    except Exception:
        return None


def _render_selection() -> None:
    st.markdown('<div class="upload-anchor"></div>', unsafe_allow_html=True)
    st.file_uploader(
        "点击选择图片，或拖拽到这里",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key=f"image_upload_{st.session_state.upload_key_version}",
        on_change=_receive_upload,
        label_visibility="collapsed",
    )
    st.markdown(
        '<div class="upload-hint">支持 JPG、PNG、WebP · 最多上传 20 张图像'
        '<br><span>总大小不超过所选张数 × 10 MB</span></div>',
        unsafe_allow_html=True,
    )
    if st.session_state.upload_error:
        st.error(st.session_state.upload_error, icon="⚠️")
    selected: list[SelectedImage] = st.session_state.selected_images
    if selected:
        st.markdown(f'<h3 class="selection-heading">已选择 {len(selected)} 张图片</h3>', unsafe_allow_html=True)
        columns = st.columns(4)
        for index, item in enumerate(selected):
            with columns[index % 4]:
                with st.container(border=True):
                    thumbnail = _preview(item.data)
                    if thumbnail:
                        st.image(thumbnail, use_container_width=True)
                    else:
                        st.markdown('<div class="preview-unavailable">无法预览</div>', unsafe_allow_html=True)
                    st.caption(item.name)
                    st.button(
                        "移除", key=f"remove_{index}", on_click=_remove_image,
                        args=(index,), use_container_width=True,
                    )
    st.button(
        "开始处理", type="primary", disabled=not selected,
        on_click=_start_processing, use_container_width=True,
        key="start_processing",
    )
    st.markdown('<p class="privacy-note">上传图片仅用于本次处理。</p>', unsafe_allow_html=True)


def _run_batch() -> None:
    st.markdown(
        '<div class="processing-art" role="img" aria-label="图片加工动画">'
        '<span class="orbit orbit-one">✦</span><span class="orbit orbit-two">✧</span>'
        '<span class="image-card image-card-back"></span>'
        '<span class="image-card image-card-front"><span class="card-sun"></span>'
        '<span class="card-hill"></span></span><span class="orbit orbit-three">✦</span></div>'
        '<h2 class="state-title">图片正在加工中</h2>'
        '<p class="state-copy">稍后回来看看吧。</p>',
        unsafe_allow_html=True,
    )
    items = [ImageInput(item.name, item.data) for item in st.session_state.selected_images]
    try:
        st.session_state.batch_result = process_batch(items)
    except Exception:
        LOGGER.exception("Batch processing failed before a result was returned")
        st.session_state.processing_error = True
    st.session_state.phase = "done"
    st.rerun()


def _render_downloads(batch: BatchResult) -> None:
    successful = batch.successful
    if len(successful) == 1:
        image = successful[0]
        st.download_button(
            "下载 PNG", data=image.data, file_name=image.output_name,
            mime="image/png", type="primary", on_click="ignore",
            use_container_width=True,
        )
    elif len(successful) > 1:
        st.download_button(
            "下载全部 ZIP", data=batch.to_zip(), file_name="processed_images.zip",
            mime="application/zip", type="primary", on_click="ignore",
            use_container_width=True,
        )
        st.markdown('<h3 class="download-heading">也可以逐张下载</h3>', unsafe_allow_html=True)
        for index, image in enumerate(successful):
            col_name, col_button = st.columns([4, 1.4], vertical_alignment="center")
            col_name.write(image.output_name)
            col_button.download_button(
                "下载 PNG", data=image.data, file_name=image.output_name,
                mime="image/png", key=f"download_{index}", on_click="ignore",
                use_container_width=True,
            )


def _render_result() -> None:
    batch: BatchResult | None = st.session_state.batch_result
    if st.session_state.processing_error or batch is None or not batch.successful:
        st.markdown('<div class="result-art result-failed">↻</div>', unsafe_allow_html=True)
        st.markdown('<h2 class="state-title">本次图片未能处理</h2>', unsafe_allow_html=True)
        st.markdown('<p class="state-copy">请重新上传。</p>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="result-art" role="img" aria-label="图片处理完成">'
            '<span>✦</span><b>✓</b><span>✧</span></div>'
            '<h2 class="state-title">你的图片准备好啦！</h2>',
            unsafe_allow_html=True,
        )
        if batch.failed:
            st.warning("部分图片未能处理，其他结果可下载。", icon="⚠️")
        _render_downloads(batch)
    st.button("处理新图片", on_click=_new_batch, use_container_width=True, key="new_batch")


def _use_page() -> None:
    _init_state()
    if st.session_state.phase == "select":
        st.markdown(
            '<div class="use-hero"><div class="eyebrow">图片处理工作台</div>'
            '<h1> 你的图片准备好了吗？</h1>'
            '<p>选好图片，检查无误后开始处理。</p></div>',
            unsafe_allow_html=True,
        )
    with st.container():
        if st.session_state.phase == "select":
            _render_selection()
        elif st.session_state.phase == "processing":
            _run_batch()
        else:
            _render_result()


def _home_placeholder() -> None:
    st.markdown(
        '<div class="home-placeholder"><span class="eyebrow">图像去重处理器</span>'
        '<h1>首页正在准备中</h1><p>使用页已接入真实图片处理流程。</p></div>',
        unsafe_allow_html=True,
    )


STYLE = """
<style>
:root { --orange:#ed7133; --orange-deep:#d95e22; --ink:#282620; --muted:#77736e; --line:#eee8e2; }
[data-testid="stApp"] { background:#fff; color:var(--ink); }
[data-testid="stHeader"] { background:transparent; pointer-events:none; }
[data-testid="stMainBlockContainer"] {max-width:100%; padding-left:2rem;padding-right:2rem;padding-top:1.5rem;padding-bottom:1rem;}
div[data-testid="stToolbar"], #MainMenu, footer { visibility:hidden; }
.site-brand { font-size:26px; font-weight:750; letter-spacing:-.04em; line-height:1.4; }
.site-brand span { color:var(--orange); font-size:27px; vertical-align:-2px; }
.dev-placeholder { color:#a29c96; text-align:right; font-size:17px; line-height:1.4; white-space:nowrap; }
.st-key-top_nav [data-testid="stHorizontalBlock"] { align-items:center; }
.st-key-top_nav [data-testid="stColumn"] { display:flex; align-items:center; }
.st-key-top_nav [data-testid="stColumn"]:last-child { justify-content:flex-end; }
.st-key-top_nav [data-testid="stColumn"] > div { width:100%; }
.st-key-top_nav [data-testid="stPageLink"] a { color:#6d6862; font-size:30px; font-weight:600; line-height:1.4;position:relative; top:3px; }
.st-key-top_nav [data-testid="stPageLink"] a p {
    font-size:19px !important;}
[data-testid="stPageLink"] a:hover { color:var(--orange); }
.use-hero { text-align:center; padding:52px 0 25px; }
.eyebrow { color:var(--orange-deep); font-size:30px; font-weight:1000;line-height:2； letter-spacing:.15em; }
.use-hero h1,.home-placeholder h1 { font-size:clamp(35px,5vw,54px); line-height:0.5; letter-spacing:-.05em; margin:15px 0 15px; color:var(--ink); }
.use-hero h1 { position:relative; left:19px; }
.use-hero p,.home-placeholder p { color:var(--muted); font-size:19px; }
.upload-anchor + div [data-testid="stFileUploaderDropzone"] { min-height:168px; border:2px dashed #e7ac82; border-radius:16px; background:#f5f3f0; padding:25px; }
[data-testid="stFileUploaderDropzone"] { min-height:168px; border:2px dashed #e7ac82; border-radius:16px; background:#f5f3f0; padding:25px; display:flex; flex-direction:column-reverse; align-items:center; justify-content:center; gap:12px; }
[data-testid="stFileUploaderDropzone"] svg { display:none; }
[data-testid="stFileUploaderDropzoneInstructions"] > div { display:none; }
[data-testid="stFileUploaderDropzoneInstructions"] { text-align:center; }
[data-testid="stFileUploaderDropzoneInstructions"]::after { content:"点击选择图片，或拖拽到这里"; color:var(--ink); font-size:16px; font-weight:650; }
[data-testid="stFileUploaderDropzone"] button { color:white; background:var(--orange); border:0; border-radius:9px; font-size:0; }
[data-testid="stFileUploaderDropzone"] button::after { content:"选择图片"; font-size:13px; }
[data-testid="stFileUploaderDropzone"] button:hover { background:var(--orange-deep); color:white; }
.upload-hint { color:#77716b; text-align:center; font-size:13px; line-height:1.8; margin:-7px 0 18px; }
.upload-hint span { color:#9a948e; font-size:12px; }
.selection-heading,.download-heading { font-size:17px; margin:30px 0 16px; color:var(--ink); }
.preview-unavailable { display:grid; place-items:center; height:150px; background:#f6f4f2; color:#9b938c; font-size:13px; border-radius:8px; }
[data-testid="stImage"] img { border-radius:8px; object-fit:cover; max-height:145px; }
[data-testid="stVerticalBlockBorderWrapper"] { border-color:var(--line); }
div.stButton > button[kind="primary"], div.stDownloadButton > button[kind="primary"] { background:var(--orange); border-color:var(--orange); border-radius:9px; min-height:49px; font-weight:650; }
div.stButton > button[kind="primary"]:hover, div.stDownloadButton > button[kind="primary"]:hover { background:var(--orange-deep); border-color:var(--orange-deep); }
div.stButton > button[kind="primary"]:disabled { background:#eaded5; border-color:#eaded5; color:#a4968b; }
div.stButton > button[kind="secondary"], div.stDownloadButton > button[kind="secondary"] { border-radius:9px; border-color:#e7ded6; }
.privacy-note { text-align:center; color:#aaa39c; font-size:12px; margin-top:12px; }
.state-title { text-align:center; font-size:30px; letter-spacing:-.04em; margin:14px 0 6px; }
.state-copy { text-align:center; font-size:15px; color:var(--muted); margin:0 0 35px; }
.processing-art { position:relative; height:190px; width:220px; margin:35px auto 0; }
.image-card { position:absolute; width:104px; height:120px; left:58px; top:34px; background:#fff; border:4px solid #f2a36e; border-radius:13px; box-shadow:0 10px 30px #ed713327; }
.image-card-back { transform:rotate(-16deg) translate(-15px,4px); background:#ffe7d8; animation:card-rock 2.8s ease-in-out infinite; }
.image-card-front { transform:rotate(8deg); animation:card-float 2.8s ease-in-out infinite; overflow:hidden; }
.card-sun { position:absolute; width:24px; height:24px; border-radius:50%; background:#ffb65b; top:15px; right:15px; }
.card-hill { position:absolute; width:100px; height:70px; background:#f5b785; border-radius:48% 55% 0 0; left:-5px; bottom:-16px; transform:rotate(-18deg); }
.orbit { position:absolute; color:var(--orange); font-size:25px; animation:spark 1.8s ease-in-out infinite; }
.orbit-one { top:5px; left:12px; }.orbit-two { top:21px; right:8px; animation-delay:.5s; }.orbit-three { bottom:7px; right:35px; animation-delay:1s; }
@keyframes card-rock { 50% { transform:rotate(-10deg) translate(-11px,0); } }
@keyframes card-float { 50% { transform:rotate(5deg) translateY(-8px); } }
@keyframes spark { 50% { transform:scale(1.35); opacity:.55; } }
.result-art { width:148px; height:148px; border-radius:50%; background:#fff0e6; color:var(--orange); margin:33px auto 15px; display:flex; align-items:center; justify-content:space-evenly; font-size:25px; }
.result-art b { display:grid; place-items:center; width:72px; height:72px; border-radius:23px; background:var(--orange); color:#fff; font-size:41px; transform:rotate(-9deg); }
.result-failed { font-size:65px; }
.home-placeholder { text-align:center; padding:100px 20px; }
@media (prefers-reduced-motion:reduce) { .image-card,.orbit { animation:none !important; } }
@media (max-width:700px) {
  [data-testid="stMainBlockContainer"] { padding:0.5rem 1.2rem 4rem; }
  [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] { gap:8px; }
  [data-testid="stMainBlockContainer"] hr { margin:4px 0 !important; }
  .st-key-top_nav [data-testid="stHorizontalBlock"] { display:grid !important; grid-template-columns:auto auto minmax(0,1fr); align-items:center !important; column-gap:16px !important; row-gap:5px !important; }
  .st-key-top_nav [data-testid="stColumn"] { width:auto !important; min-width:0 !important; display:block; }
  .st-key-top_nav [data-testid="stColumn"]:first-child { grid-column:1 / -1; min-height:36px !important; }
  .st-key-top_nav [data-testid="stColumn"]:last-child { justify-self:end; min-height:20px !important; }
  .st-key-top_nav [data-testid="stPageLink"] a { top:0; font-size:15px !important; line-height:1.3; }
  .st-key-top_nav [data-testid="stPageLink"] a p { font-size:15px !important; }
  .site-brand { font-size:22px; white-space:nowrap; }
  .site-brand span { font-size:23px; }
  .dev-placeholder { font-size:11px; line-height:1.3; white-space:normal; }
  .use-hero { padding-top:12px; }
  .use-hero h1 { font-size:35px; }
  [data-testid="stFileUploaderDropzone"] { min-height:165px; }
}
</style>
"""


def main() -> None:
    st.set_page_config(page_title="图像去重处理器", page_icon="🟠", layout="wide", initial_sidebar_state="collapsed")
    st.markdown(STYLE, unsafe_allow_html=True)
    use = st.Page(_use_page, title="开始使用", url_path="use")
    home = st.Page(lambda: render_home(use), title="首页", url_path="home", default=True)
    current = st.navigation([use, home], position="hidden")
    with st.container(key="top_nav"):
        brand, home_link, use_link, developer = st.columns([2.6, 0.7, 1.1, 2.5], vertical_alignment="center")
        brand.markdown('<div class="site-brand">图像去重处理器 <span>✳</span></div>', unsafe_allow_html=True)
        home_link.page_link(home, label="首页")
        use_link.page_link(use, label="开始使用")
        developer.markdown('<div class="dev-placeholder">开发者介绍 ↗ · 即将开放</div>', unsafe_allow_html=True)
    st.divider()
    current.run()


if __name__ == "__main__":
    main()
