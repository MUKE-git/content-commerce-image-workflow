"""Public homepage. The image pairs and scores are supplied by the project owner."""

from __future__ import annotations

import base64
from html import escape
from pathlib import Path

import streamlit as st
from PIL import Image, ImageOps
from io import BytesIO


ASSETS = Path(__file__).parent / "assets" / "homepage"

CASES = (
    {"id": "01", "name": "灰色外套", "kind": "上身展示图", "original": "K0.jpg", "result": "01_K_processed.png", "score": "3.70", "ssim": "0.432022", "psnr": "12.3883 dB", "mse": "3751.8657", "mad": "42.2439"},
    {"id": "02", "name": "粉色袖口", "kind": "局部展示图（有文字）", "original": "B.jpg", "result": "02_B_processed.png", "score": "35.78", "ssim": "0.696924", "psnr": "19.3066 dB", "mse": "762.8218", "mad": "11.4385"},
    {"id": "03", "name": "米色上衣", "kind": "上身展示图（含干扰文字）", "original": "D.png", "result": "03_D_processed.png", "score": "12.95", "ssim": "0.536451", "psnr": "14.5751 dB", "mse": "2267.6090", "mad": "24.0449"},
)

STAGES = (
    ("01", "几何处理", "轻调构图，照顾画面里的文字", "微调角度与位置；只在画面无文字时水平翻转图片", "Pillow · RapidOCR · Tesseract"),
    ("02", "颜色处理", "给色彩做细微调整", "对亮度、对比度、饱和度和清晰度进行小幅处理，让主体保持可辨。", "Pillow ImageEnhance"),
    ("03", "文字图层", "加入低可见度文字纹理", "在独立图层上铺设文字纹理，参与后续合成。", "Pillow ImageDraw"),
    ("04", "贴纸图层", "融入真实照片纹理", "随机检索真实照片并以 1% 强度覆盖画面；在线素材不可用时使用备用照片。", "Wikimedia Commons · Pexels"),
    ("05", "涂鸦图层", "增加细小图形变化", "在独立图层绘制线条与形状，让画面细节产生差异。", "Pillow ImageDraw"),
    ("06", "合成", "把多层变化合为一张图", "将处理后的底图与低透明度纹理层合成，形成最终画面。", "Pillow 图层合成"),
    ("07", "导出", "得到可下载的 PNG", "每张图独立导出为 1280×1706 像素 PNG；多张成功结果可打包下载。", "Pillow PNG 导出 · 批次管理"),
)

