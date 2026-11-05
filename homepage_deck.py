"""Five full-screen homepage panels, with the approved sketch as panel one."""

from __future__ import annotations

import re
from html import escape
from pathlib import Path

import streamlit as st

from homepage import ASSETS, CASES, STAGES, _image_data


SKETCH = Path(__file__).parent / "docs" / "HOMEPAGE_HERO_SKETCH.html"


def _compare(case: dict[str, str]) -> str:
    name = escape(case["name"])
    return (
        f'<div class="compare" aria-label="{name}原图与处理后对比">'
        f'<img src="{_image_data(case["result"])}" alt="{name}处理后">'
        f'<img class="after" src="{_image_data(case["original"])}" alt="{name}原图">'
        '<div class="divider"><div class="handle">↔</div></div>'
        '<span class="image-label left">原图</span><span class="image-label right">处理后</span>'
        f'<input type="range" min="0" max="100" value="50" aria-label="拖动查看{name}处理前后对比">'
        '</div>'
    )


def _case(case: dict[str, str]) -> str:
    metrics = ''.join(
        f'<div><small>{label}</small><b>{escape(case[key])}</b></div>'
        for label, key in (("SSIM", "ssim"), ("PSNR", "psnr"), ("MSE", "mse"), ("MAD", "mad"))
    )
    return (
        f'<article class="case" tabindex="0" aria-label="{escape(case["name"])}详情">'
        f'<div class="case-teaser"><img src="{_image_data(case["result"])}" alt="{escape(case["name"])}处理后">'
        f'<div><small>{case["id"]} / {escape(case["kind"])}</small><h3>{escape(case["name"])}</h3>'
        f'<strong>{case["score"]} <small>/ 100</small></strong><p>本系统离线相似分 · 不重复</p></div></div>'
        f'<div class="case-detail">{_compare(case)}<div class="case-data"><h3>{escape(case["name"])}</h3>'
        f'<p>{escape(case["kind"])} · 本系统判定：不重复</p><strong>{case["score"]} / 100</strong>'
        f'<div class="metric-grid">{metrics}</div></div></div>'
        '</article>'
    )


EXTRA_CSS = r'''
html,body{width:100%;height:100%;overflow:hidden}body{background:#fff}
.deck{position:relative;width:100%;height:100dvh;overflow:hidden}
.slide{position:absolute;inset:0;display:none;overflow:hidden;background:#fff}
.slide.active{display:block;animation:appear .22s ease-out}@keyframes appear{from{opacity:.4}to{opacity:1}}
.scroll{height:100%;overflow:hidden;overscroll-behavior:contain}
.page{max-width:1440px;margin:auto;min-height:100%;padding:clamp(15px,3vh,30px) clamp(24px,5vw,76px);display:flex;flex-direction:column;justify-content:center}
.slide:not(:first-child) .page{justify-content:flex-start;padding-top:0}
.slide .hero{min-height:0;height:100%;padding:45px 0;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:clamp(24px,4vw,65px)}
.slide .hero h1{font-size:clamp(50px,5.5vw,86px);margin:18px 0 14px}
.slide .hero .lead{font-size:clamp(18px,1.5vw,24px);margin-bottom:20px}.slide .hero .metric{min-height:86px;padding:10px 15px}.slide .hero .metric strong,.slide .hero .metric.efficiency strong{font-size:clamp(21px,2vw,31px)}
.slide .hero .actions{margin-top:19px}.slide .hero .footnote{margin-top:13px}
.slide .hero .compare{height:clamp(250px,50vh,530px);min-height:0}.slide .hero .compare img{object-fit:cover}.slide .hero .visual{padding-top:8px}
.page-control{position:absolute;z-index:30;right:18px;bottom:12px;display:flex;gap:10px;align-items:center;background:#fffdf7ef;border:1px solid #e5dfd4;border-radius:99px;padding:6px 9px;box-shadow:0 8px 25px #0001}
.page-control button{width:30px;height:30px;border:0;border-radius:50%;background:#f5eee7;color:#a04423;font-size:19px;cursor:pointer}.page-control button:disabled{opacity:.25;cursor:default}.page-control span{min-width:48px;text-align:center;font-size:12px;font-weight:800;color:#736d64}
.kicker{display:inline-flex;align-items:center;gap:10px;color:#a04423;font-size:clamp(15px,1.15vw,19px);font-weight:900;letter-spacing:.13em}.kicker::before{content:"";width:27px;height:2px;background:var(--orange)}
.slide .hero .eyebrow{font-size:clamp(15px,1.15vw,19px)}
.slide h2{font-size:clamp(34px,4.2vw,60px);line-height:1.18;letter-spacing:-.05em;margin:10px 0 10px}.intro{color:#66685c;font-size:clamp(17px,1.35vw,21px);line-height:1.5;margin:0 0 17px}
.stats{display:grid;grid-template-columns:1fr 1fr;gap:15px;margin:12px 0}.stat{border:1px solid #e4ded3;border-radius:20px;padding:20px;background:#faf8f2}.stat.orange{background:var(--orange);color:#fff;border-color:var(--orange)}.stat small{display:block;font-size:13px;font-weight:800}.stat strong{display:block;font-size:clamp(28px,3.3vw,47px);letter-spacing:-.05em;margin:7px 0}.stat span{font-size:14px}
.measure{border-left:4px solid var(--orange);padding:18px 24px;background:#faf8f2;border-radius:0 15px 15px 0;margin:18px 0}.measure h3{font-size:clamp(23px,2vw,31px);margin:0 0 9px}.measure p{color:#66685c;line-height:1.6;margin:0;font-size:clamp(15px,1.2vw,19px)}.note{color:#88877b;font-size:12px;line-height:1.6;margin:8px 0}
.notes{margin-top:auto;padding-top:24px}.notes .note{margin:5px 0}
.efficiency-band{margin:18px 0 10px;padding:13px 20px;border:1px solid #eaded0;border-radius:16px;background:#fffaf3}.efficiency-band .figures{display:flex;align-items:baseline;flex-wrap:wrap;gap:8px 18px;color:var(--orange);font-size:clamp(21px,2.3vw,34px);font-weight:900;letter-spacing:-.045em}.efficiency-band .divider-text{color:#c9b9a8;font-weight:400}.efficiency-band p{margin:5px 0 0;color:#736d64;font-size:clamp(12px,1vw,15px);line-height:1.45}
.effect-copy{font-size:clamp(17px,1.3vw,21px);line-height:1.55;color:#46463f;margin:4px 0 10px}.effect-copy strong{color:var(--orange);font-weight:900}.metric-explainer{width:100%;border-collapse:separate;border-spacing:0 5px;font-size:clamp(14px,1.05vw,17px)}.metric-explainer th,.metric-explainer td{padding:8px 16px;text-align:left;background:#faf8f2}.metric-explainer th{width:120px;color:#a04423;font-weight:900;border-radius:9px 0 0 9px}.metric-explainer td{color:#5f6059;border-radius:0 9px 9px 0}.metric-explainer thead th,.metric-explainer thead td{background:none;color:#8a8177;font-size:12px;padding-top:0;padding-bottom:1px}.p2-notes{margin-top:10px;padding-top:0}.p2-notes .note{font-size:11px;line-height:1.45;margin:4px 0}
.stages{display:grid;gap:clamp(8px,1.3vh,16px);margin:14px 0}.stage{display:grid;grid-template-columns:42px 112px minmax(0,1fr) 250px;align-items:center;gap:15px;border:1px solid #e8e3d9;background:#faf8f2;border-radius:13px;padding:8px 17px;min-height:60px}.stage .no{color:var(--orange);font-weight:900;font-size:21px}.stage .name{font-weight:800;font-size:23px}.stage b{font-size:19px}.stage p{color:#77736e;font-size:19px;line-height:1.35;margin:4px 0 0}.stage small{color:#ad6947;font-size:19px;text-align:right}.sources{font-size:12px;color:#88877b}.sources a{color:#a04423}
@media(min-width:1001px){.slide[aria-label="七阶段"] .page{padding-right:20px}.slide[aria-label="七阶段"] .stage{grid-template-columns:42px 112px minmax(0,1fr) 320px}}
.cases{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.case{border:1px solid #e6dfd5;border-radius:18px;background:#faf8f2;overflow:hidden;min-width:0;cursor:pointer}.case:hover,.case:focus-within,.case.open{border-color:#f5ad80;box-shadow:0 13px 30px #382b1d20}.case-teaser img{width:100%;height:clamp(250px,52vh,580px);object-fit:cover;object-position:center 25%;display:block}.case-teaser>div{padding:13px}.case-teaser small{display:block;font-size:clamp(17px,1.5vw,23px);font-weight:850;color:#a04423}.case-teaser h3{font-size:15px;margin:5px 0}.case-teaser strong{font-size:27px;color:var(--orange)}.case-teaser strong small{display:inline;font-size:13px;color:#77736e}.case-teaser p{font-size:11px;color:#77736e;margin:4px 0 0}
.case-detail{display:none;position:fixed;z-index:20;width:min(760px,75vw);max-height:82vh;left:50%;top:50%;transform:translate(-50%,-50%);background:#fff;border:1px solid #e7d9cc;border-radius:24px;box-shadow:0 22px 80px #0005;padding:16px;grid-template-columns:minmax(260px,380px) minmax(220px,1fr);gap:18px;align-items:center}.case.open .case-detail{display:grid}.case-detail .compare{height:min(68vh,560px);min-height:0}.case-detail .compare img{object-fit:contain;background:#eee9e2}.case-data p{color:#66685c;font-size:14px}.case-data>strong{color:var(--orange);font-size:36px}.metric-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:15px}.metric-grid div{padding:10px;border-radius:10px;background:#faf8f2}.metric-grid small{display:block;color:#77736e;font-size:11px}.metric-grid b{font-size:13px}
.last{background:radial-gradient(circle at 85% 17%,#ffe4cc 0,#ffe4cc 11%,transparent 11.1%),radial-gradient(circle at 14% 84%,#fff1e4 0,#fff1e4 16%,transparent 16.1%),#fff;color:#24251f;text-align:center}.last .page{align-items:center;justify-content:center!important;padding-top:0!important;transform:translateY(-4vh)}.last .kicker{font-size:15px}.last h2{font-size:clamp(50px,5.6vw,84px);max-width:1040px}.last p{color:#68675d;font-size:clamp(19px,1.6vw,25px)}.last .button{background:var(--orange);margin-top:32px;box-shadow:0 14px 30px #fd653733}.last::after{content:'✳';position:absolute;right:12%;bottom:10%;color:var(--orange);font-size:clamp(70px,9vw,140px);line-height:1;opacity:.75;pointer-events:none}
@media(max-height:700px) and (min-width:901px){.slide .hero h1{font-size:clamp(42px,4.8vw,68px)}.slide .hero .compare{height:clamp(240px,44vh,440px)}.slide .hero .metric{min-height:76px}.slide .hero .metric strong{font-size:clamp(23px,2.3vw,35px)}.slide .hero .metric.efficiency strong{font-size:clamp(21px,2vw,31px)}.page{padding-top:7px;padding-bottom:7px}.page h2{font-size:39px;margin:8px 0 5px}.last h2{font-size:clamp(49px,5vw,66px)}.page .intro{margin-bottom:7px}.stats .stat{padding:15px}.measure{padding:13px 20px;margin:10px 0}.measure p{font-size:14px;line-height:1.48}.notes{padding-top:12px}.note{font-size:10px}.stage{padding:3px 10px;min-height:37px}.stage p{font-size:11px;margin-top:1px}.stages{gap:6px;margin:6px 0}}
@media(min-width:701px) and (max-width:1000px){.slide .hero{grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:25px}.slide .hero h1{font-size:clamp(40px,5vw,56px)}.slide .hero .metric strong,.slide .hero .metric.efficiency strong{font-size:21px}.slide .hero .metric{padding:10px;min-height:78px}.slide .hero .compare{height:clamp(230px,42vh,410px)}.slide .hero .photo-bottom strong{font-size:12px}.slide .hero .photo-bottom strong b{font-size:20px}.slide .hero .photo-bottom span{font-size:10px}.stage{grid-template-columns:30px 82px minmax(0,1fr)}.stage small{display:none}}
@media(max-width:700px){.slide .shell{overflow:hidden}.slide .hero{grid-template-columns:1fr;height:auto}.slide .hero .visual{max-width:100%;padding:0 6px}.slide .hero .compare{height:200px}.slide .hero .photo-card{max-width:350px}.slide .hero .metrics{grid-template-columns:1fr 1fr}.slide .hero .metric strong,.slide .hero .metric.efficiency strong{font-size:21px}.slide .hero .metric{min-height:90px}.slide .hero h1{font-size:clamp(38px,6vw,58px)}.stage{grid-template-columns:28px 70px minmax(0,1fr);gap:8px}.stage small{display:none}.case-detail{width:90vw;max-height:90vh;grid-template-columns:1fr}.case-detail .compare{height:45vh}}
@media(max-width:580px){.page{padding:12px 18px 46px}.slide .hero{padding:4px 0;gap:10px}.slide .hero h1{font-size:clamp(36px,9vw,48px);margin:8px 0}.slide .hero .lead{font-size:13px;margin:0 0 10px}.slide .hero .metrics{gap:8px}.slide .hero .metric{padding:9px;min-height:69px}.slide .hero .metric small,.slide .hero .metric span{font-size:9px}.slide .hero .metric strong,.slide .hero .metric.efficiency strong{font-size:17px;white-space:normal;margin:3px 0}.slide .hero .actions{margin-top:10px}.slide .hero .button{padding:10px 14px;font-size:12px}.slide .hero .text-link{font-size:12px}.slide .hero .footnote{margin:8px 0;font-size:9px}.slide .hero .photo-card{padding:6px;transform:none}.slide .hero .compare{height:clamp(105px,22vh,170px)}.slide .hero .photo-bottom strong{font-size:11px}.slide .hero .photo-bottom strong b{font-size:17px}.slide .hero .photo-bottom span{font-size:9px}.slide .hero .photo-top{padding:2px 3px 5px}.slide h2{font-size:28px}.intro{font-size:13px;margin-bottom:10px}.stats{gap:7px}.stat{padding:10px}.stat strong{font-size:19px}.stat small,.stat span{font-size:10px}.measure{padding:9px;margin:6px 0}.measure h3{font-size:16px}.measure p{font-size:11px}.note{font-size:9px}.stages{gap:4px}.stage{grid-template-columns:20px 56px minmax(0,1fr);padding:4px 6px;min-height:48px}.stage b{font-size:11px}.stage p{font-size:9px}.stage .name{font-size:10px}.cases{grid-template-columns:1fr;gap:7px}.case-teaser{display:grid;grid-template-columns:95px 1fr}.case-teaser img{height:97px}.case-teaser>div{padding:6px}.case-teaser h3{font-size:16px;margin:2px 0}.case-teaser strong{font-size:19px}.case-teaser p{font-size:9px}.case-detail{inset:4vh 4vw;padding:10px;gap:8px}.case-detail .compare{height:44vh}.case-data h3{font-size:16px}.case-data p{font-size:11px}.case-data>strong{font-size:21px}.metric-grid{margin-top:5px}.metric-grid div{padding:6px}.metric-grid b{font-size:11px}.page-control{right:7px;bottom:7px}}
@media(prefers-reduced-motion:reduce){.slide.active{animation:none}}
'''