STYLE = """
<style>
.home-root { font-family:"Microsoft YaHei","PingFang SC",Arial,sans-serif; color:#26251f; }
.home-root * { box-sizing:border-box; }
.home-section { max-width:1380px; margin:0 auto; padding:80px clamp(20px,4vw,72px); }
.home-kicker { display:inline-flex; align-items:center; gap:10px; color:#b4512d; font-size:13px; font-weight:800; letter-spacing:.13em; }
.home-kicker::before { content:""; width:27px; height:2px; background:#ed7133; }
.home-section h2 { font-size:clamp(32px,3.4vw,48px); line-height:1.25; letter-spacing:-.05em; margin:18px 0 15px; }
.home-lead { color:#66645e; font-size:17px; line-height:1.8; max-width:780px; }
.home-hero { padding-top:42px; padding-bottom:64px; background:radial-gradient(circle at 82% 20%,#fff0e5 0,transparent 28%),#faf8f3; border-radius:28px; }
.home-hero h1 { font-size:clamp(49px,5vw,78px); line-height:1.15; letter-spacing:-.07em; margin:23px 0 18px; }
.home-hero h1 small { display:block; font-size:.58em; letter-spacing:-.04em; }
.home-hero h1 em { display:block; color:#ed7133; font-style:normal; white-space:nowrap; }
.home-hero .home-lead { margin:0 0 26px; }
.home-metrics { display:grid; grid-template-columns:1fr 1fr; gap:14px; margin:0 0 15px; }
.home-metric { min-height:142px; border:1px solid #e7dfd3; border-radius:18px; padding:20px; background:#fff; }
.home-metric.orange { background:#ed7133; color:#fff; border-color:#ed7133; transform:rotate(-1deg); }
.home-metric span { display:block; font-size:13px; font-weight:750; opacity:.8; }
.home-metric strong { display:block; font-size:clamp(25px,2.6vw,39px); line-height:1.25; margin:9px 0 5px; white-space:nowrap; }
.home-metric small { font-size:12px; opacity:.8; }
.home-footnote { color:#827f75; font-size:11px; line-height:1.65; margin:16px 0 0; }
.st-key-home_action_hero [data-testid="stPageLink"] a,.st-key-home_action_footer [data-testid="stPageLink"] a { display:inline-flex; justify-content:center; border-radius:999px; padding:11px 24px; background:#282620; color:#fff !important; }
.st-key-home_action_hero [data-testid="stPageLink"] a p,.st-key-home_action_footer [data-testid="stPageLink"] a p { color:#fff !important; font-size:16px !important; font-weight:800; }
.st-key-home_action_hero [data-testid="stPageLink"],.st-key-home_action_footer [data-testid="stPageLink"] { width:max-content; }
.home-result-note { text-align:center; color:#827e76; font-size:12px; line-height:1.6; }
.home-section.alt { background:#faf8f3; border-radius:28px; }
.home-stat-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:18px; margin:28px 0 18px; }
.home-stat { padding:28px; border-radius:18px; background:#fff; border:1px solid #e8e1d8; }
.home-stat span { font-size:13px; color:#8a7767; font-weight:800; }
.home-stat strong { display:block; margin:10px 0 6px; font-size:clamp(30px,3.2vw,48px); color:#ed7133; letter-spacing:-.05em; }
.home-stat small { color:#77736d; font-size:14px; }
.home-measure { margin-top:35px; padding:28px 30px; border-left:4px solid #ed7133; background:#fff; border-radius:0 17px 17px 0; }
.home-measure h3 { margin:0 0 8px; font-size:24px; }
.home-measure p { margin:0; color:#66645e; line-height:1.8; }
.home-stage-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:15px; margin-top:30px; }
.home-stage { border:1px solid #e8e1d8; border-radius:18px; padding:23px 25px; background:#fff; }
.home-stage-num { color:#ed7133; font-weight:900; font-size:14px; letter-spacing:.1em; }
.home-stage h3 { font-size:21px; margin:12px 0 8px; }
.home-stage strong { display:block; font-size:15px; margin-bottom:8px; }
.home-stage p { color:#66645e; line-height:1.7; margin:0 0 13px; font-size:14px; }
.home-stage small { color:#ad6947; font-size:12px; }
.st-key-home_case_01,.st-key-home_case_02,.st-key-home_case_03 { padding:25px; border:1px solid #e8e1d8; border-radius:24px; background:#fff; margin:26px 0; box-shadow:0 16px 36px #4a3c2110; }
.home-case-head { display:flex; align-items:baseline; justify-content:space-between; gap:14px; flex-wrap:wrap; }
.home-case-head h3 { margin:0 0 15px; font-size:25px; }
.home-case-head span { color:#b65b31; font-size:13px; font-weight:800; }
.home-score { display:flex; align-items:baseline; gap:16px; flex-wrap:wrap; padding:15px 0; }
.home-score strong { color:#ed7133; font-size:32px; }
.home-score span { color:#605e57; font-size:14px; }
.home-four { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; }
.home-four div { background:#faf8f3; border-radius:12px; padding:13px; }
.home-four small { display:block; color:#77736e; margin-bottom:6px; }
.home-four b { font-size:16px; }
.home-case-copy { color:#66645e; margin:16px 0 0; }
.home-sources { color:#77736e; font-size:13px; line-height:1.8; margin-top:20px; }
.home-sources a { color:#b4512d; }
.home-footer { text-align:center; padding:92px 20px; background:#282620; color:#fff; border-radius:28px; }
.home-footer h2 { color:#fff; }
.home-footer p { color:#e1dcd4; }
.st-key-home_action_footer [data-testid="stPageLink"] { margin:0 auto; }
.st-key-home_action_footer [data-testid="stPageLink"] a { background:#ed7133; }
@media(max-width:900px) { .home-section { padding:52px 20px; } .home-hero { padding:42px 22px; } .home-stage-grid { grid-template-columns:1fr; } }
@media(max-width:620px) { .home-hero h1 { font-size:clamp(37px,9vw,51px); } .home-metrics,.home-stat-grid { grid-template-columns:1fr; } .home-metric { min-height:110px; } .home-four { grid-template-columns:repeat(2,1fr); } .home-section h2 { font-size:33px; } }
</style>
"""