SCRIPT = r'''
const slides=[...document.querySelectorAll('.slide')];let page=0,lastGesture=0;
function closeCases(){document.querySelectorAll('.case.open').forEach(x=>x.classList.remove('open'))}
function openCase(card){closeCases();card.classList.add('open')}
function fitPage(){const scroll=slides[page].querySelector('.scroll');if(!scroll)return;const content=scroll.firstElementChild;let low=.1,high=1,best=.1;for(let attempt=0;attempt<9;attempt++){const scale=(low+high)/2;content.style.zoom=String(scale);if(scroll.scrollHeight<=scroll.clientHeight+1&&scroll.scrollWidth<=scroll.clientWidth+1){best=scale;low=scale}else high=scale}content.style.zoom=String(best)}
function show(i){if(i<0||i>=slides.length||i===page)return;slides[page].classList.remove('active');page=i;slides[page].classList.add('active');fitPage();document.querySelector('.count').textContent=String(page+1).padStart(2,'0')+' / 05';document.querySelector('.prev').disabled=page===0;document.querySelector('.next').disabled=page===4;closeCases();lastPointer=null}
function turn(d){let now=Date.now();if(now-lastGesture<900)return;lastGesture=now;show(page+d)}
document.querySelector('.prev').onclick=()=>show(page-1);document.querySelector('.next').onclick=()=>show(page+1);document.querySelector('.prev').disabled=true;
document.querySelectorAll('[data-go]').forEach(a=>a.onclick=e=>{e.preventDefault();show(Number(a.dataset.go))});
document.querySelectorAll('a[data-start-use]').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();window.parent.postMessage({kind:'image-dedupe-use'},'*')}));
document.querySelectorAll('.compare').forEach(box=>{let slider=box.querySelector('input'),after=box.querySelector('.after'),line=box.querySelector('.divider');slider.oninput=()=>{after.style.clipPath=`inset(0 ${100-slider.value}% 0 0)`;line.style.left=slider.value+'%'}});
let lastPointer=null;
document.addEventListener('pointermove',e=>{if(e.pointerType!=='mouse')return;const previous=lastPointer;lastPointer=[e.clientX,e.clientY];if(page!==3||!previous||Math.hypot(e.clientX-previous[0],e.clientY-previous[1])<2)return;const card=e.target.closest('.case');if(card&&!card.classList.contains('open'))openCase(card)});
document.querySelectorAll('.case').forEach(card=>{card.addEventListener('click',e=>{if(e.pointerType==='mouse'||e.target.closest('input'))return;if(card.classList.contains('open'))closeCases();else openCase(card)});card.querySelector('.case-detail').addEventListener('pointerleave',e=>{if(e.pointerType==='mouse')closeCases()});card.addEventListener('pointerleave',e=>{if(e.pointerType==='mouse')closeCases()})});
document.addEventListener('click',e=>{if(!e.target.closest('.case'))closeCases()});
window.addEventListener('wheel',e=>{const d=Math.sign(e.deltaY);if(d){e.preventDefault();turn(d)}},{passive:false});
let touchY=null,touchCompare=false;window.addEventListener('touchstart',e=>{touchY=e.touches[0].clientY;touchCompare=!!e.target.closest('.compare')},{passive:true});window.addEventListener('touchend',e=>{if(touchY===null||touchCompare)return;const delta=touchY-e.changedTouches[0].clientY;touchY=null;if(Math.abs(delta)>45)turn(Math.sign(delta))},{passive:true});
window.addEventListener('keydown',e=>{if(e.target.matches('input[type=range]'))return;if(['ArrowDown','PageDown',' '].includes(e.key)){e.preventDefault();turn(1)}else if(['ArrowUp','PageUp'].includes(e.key)){e.preventDefault();turn(-1)}});
window.addEventListener('resize',()=>requestAnimationFrame(fitPage));window.addEventListener('load',fitPage);requestAnimationFrame(fitPage);
'''


def _document() -> str:
    sketch = SKETCH.read_text(encoding="utf-8")
    sketch_css = re.search(r"<style>(.*?)</style>", sketch, re.S).group(1)
    hero = re.search(r'<main class="hero">(.*?)</main>', sketch, re.S).group(1)
    hero = hero.replace('<img src="../assets/homepage/B.jpg" alt="粉色袖口原图">', '<img src="../assets/homepage/02_B_processed.png" alt="粉色袖口处理结果">')
    hero = hero.replace('<img class="after" src="../assets/homepage/02_B_processed.png" alt="粉色袖口处理结果">', '<img class="after" src="../assets/homepage/B.jpg" alt="粉色袖口原图">')
    hero = hero.replace('../assets/homepage/B.jpg', _image_data('B.jpg'))
    hero = hero.replace('../assets/homepage/02_B_processed.png', _image_data('02_B_processed.png'))
    hero = hero.replace('<span class="image-label left">处理后</span><span class="image-label right">原图</span>', '<span class="image-label left">原图</span><span class="image-label right">处理后</span>')
    hero = hero.replace('href="#demo"', 'href="/use" data-start-use target="_top"')
    hero = hero.replace('href="#compare"', 'href="#cases" data-go="3"')
    stages = ''.join(
        f'<article class="stage"><span class="no">{n}</span><span class="name">{escape(label)}</span><div><b>{escape(title)}</b><p>{escape(body)}</p></div><small>{escape(tech)}</small></article>'
        for n, label, title, body, tech in STAGES
    )
    cases = ''.join(_case(case) for case in CASES)
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>{sketch_css}\n{EXTRA_CSS}</style></head><body><div class="deck">
    <section class="slide active" aria-label="首屏"><div class="scroll"><div class="shell"><main class="hero">{hero}</main></div></div></section>
    <section class="slide" aria-label="效率与测评"><div class="scroll"><div class="page"><div class="kicker">02 / 效率与测评</div><div class="efficiency-band"><div class="figures"><span>20 张约 11 分钟</span><span class="divider-text">｜</span><span>处理效率约提升 264%</span></div><p>据项目方提供的同批 20 张图片对照数据，人工处理约 40 分钟，工具处理约 11 分钟。实际耗时随图片和运行环境变化。</p></div><h2>像素级去重，保留原图效果</h2><p class="effect-copy">保留商品主体、文字和画面质感，肉眼效果一致，处理后的图片可直接用于内容发布。<br><strong>BUT，像素层面大不同！</strong>模拟社媒查重机制，以原图为参照，从 SSIM、PSNR、MSE、MAD 四项指标衡量相似度，处理前后图片综合相似分平均为 32.71／100。</p><table class="metric-explainer"><thead><tr><th>指标</th><td>简明解释</td></tr></thead><tbody><tr><th scope="row">SSIM</th><td>比较画面结构；越高，结构越相似。</td></tr><tr><th scope="row">PSNR</th><td>衡量像素变化带来的图像差异；通常越高，图片越接近。</td></tr><tr><th scope="row">MSE</th><td>统计像素差异的平方平均值；越高，差异越大。</td></tr><tr><th scope="row">MAD</th><td>统计像素差异的平均幅度；越高，差异越大。</td></tr></tbody></table><div class="notes p2-notes"><p class="note">据项目方提供的同批对照数据，同一组 20 张图片，人工处理约 40 分钟，工具处理约 11 分钟。按单位时间处理张数计算，效率约提升 264%［(40 ÷ 11 − 1) × 100%］；实际耗时随图片和运行环境变化。</p><p class="note">指定图片的离线测试模拟内容平台的相似性检查，不代表小红书或其他平台的官方判定、审核或推荐结果。</p><p class="note">选取 89 组商品图片，将每组原图与本工具处理后的结果图进行离线两图测试，综合相似分平均为 32.71／100；分数越低，表示两图差异越大。</p></div></div></div></section>
    <section class="slide" aria-label="七阶段"><div class="scroll"><div class="page"><div class="kicker">03 / 处理流程</div><h2>上传一次，七步完成图片处理</h2><p class="intro">从画面结构到最终导出，七个步骤在同一次任务里完成。</p><div class="stages">{stages}</div><p class="sources">技术与素材来源：<a href="https://pillow.readthedocs.io/en/stable/" target="_blank" rel="noopener">Pillow</a> · <a href="https://rapidai.github.io/RapidOCRDocs/" target="_blank" rel="noopener">RapidOCR</a> · <a href="https://commons.wikimedia.org/wiki/Commons:API" target="_blank" rel="noopener">Wikimedia Commons</a> · <a href="https://www.pexels.com/license/" target="_blank" rel="noopener">Pexels 照片</a></p></div></div></section>
    <section class="slide" id="cases" aria-label="三组效果案例"><div class="scroll"><div class="page"><div class="kicker">04 / 三组效果案例</div><h2>别只看“处理完成”，看看处理前后</h2><p class="intro">悬停或点按案例，放大查看原图、处理后及四项指标。</p><div class="cases">{cases}</div><p class="note">分数为指定配对在本系统中的离线结果，不代表平台官方判定。</p></div></div></section>
    <section class="slide last" aria-label="开始使用"><div class="page"><div class="kicker">05 / 开始使用</div><h2>把图片交给工具 <br>把时间留给内容 </h2><p>选好商品图，剩下的批量处理交给它。</p><a class="button" href="/use" data-start-use target="_top">开始使用 ↗</a></div></section>
    <div class="page-control"><button type="button" class="prev" aria-label="上一页">↑</button><span class="count">01 / 05</span><button type="button" class="next" aria-label="下一页">↓</button></div>
    </div><script>{SCRIPT}</script></body></html>'''


def render_home(_use_page: st.Page) -> None:
    st.markdown('''<style>
    [data-testid="stMain"]:has(.st-key-home_deck){overflow:hidden!important}
    [data-testid="stMainBlockContainer"]:has(.st-key-home_deck){padding-bottom:0!important;padding-top:1.5rem!important}
    [data-testid="stMainBlockContainer"]:has(.st-key-home_deck) [data-testid="stDivider"]{margin:0!important}
    .st-key-home_deck{margin:-3rem -2rem 0!important}
    .st-key-home_deck iframe[data-testid="stIFrame"],.st-key-home_deck [data-testid="stElementContainer"]:has(iframe[data-testid="stIFrame"]){height:calc(100dvh - 143px)!important;max-height:calc(100dvh - 143px)!important;min-height:0!important;width:100%;border:0}
    @media(max-width:700px){.st-key-home_deck{margin:0 -1.2rem!important}}
    </style>''', unsafe_allow_html=True)
    st.html('''<script>
    function fitHomeFrame() {
      const main = document.querySelector('[data-testid="stMain"]');
      const frame = document.querySelector('.st-key-home_deck iframe[data-testid="stIFrame"]');
      if (!main || !frame) return false;
      main.scrollTop = 0;
      const height = Math.max(220, Math.floor(main.getBoundingClientRect().bottom - frame.getBoundingClientRect().top));
      for (const element of [frame, frame.closest('[data-testid="stElementContainer"]'), frame.closest('.st-key-home_deck')]) {
        element?.style.setProperty('height', `${height}px`, 'important');
        element?.style.setProperty('max-height', `${height}px`, 'important');
      }
      return true;
    }
    if (!fitHomeFrame()) {
      const observer = new MutationObserver(() => { if (fitHomeFrame()) observer.disconnect(); });
      observer.observe(document.body, {childList:true, subtree:true});
    }
    window.addEventListener('resize', () => requestAnimationFrame(fitHomeFrame));
    window.addEventListener('message', event => {
      if (event.data?.kind === 'image-dedupe-use') {
         window.location.assign('/use');
      }
    });
    </script>''', unsafe_allow_javascript=True)
    with st.container(key="home_deck"):
        st.iframe(_document(), height=900, alt="图像去重处理器首页，使用滚轮或上下箭头逐屏浏览")