@st.cache_data(show_spinner=False)
def _image_data(name: str) -> str:
    """Produce a compact display image while preserving the supplied originals on disk."""
    with Image.open(ASSETS / name) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        image.thumbnail((1100, 1500))
        out = BytesIO()
        image.save(out, "JPEG", quality=84, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(out.getvalue()).decode("ascii")


def _comparison(case: dict[str, str], *, height: int = 510) -> None:
    before = _image_data(case["original"])
    after = _image_data(case["result"])
    title = escape(case["name"])
    st.iframe(
        f"""<!doctype html><html lang="zh-CN"><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>
        *{{box-sizing:border-box}}body{{margin:0;font-family:Arial,'Microsoft YaHei',sans-serif}}
        .frame{{position:relative;width:100%;height:{height-10}px;overflow:hidden;border-radius:17px;background:#e6e0d7;isolation:isolate}}
        img{{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;background:#eee9e2}}
        .after{{clip-path:inset(0 50% 0 0)}}.line{{position:absolute;z-index:3;top:0;bottom:0;left:50%;width:3px;background:#fff;pointer-events:none;box-shadow:0 0 0 1px #0002}}
        .handle{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:46px;height:46px;display:grid;place-items:center;border-radius:50%;background:#fff;color:#ed7133;box-shadow:0 4px 15px #0003;font-size:19px;font-weight:bold}}
        .tag{{position:absolute;z-index:4;top:15px;padding:8px 12px;border-radius:30px;background:#fff;color:#282620;font-size:12px;font-weight:bold;pointer-events:none}}
        .tag.left{{left:15px}}.tag.right{{right:15px}}input{{position:absolute;z-index:5;inset:0;width:100%;height:100%;margin:0;opacity:0;cursor:ew-resize}}
        </style></head><body><div class="frame" aria-label="{title}原图与处理后拖动对比">
        <img src="{before}" alt="{title}原图"><img class="after" src="{after}" alt="{title}处理后">
        <div class="line"><div class="handle">↔</div></div><span class="tag left">处理后</span><span class="tag right">原图</span>
        <input type="range" min="0" max="100" value="50" aria-label="拖动查看{title}处理前后对比"></div>
        <script>const x=document.querySelector('input'),a=document.querySelector('.after'),l=document.querySelector('.line');x.oninput=()=>{{a.style.clipPath=`inset(0 ${{100-x.value}}% 0 0)`;l.style.left=x.value+'%'}};</script></body></html>""",
        height=height,
    )


def _section_start(number: str, kicker: str, title: str, lead: str) -> None:
    st.markdown(f'<div class="home-root home-section"><div class="home-kicker">{number} / {kicker}</div><h2>{title}</h2><p class="home-lead">{lead}</p></div>', unsafe_allow_html=True)


def render_home(use_page: st.Page) -> None:
    st.markdown(STYLE, unsafe_allow_html=True)

    # 1. Hero: the B pair is the approved lead visual.
    left, right = st.columns([1.05, .95], gap="large", vertical_alignment="center")
    with left:
        st.markdown('''<div class="home-root home-section home-hero"><div class="home-kicker">给内容电商运营的批量图片处理工具</div><h1><small>把图片交给工具</small><em>把时间留给内容</em></h1><p class="home-lead">一次提交，批量处理，拒绝重复</p><div class="home-metrics"><div class="home-metric orange"><span>满批量 · 本次测试约</span><strong>20 张约 11 分钟</strong><small>平均 33 秒／张</small></div><div class="home-metric"><span>项目方提供的同批对照数据</span><strong>效率约提升 264%</strong><small>人工约 40 分钟 · 工具约 11 分钟</small></div></div><p class="home-footnote">据项目方提供的同批对照数据：人工处理 20 张约 40 分钟，工具处理同批图片约 11 分钟。按单位时间处理张数计算，效率约提升 264%；实际耗时随图片和运行环境变化。</p></div>''', unsafe_allow_html=True)
        with st.container(key="home_action_hero"):
            st.page_link(use_page, label="开始使用 ↗")
            st.markdown('<a href="#home-cases" style="color:#b4512d;font-weight:750">看看处理效果 ↓</a>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="home-root" style="text-align:center;color:#77736e;font-size:13px;padding:18px 0 8px">拖动看看原图与处理结果 ↔</div>', unsafe_allow_html=True)
        _comparison(CASES[1], height=610)
        st.markdown('<div class="home-root home-result-note">原图 / 处理后 · 本系统离线相似分 <b>35.78／100</b><br>离线相似分不是平台判定。</div>', unsafe_allow_html=True)

    # 2. Efficiency and measurement.
    _section_start("02", "效率与测评", "批量处理，把重复操作压缩成一次提交", "一次选好一批图片，后续处理在同一任务中完成。以下数字来自项目方提供的同批对照数据。")
    st.markdown('''<div class="home-root home-section alt"><div class="home-stat-grid"><div class="home-stat"><span>满批量 · 本次测试</span><strong>20 张约 11 分钟</strong><small>本次平均 33 秒／张</small></div><div class="home-stat"><span>同批对照</span><strong>处理效率约提升 264%</strong><small>同一组 20 张，人工约 40 分钟，工具约 11 分钟</small></div></div><p class="home-footnote">据项目方提供的同批对照数据，同一组 20 张图片，人工处理约 40 分钟，工具处理约 11 分钟。按单位时间处理张数计算，效率约提升 264%［(40 ÷ 11 − 1) × 100%］。实际耗时随图片和运行环境变化。</p><div class="home-measure"><h3>处理效果，拿原图和结果图来比</h3><p>自建两图测试系统统一图片方向和尺寸，结合 SSIM、PSNR、MSE、MAD 四项指标，计算 0–100 的综合相似分。展示对应原图、结果图和四项指标，让画面变化有据可查。</p></div><p class="home-footnote">测试结果来源于指定图片离线测试，模拟内容平台对内容的审核机制，基于像素比较图片，不代表小红书或其他平台的官方判定、审核或推荐结果。</p></div>''', unsafe_allow_html=True)

    # 3. All seven stages are visible without expansion controls.
    st.markdown('<div class="home-root home-section"><div class="home-kicker">03 / 处理流程</div><h2>上传一次，七步完成图片处理</h2><p class="home-lead">从画面结构到最终导出，七个步骤在同一次任务里完成，减少中间图片反复传递。</p><div class="home-stage-grid">' + ''.join(f'<article class="home-stage"><span class="home-stage-num">{n} / {escape(label)}</span><h3>{escape(title)}</h3><p>{escape(body)}</p><small>{escape(tech)}</small></article>' for n,label,title,body,tech in STAGES) + '</div><p class="home-sources">技术与素材来源：<a href="https://pillow.readthedocs.io/en/stable/" target="_blank" rel="noopener">Pillow</a> · <a href="https://rapidai.github.io/RapidOCRDocs/" target="_blank" rel="noopener">RapidOCR</a> · <a href="https://commons.wikimedia.org/wiki/Commons:API" target="_blank" rel="noopener">Wikimedia Commons</a> · <a href="https://www.pexels.com/license/" target="_blank" rel="noopener">Pexels 照片</a></p></div>', unsafe_allow_html=True)

    # 4. Each published score stays beside its own pair and raw metrics.
    st.markdown('<div id="home-cases" class="home-root home-section"><div class="home-kicker">04 / 三组效果案例</div><h2>别只看“处理完成”，看看处理前后</h2><p class="home-lead">拖动分割线检查主体、文字与细节。每组分数只对应旁边这一组原图和处理结果。</p></div>', unsafe_allow_html=True)
    for case in CASES:
        with st.container(key=f'home_case_{case["id"]}'):
            st.markdown(f'<div class="home-root home-case-head"><h3>{case["id"]} / {escape(case["name"])}</h3><span>{escape(case["kind"])}</span></div>', unsafe_allow_html=True)
            _comparison(case, height=580)
            st.markdown(f'<div class="home-root home-score"><strong>{case["score"]} / 100</strong><span>本系统离线相似分</span><span>本系统判定：不重复</span></div><div class="home-root home-four"><div><small>SSIM</small><b>{case["ssim"]}</b></div><div><small>PSNR</small><b>{case["psnr"]}</b></div><div><small>MSE</small><b>{case["mse"]}</b></div><div><small>MAD</small><b>{case["mad"]}</b></div></div><p class="home-root home-case-copy">{escape(case["kind"])}</p>', unsafe_allow_html=True)

    # 5. The final CTA leads to the existing processing page.
    st.markdown('<div class="home-root home-footer"><div class="home-kicker">05 / 开始使用</div><h2>把图片交给工具，把时间留给内容。</h2><p>选好商品图，剩下的批量处理交给它。</p></div>', unsafe_allow_html=True)
    with st.container(key="home_action_footer"):
        st.page_link(use_page, label="开始使用 ↗")
