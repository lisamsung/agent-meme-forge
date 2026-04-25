#!/usr/bin/env python3

import argparse
import csv
import json
import math
import re
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont, ImageSequence


WECHAT_SPEC = {
    "main": {"size": (240, 240), "max_bytes": 500_000, "target_bytes": 480_000, "format": "GIF"},
    "thumb": {"size": (120, 120), "max_bytes": 50_000, "format": "PNG"},
    "icon": {"size": (50, 50), "max_bytes": 30_000, "format": "PNG"},
    "cover": {"size": (240, 240), "max_bytes": 80_000, "format": "PNG"},
    "banner": {"size": (750, 400), "max_bytes": 80_000, "format": "PNG"},
}

GENERATED_DIRS = [
    Path("named-gifs"),
    Path("wechat-submit") / "main",
    Path("wechat-submit") / "thumbs",
]

GENERATED_FILES = [
    Path("manifest.json"),
    Path("manifest.csv"),
    Path("wechat-submit") / "cover.png",
    Path("wechat-submit") / "icon.png",
    Path("wechat-submit") / "banner.png",
]

FONT_CANDIDATES = [
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
]

STYLE_PROMPTS = {
    "clean-sticker": "clean digital sticker art, crisp dark outline, large readable head, simple color blocks, expressive face, transparent-friendly plain background",
    "pixel-art": "chunky pixel-art sticker, limited palette, hard square edges, readable silhouette, large shapes that survive 240x240 export",
    "chibi": "chibi sticker character with oversized head, compact body, strong facial acting, cute but still sarcastic and sendable",
    "retro-msn": "nostalgic early-internet messenger sticker, glossy avatar charm, simple playful colors, compact readable pose",
    "office-cartoon": "modern workplace cartoon sticker, vector-like shapes, clean props such as laptop papers coffee or meeting notes",
    "hand-drawn": "loose hand-drawn marker sticker, expressive imperfect linework, bold contour, energetic but uncluttered",
}

PERSONA_PROMPT_CUES = {
    "科研打工人": "papers, literature review, lab mishaps, group meeting pressure, supervisor messages, charts, revision anxiety",
    "研究僧": "papers, literature review, group meetings, supervisor messages, thesis pressure, significance anxiety",
    "码农": "bugs, terminal windows, server panic, deploy pressure, requirements changing, logs, compile rituals",
    "都市丽人": "commute, coffee, elegant collapse, meeting smile, office desk, lipstick or mirror props, after-work revival",
    "打工仔": "boss messages, overtime, office desk, tiny salary survival, task papers, workplace fake calm",
    "学生": "early class, homework, exams, library, roll call, GPA panic, cafeteria and vacation countdown",
    "早八特困生": "alarm clock, sleepy classroom, coffee boot sequence, roll-call alert, notes drifting, bell revival",
    "甲方幸存者": "revision loops, abstract feedback, low budget, final-version chaos, delivery pressure, polite survival smile",
    "会议受害者": "mute button, camera anxiety, endless agenda, meeting notes, post-meeting mini meeting, fake understanding",
    "ddl祭司": "deadline meteor, late-night desk lamp, progress bar ritual, save icon, upload moment, last-minute miracle",
}

HARD_IMAGE_RULES = (
    "no text, no words, no Chinese characters, no Latin letters, no captions, "
    "no labels, no watermark, no official logo, no brand mark, no UI, no speech bubbles"
)

SHEET_LAYOUTS = {
    "1x4": (1, 4),
    "2x2": (2, 2),
    "2x3": (2, 3),
    "3x3": (3, 3),
    "4x4": (4, 4),
}

DEFAULT_ANIMATION_LAYOUT = "1x4"


@dataclass(frozen=True)
class MemeEntry:
    name: str
    text: str
    keyword: str
    scene: str
    motion: str = "soft bounce loop"


COMMON_ENTRIES = [
    MemeEntry("收到离线", "收到\n但灵魂已离线", "收到", "收到消息但暂时没有处理能力", "eyes blink and tiny nod"),
    MemeEntry("加载中", "别催\n我在加载", "稍等", "被催进度时的缓冲回应", "loading wobble"),
    MemeEntry("先装懂", "我先\n装懂一下", "懂了", "没完全听懂但先稳住场面", "confused nod"),
    MemeEntry("合理吗", "这合理吗", "疑问", "遇到离谱安排或荒谬逻辑", "slow head tilt"),
    MemeEntry("在写了", "我在写了\n真的", "赶工", "被问交付时的保命回复", "frantic typing bounce"),
    MemeEntry("已读乱回", "已读\n但乱回", "已读", "脑子断线但必须回复", "blank stare blink"),
    MemeEntry("别问了", "别问\n问就是快了", "快了", "无法解释进度时", "sweat drop bounce"),
    MemeEntry("问题不大", "问题不大\n只是很大", "崩溃", "表面镇定实则爆炸", "tiny shake"),
    MemeEntry("我退一下", "我先\n精神退场", "退场", "想从聊天或会议里消失", "fade down bounce"),
    MemeEntry("笑不出来", "笑不出来\n但礼貌", "尴尬", "社交假笑场景", "forced smile twitch"),
    MemeEntry("稳住", "稳住\n先别崩", "稳住", "互相安慰先顶住", "deep breath loop"),
    MemeEntry("离谱", "有点\n离谱了", "离谱", "表达震惊和不认可", "pop-eyed recoil"),
]

PERSONA_ENTRIES = {
    "科研打工人": [
        MemeEntry("文献山", "文献又\n长出来了", "文献", "文献越看越多", "paper pile bounce"),
        MemeEntry("组会渡劫", "组会\n渡劫中", "组会", "组会汇报前后", "laser pointer tremble"),
        MemeEntry("显著吗", "显著吗\n不显著", "显著性", "统计结果不理想", "chart droop"),
        MemeEntry("实验翻车", "实验又\n有想法了", "实验", "实验失败后的自嘲", "beaker fizz"),
        MemeEntry("论文返修", "返修意见\n比正文长", "返修", "论文返修压力", "scroll unroll"),
        MemeEntry("导师召唤", "导师正在\n召唤", "导师", "收到导师消息", "summon glow"),
        MemeEntry("数据沉默", "数据选择\n沉默", "数据", "结果没有趋势", "flatline chart"),
        MemeEntry("毕业玄学", "毕业\n靠玄学推进", "毕业", "毕业进度焦虑", "ritual candle wobble"),
    ],
    "研究僧": [
        MemeEntry("文献山", "文献又\n长出来了", "文献", "文献越看越多", "paper pile bounce"),
        MemeEntry("组会渡劫", "组会\n渡劫中", "组会", "组会汇报前后", "laser pointer tremble"),
        MemeEntry("显著吗", "显著吗\n不显著", "显著性", "统计结果不理想", "chart droop"),
        MemeEntry("实验翻车", "实验又\n有想法了", "实验", "实验失败后的自嘲", "beaker fizz"),
        MemeEntry("论文返修", "返修意见\n比正文长", "返修", "论文返修压力", "scroll unroll"),
        MemeEntry("导师召唤", "导师正在\n召唤", "导师", "收到导师消息", "summon glow"),
        MemeEntry("开题别问", "开题\n先别问", "开题", "开题压力", "document hide"),
        MemeEntry("毕业玄学", "毕业\n靠玄学推进", "毕业", "毕业进度焦虑", "ritual candle wobble"),
    ],
    "码农": [
        MemeEntry("BUG又来", "BUG\n又来上班", "bug", "bug 复现或回归", "bug jump scare"),
        MemeEntry("能跑别动", "能跑\n先别动", "能跑", "代码暂时能用时", "freeze pose"),
        MemeEntry("生产别碰", "别动\n生产环境", "生产", "上线和运维风险", "red button guard"),
        MemeEntry("需求变更", "需求变更\n我变异", "需求", "需求突然变化", "mutation wobble"),
        MemeEntry("编译祈福", "编译通过\n全靠祈福", "编译", "等待构建通过", "terminal sparkle"),
        MemeEntry("日志沉默", "日志说\n它不知道", "日志", "日志没有有用信息", "scroll shrug"),
        MemeEntry("线上没事", "线上没事\n我有事", "上线", "上线后的压力", "server pulse"),
        MemeEntry("重启试试", "要不\n重启试试", "重启", "经典排障回复", "power icon bounce"),
    ],
    "都市丽人": [
        MemeEntry("精致崩溃", "精致\n但崩溃", "崩溃", "体面地崩溃", "lipstick wobble"),
        MemeEntry("咖啡续命", "咖啡\n正在续命", "咖啡", "靠咖啡撑住", "coffee steam loop"),
        MemeEntry("通勤掉血", "通勤\n掉血中", "通勤", "上下班路上", "metro sway"),
        MemeEntry("假笑营业", "假笑\n营业中", "假笑", "社交和会议场景", "smile twitch"),
        MemeEntry("下班变身", "下班\n开始做人", "下班", "下班恢复生命", "sparkle transform"),
        MemeEntry("会议腮红", "听懂了\n才怪", "会议", "会议假装理解", "cheek twitch"),
        MemeEntry("工位结界", "别进\n我的结界", "工位", "想保护工位安静", "shield pop"),
        MemeEntry("妆没白化", "今天也算\n没白化妆", "精致", "自我鼓励", "mirror flash"),
    ],
    "打工仔": [
        MemeEntry("老板饶命", "老板\n我尽量", "老板", "接到任务", "tiny bow"),
        MemeEntry("薪水冷静", "看在工资\n我冷静", "工资", "忍住不爆发", "wallet squeeze"),
        MemeEntry("工位扎根", "我在工位\n长出来了", "工位", "久坐加班", "root grow"),
        MemeEntry("加班开花", "加班加到\n开花", "加班", "加班自嘲", "flower pop"),
        MemeEntry("需求砸脸", "需求\n砸脸上了", "需求", "任务突然降临", "paper hit"),
        MemeEntry("领导英明", "领导英明\n我先截图", "领导", "职场求生回复", "screenshot flash"),
        MemeEntry("别画饼", "饼太大\n咽不下", "画饼", "听到虚假激励", "pie wobble"),
        MemeEntry("下班幻觉", "刚才好像\n下班了", "下班", "以为能走又被叫住", "door vanish"),
    ],
    "学生": [
        MemeEntry("早八索命", "早八\n正在索命", "早八", "早课困倦", "alarm shake"),
        MemeEntry("作业复活", "作业\n又复活了", "作业", "作业没完", "notebook bounce"),
        MemeEntry("考试玄学", "考试\n靠玄学", "考试", "考前祈祷", "pencil ritual"),
        MemeEntry("已在图书馆", "人在图书馆\n心在外卖", "图书馆", "学习状态飘走", "book blink"),
        MemeEntry("老师别点", "老师别点\n我害怕", "点名", "课堂点名", "hide under desk"),
        MemeEntry("绩点救命", "绩点\n救一下", "绩点", "成绩焦虑", "score tremble"),
        MemeEntry("ddl飞来", "ddl\n飞过来了", "ddl", "截止日期逼近", "deadline swoop"),
        MemeEntry("放假倒计时", "放假\n启动倒计时", "放假", "期待假期", "calendar flip"),
    ],
    "早八特困生": [
        MemeEntry("早八索命", "早八\n正在索命", "早八", "早课困倦", "alarm shake"),
        MemeEntry("灵魂迟到", "人到了\n魂没到", "迟到", "到场但没醒", "ghost drift"),
        MemeEntry("咖啡开机", "咖啡一口\n系统开机", "咖啡", "喝咖啡醒脑", "boot light"),
        MemeEntry("课表太满", "课表满到\n溢出", "课表", "课程太多", "calendar overflow"),
        MemeEntry("点名警报", "点名警报\n一级戒备", "点名", "老师点名", "siren blink"),
        MemeEntry("睡意攻击", "睡意\n精准打击", "困", "上课想睡", "head bob"),
        MemeEntry("笔记漂移", "笔记写了\n但没懂", "笔记", "机械记笔记", "pen drift"),
        MemeEntry("下课复活", "下课铃\n复活术", "下课", "下课瞬间精神", "revive flash"),
    ],
    "甲方幸存者": [
        MemeEntry("再改一版", "再改一版\n我懂", "改稿", "甲方继续改", "smile crack"),
        MemeEntry("五彩斑斓黑", "要不\n再黑一点", "审美", "抽象需求", "color wheel spin"),
        MemeEntry("马上就要", "马上要\n但刚想到", "需求", "临时加需求", "paper storm"),
        MemeEntry("预算冷静", "预算没有\n想法很多", "预算", "预算低要求高", "coin shrink"),
        MemeEntry("最终版", "最终版\n第七版", "最终版", "反复改版", "file stack"),
        MemeEntry("懂你意思", "懂你意思\n但不懂", "沟通", "需求模糊", "question bubble pop"),
        MemeEntry("今晚能出吗", "今晚能出吗\n我先没睡", "交付", "急交付", "moon typing"),
        MemeEntry("幸存者", "我又\n活过一轮", "幸存", "改稿后幸存", "tiny victory"),
    ],
    "会议受害者": [
        MemeEntry("会议续杯", "会议\n又续杯了", "会议", "会议延长", "cup refill"),
        MemeEntry("静音保命", "我先\n静音保命", "静音", "会议不想发言", "mute icon pulse"),
        MemeEntry("镜头别开", "镜头别开\n人设会塌", "镜头", "视频会议", "camera dodge"),
        MemeEntry("听懂掌声", "听懂了\n鼓掌", "懂了", "没懂但配合", "clap blink"),
        MemeEntry("议程失踪", "议程\n去哪了", "议程", "会议跑题", "map spin"),
        MemeEntry("纪要压身", "纪要\n压住我了", "纪要", "会后整理", "document squash"),
        MemeEntry("还有问题吗", "没有问题\n只有灵魂", "问题", "会议结束前", "ghost wave"),
        MemeEntry("会后再会", "会后还有\n小会", "小会", "会后继续聊", "mini meeting pop"),
    ],
    "ddl祭司": [
        MemeEntry("DDL降临", "DDL\n降临了", "ddl", "截止日期逼近", "meteor deadline"),
        MemeEntry("献祭睡眠", "献祭睡眠\n换进度", "熬夜", "赶 deadline", "moon ritual"),
        MemeEntry("保存救命", "先保存\n再做人", "保存", "防止文件丢失", "save icon flash"),
        MemeEntry("进度召唤", "进度条\n动一下", "进度", "等待导出/训练/上传", "bar inch"),
        MemeEntry("最后亿点", "还差\n最后亿点", "快了", "剩余工作很多", "tiny mountain"),
        MemeEntry("截止前夜", "今晚\n不属于我", "通宵", "截止前夜", "desk lamp flicker"),
        MemeEntry("交了再说", "先交\n再忏悔", "提交", "先提交保命", "upload sparkle"),
        MemeEntry("神迹发生", "居然\n赶上了", "赶上", "极限完成", "halo pop"),
    ],
}

FILLER_ENTRIES = [
    MemeEntry("可以可以", "可以\n非常可以", "可以", "表示认可", "thumb bounce"),
    MemeEntry("不愧是我", "不愧是我", "自信", "小小得意", "sparkle pose"),
    MemeEntry("撤回重说", "撤回\n我重说", "撤回", "说错话补救", "rewind shake"),
    MemeEntry("你说得对", "你说得对\n但我先睡", "睡觉", "敷衍结束话题", "sleep bubble"),
    MemeEntry("马上来", "马上来\n在路上", "马上", "迟到或拖延", "dash trail"),
    MemeEntry("先吃饭", "先吃饭\n天塌不了", "吃饭", "暂停处理事情", "rice bowl steam"),
    MemeEntry("收到开演", "收到\n开始表演", "开工", "准备开始", "stage bow"),
    MemeEntry("今日闭麦", "今日\n闭麦", "沉默", "不想说话", "zip mouth"),
]


def validate_pack_size(pack_size: int, mode: str) -> int:
    if mode == "wechat" and pack_size not in {16, 24}:
        raise ValueError("WeChat sticker albums must contain 16 or 24 GIFs; use self_use mode for 18.")
    if pack_size <= 0:
        raise ValueError("pack_size must be positive.")
    return pack_size


def style_prompt(style: str) -> str:
    return STYLE_PROMPTS.get(style, STYLE_PROMPTS["clean-sticker"])


def persona_prompt(persona: str) -> str:
    return PERSONA_PROMPT_CUES.get(persona, PERSONA_PROMPT_CUES["科研打工人"])


def parse_sheet_layout(layout: str) -> tuple[int, int]:
    if layout not in SHEET_LAYOUTS:
        raise ValueError(f"Unsupported sheet layout '{layout}'. Use one of: {', '.join(sorted(SHEET_LAYOUTS))}.")
    return SHEET_LAYOUTS[layout]


def animation_frames_for_entry(entry: MemeEntry, frame_count: int = 4) -> list[str]:
    motion = entry.motion.lower()
    name = entry.name
    if any(token in motion for token in ["paper pile", "scroll", "document", "literature"]):
        frames = [
            f"{name}: character notices one small paper stack, worried eyes",
            f"{name}: paper stack grows quickly around the character",
            f"{name}: character is half buried, eyes wide and panicked",
            f"{name}: character pops back up exhausted, loopable return pose",
        ]
    elif any(token in motion for token in ["typing", "terminal", "compile", "keyboard"]):
        frames = [
            f"{name}: character freezes at the keyboard before starting",
            f"{name}: frantic typing begins, hands slightly blurred",
            f"{name}: peak panic typing with sweat and screen glow",
            f"{name}: tiny exhausted pause, still loopable back to frame 1",
        ]
    elif any(token in motion for token in ["shake", "tremble", "wobble", "panic"]):
        frames = [
            f"{name}: character holds a tense neutral pose",
            f"{name}: character shakes slightly to the left",
            f"{name}: character shakes harder to the right with sweat",
            f"{name}: character snaps back to tense center, loopable",
        ]
    elif any(token in motion for token in ["nod", "understand", "blink"]):
        frames = [
            f"{name}: character stares blankly, eyes open",
            f"{name}: character blinks slowly",
            f"{name}: character gives a tiny uncertain nod",
            f"{name}: character returns to blank stare, loopable",
        ]
    elif any(token in motion for token in ["recoil", "jump", "hit", "swoop"]):
        frames = [
            f"{name}: character sees the problem approaching",
            f"{name}: character recoils backward with wide eyes",
            f"{name}: peak exaggerated impact pose",
            f"{name}: character settles back while still shocked",
        ]
    elif any(token in motion for token in ["droop", "flatline", "data", "chart"]):
        frames = [
            f"{name}: character holds a chart hopefully",
            f"{name}: chart line starts falling",
            f"{name}: chart droops or flatlines, character deflates",
            f"{name}: character stares at the result in silence",
        ]
    elif any(token in motion for token in ["summon", "glow", "sparkle", "ritual"]):
        frames = [
            f"{name}: small glow appears near the character",
            f"{name}: glow expands and character notices",
            f"{name}: peak summon or ritual panic pose",
            f"{name}: glow fades while character remains stressed",
        ]
    elif any(token in motion for token in ["fade", "sleep", "ghost"]):
        frames = [
            f"{name}: character sits normally but tired",
            f"{name}: character starts sinking or fading",
            f"{name}: character is mostly mentally gone",
            f"{name}: character returns faintly for a loopable beat",
        ]
    else:
        frames = [
            f"{name}: readable starting expression",
            f"{name}: action starts, body language changes clearly",
            f"{name}: peak exaggerated reaction pose",
            f"{name}: settle pose that loops back cleanly",
        ]
    if frame_count <= len(frames):
        return frames[:frame_count]
    return frames + [frames[-1]] * (frame_count - len(frames))


def sheet_prompt_rules(layout: str) -> str:
    rows, cols = parse_sheet_layout(layout)
    cells = rows * cols
    return (
        f"Motion sheet rules: exactly {cells} equal cells in a {layout} grid "
        f"({rows} row{'s' if rows != 1 else ''}, {cols} column{'s' if cols != 1 else ''}), reading left-to-right and top-to-bottom. "
        "No borders, no separator lines, no panel frames, no numbers. "
        "Same character identity, same outfit cues, same color anchors, same bounding box, and same pixel scale in every cell. "
        "The entire subject and any prop or effect must fit fully inside each cell with clear margin; nothing may cross a cell edge. "
        "Use a 100% solid flat #FF00FF magenta background for clean local chroma-key removal. "
        "No gradients in the background."
    )


def build_character_card(subject: str, style: str, reference_image: str | None = None) -> str:
    subject = subject.strip()
    if not subject and not reference_image:
        raise ValueError("subject is required when no reference image is provided.")
    identity_source = (
        f"uploaded reference image ({reference_image}) plus concept note: {subject or 'preserve the uploaded character'}"
        if reference_image
        else f"text_concept: {subject}"
    )
    source_rule = (
        "Preserve the uploaded character's silhouette, hair or head shape, outfit cues, posture, vibe, and signature details."
        if reference_image
        else "Create an original character from the text concept; do not copy an official mascot, official logo, brand mark, or exact copyrighted character."
    )
    return (
        f"Identity source: {identity_source}. "
        f"{source_rule} "
        f"Style target: {style} ({style_prompt(style)}). "
        "Keep the same head shape, color anchors, body proportions, line weight, and facial feature logic across all stickers. "
        "The character must feel like the same sendable chat sticker persona in every image."
    )


def image_prompt_for_entry(
    entry: MemeEntry,
    index: int,
    subject: str,
    persona: str,
    style: str,
    character_card: str,
    tone: str,
    animation_layout: str = DEFAULT_ANIMATION_LAYOUT,
) -> dict:
    caption = entry.text.replace("\n", " / ")
    rows, cols = parse_sheet_layout(animation_layout)
    frame_plan = animation_frames_for_entry(entry, rows * cols)
    frame_lines = "\n".join(f"Frame {frame_index}: {description}" for frame_index, description in enumerate(frame_plan, start=1))
    prompt = (
        "Create one raw no-text motion sheet for a Chinese WeChat animated meme GIF sticker pack.\n"
        f"Character card: {character_card}\n"
        f"Subject reminder: {subject.strip() or 'uploaded reference character'}.\n"
        f"Visual style: {style_prompt(style)}.\n"
        f"Persona context: {persona}; useful visual cues: {persona_prompt(persona)}.\n"
        f"Meme item {index:02d}: {entry.name}. Chat send scenario: {entry.scene}. "
        f"The final Chinese caption will be added later by a local processor as \"{caption}\"; do not draw any text.\n"
        f"Acting direction: exaggerated readable reaction, {entry.motion}; make the emotion understandable before the caption is added.\n"
        f"{sheet_prompt_rules(animation_layout)}\n"
        f"Frame-by-frame acting plan:\n{frame_lines}\n"
        f"Tone: {tone}; funny, slightly unhinged, but safe for public WeChat review.\n"
        "Composition: one character only, centered, full character or large bust visible, oversized readable face, crisp silhouette, "
        "simple transparent-friendly background, no clutter, no tiny joke-critical props, high contrast, designed to read at 240x240.\n"
        f"Hard negative rules: {HARD_IMAGE_RULES}."
    )
    return {
        "index": index,
        "name": entry.name,
        "caption": entry.text,
        "scene": entry.scene,
        "motion": entry.motion,
        "animation_layout": animation_layout,
        "frames": frame_plan,
        "raw_image_filename": f"{index:02d}-{slug_filename(entry.name)}-{animation_layout}.png",
        "prompt": prompt,
    }


def plan_pack(
    subject: str,
    persona: str = "科研打工人",
    style: str = "clean-sticker",
    pack_size: int = 24,
    mode: str = "wechat",
    tone: str = "职场发疯但安全",
    reference_image: str | None = None,
    pack_name: str = "Agent Meme Pack",
    animation_layout: str = DEFAULT_ANIMATION_LAYOUT,
) -> dict:
    validate_pack_size(pack_size, mode)
    parse_sheet_layout(animation_layout)
    entries = default_entries(persona, pack_size)
    character_card = build_character_card(subject, style, reference_image)
    prompts = [
        image_prompt_for_entry(entry, index, subject, persona, style, character_card, tone, animation_layout)
        for index, entry in enumerate(entries, start=1)
    ]
    return {
        "pack_name": pack_name,
        "subject": subject.strip(),
        "input_mode": "reference_image" if reference_image else "text_concept",
        "reference_image": reference_image or "",
        "persona": persona,
        "style": style,
        "pack_size": pack_size,
        "mode": mode,
        "tone": tone,
        "character_card": character_card,
        "animation": {
            "source_layout": animation_layout,
            "frames_per_sticker": parse_sheet_layout(animation_layout)[0] * parse_sheet_layout(animation_layout)[1],
            "rules": sheet_prompt_rules(animation_layout),
        },
        "items": [asdict(entry) for entry in entries],
        "image_prompts": prompts,
        "agent_instructions": [
            "Call built-in image_gen once per image_prompt to generate one no-text motion sheet per sticker, or generate a small first-pass sample from the first 3 prompts before committing to all 24.",
            "Save raw generated no-text images using raw_image_filename under a source directory such as output/raw-frames/<pack-slug>/.",
            "Reject and regenerate any raw sheet that contains text, speech bubbles, official logos, brand marks, wrong grid count, a tiny face, edge-crossing props, or a character that drifts from the character card.",
            f"After raw sheets are accepted, run meme_pack.py build-pack with --source-layout {animation_layout} plus the same persona, style, pack_size, mode, and pack_name.",
        ],
        "processor_command": (
            "python skills/generate-meme-gif-pack/scripts/meme_pack.py build-pack "
            "--source-dir output/raw-frames/<pack-slug> "
            "--output-dir output/<pack-slug> "
            f"--persona {persona} --style {style} --pack-size {pack_size} --mode {mode} "
            f"--pack-name {pack_name} --source-layout {animation_layout}"
        ),
    }


def default_entries(persona: str, pack_size: int = 24) -> list[MemeEntry]:
    validate_pack_size(pack_size, "wechat" if pack_size in {16, 24} else "self_use")
    persona_entries = PERSONA_ENTRIES.get(persona, PERSONA_ENTRIES["科研打工人"])
    ordered = [*COMMON_ENTRIES, *persona_entries, *FILLER_ENTRIES]
    unique: list[MemeEntry] = []
    seen: set[str] = set()
    for entry in ordered:
        if entry.name in seen:
            continue
        seen.add(entry.name)
        unique.append(entry)
    if len(unique) < pack_size:
        raise ValueError(f"Not enough meme entries for {persona}: need {pack_size}, have {len(unique)}.")
    return unique[:pack_size]


def find_default_font() -> str:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    return ""


def _font(font_path: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if font_path:
        try:
            return ImageFont.truetype(font_path, size=size, index=0)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def _text_size(text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), text, font=font, stroke_width=2)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _wrap_text(text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    normalized = text.replace("\\n", "\n")
    lines: list[str] = []
    for block in normalized.splitlines() or [normalized]:
        current = ""
        for char in block:
            trial = current + char
            if current and _text_size(trial, font)[0] > max_width:
                lines.append(current)
                current = char
            else:
                current = trial
        if current:
            lines.append(current)
    return lines or [""]


def _truncate_line_to_width(text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    ellipsis = "…"
    if _text_size(text, font)[0] <= max_width:
        return text
    if _text_size(ellipsis, font)[0] > max_width:
        return ""
    kept = ""
    for char in text:
        trial = kept + char + ellipsis
        if _text_size(trial, font)[0] > max_width:
            break
        kept += char
    return kept + ellipsis


def _truncate_lines_to_height(lines: list[str], font: ImageFont.ImageFont, max_width: int, max_height: int) -> list[str]:
    line_height = max(_text_size(line, font)[1] for line in lines) + 6
    max_lines = max(1, max_height // line_height)
    if len(lines) <= max_lines and line_height * len(lines) <= max_height:
        return lines
    trimmed = lines[:max_lines]
    overflow = "".join(lines[max_lines - 1 :])
    trimmed[-1] = _truncate_line_to_width(overflow, font, max_width)
    return trimmed


def fit_text_lines(
    text: str,
    font_path: str,
    max_width: int,
    max_height: int,
    max_font_size: int = 34,
    min_font_size: int = 16,
) -> tuple[list[str], ImageFont.ImageFont]:
    for size in range(max_font_size, min_font_size - 1, -1):
        font = _font(font_path, size)
        lines = _wrap_text(text, font, max_width)
        line_height = max(_text_size(line, font)[1] for line in lines) + 6
        if line_height * len(lines) <= max_height and all(_text_size(line, font)[0] <= max_width for line in lines):
            return lines, font
    font = _font(font_path, min_font_size)
    lines = _wrap_text(text, font, max_width)
    return _truncate_lines_to_height(lines, font, max_width, max_height), font


def slug_filename(name: str) -> str:
    cleaned = re.sub(r'[\\\\/:*?"<>|\\s]+', "", name).strip(".")
    return cleaned or "meme"


def ensure_unique_name(name: str, used: set[str]) -> str:
    base = slug_filename(name)
    candidate = base
    index = 2
    while candidate in used:
        candidate = f"{base}-{index}"
        index += 1
    used.add(candidate)
    return candidate


def load_image(path: Path) -> Image.Image:
    image = Image.open(path)
    if getattr(image, "is_animated", False):
        frame = next(ImageSequence.Iterator(image))
        return frame.convert("RGBA")
    return image.convert("RGBA")


def infer_sheet_layout(path: Path, image: Image.Image, source_layout: str = "auto") -> str:
    if source_layout == "single":
        return "single"
    if source_layout != "auto":
        parse_sheet_layout(source_layout)
        return source_layout
    lowered = path.stem.lower()
    for layout in sorted(SHEET_LAYOUTS, key=len, reverse=True):
        if re.search(rf"(^|[-_]){re.escape(layout)}($|[-_])", lowered):
            return layout
    ratio = image.width / image.height if image.height else 1
    if ratio >= 3.3:
        return "1x4"
    if 1.35 <= ratio <= 1.75:
        return "2x3"
    return "single"


def split_sheet_frames(image: Image.Image, layout: str) -> list[Image.Image]:
    rows, cols = parse_sheet_layout(layout)
    frames: list[Image.Image] = []
    for row in range(rows):
        for col in range(cols):
            left = image.width * col // cols
            upper = image.height * row // rows
            right = image.width * (col + 1) // cols
            lower = image.height * (row + 1) // rows
            frames.append(image.crop((left, upper, right, lower)).convert("RGBA"))
    return frames


def remove_chroma_background(image: Image.Image, color: tuple[int, int, int] = (255, 0, 255), tolerance: int = 18) -> Image.Image:
    rgba = image.convert("RGBA")
    pixels = []
    source_pixels = rgba.get_flattened_data() if hasattr(rgba, "get_flattened_data") else rgba.getdata()
    target_red, target_green, target_blue = color
    for red, green, blue, alpha in source_pixels:
        exact_match = (
            abs(red - target_red) <= tolerance
            and abs(green - target_green) <= tolerance
            and abs(blue - target_blue) <= tolerance
        )
        generated_magenta = red >= 210 and blue >= 190 and green <= 90 and abs(red - blue) <= 90
        if alpha and (exact_match or generated_magenta):
            pixels.append((red, green, blue, 0))
        else:
            pixels.append((red, green, blue, alpha))
    rgba.putdata(pixels)
    return rgba


def clean_generated_frame_background(image: Image.Image) -> Image.Image:
    return remove_light_background(remove_chroma_background(image))


def load_source_frames(path: Path, source_layout: str = "auto") -> tuple[list[Image.Image], str, str]:
    image = Image.open(path)
    if getattr(image, "is_animated", False):
        frames = [clean_generated_frame_background(frame.convert("RGBA")) for frame in ImageSequence.Iterator(image)]
        return frames or [load_image(path)], "animated_gif", "gif"
    rgba = image.convert("RGBA")
    layout = infer_sheet_layout(path, rgba, source_layout)
    if layout == "single":
        return [clean_generated_frame_background(rgba)], "single", "single"
    return [clean_generated_frame_background(frame) for frame in split_sheet_frames(rgba, layout)], "sheet", layout


def contain(image: Image.Image, size: tuple[int, int], margin: int = 18) -> Image.Image:
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    image = image.copy()
    image.thumbnail((size[0] - margin * 2, size[1] - margin * 2), Image.Resampling.LANCZOS)
    x = (size[0] - image.width) // 2
    y = max(4, size[1] - margin - image.height)
    canvas.alpha_composite(image, (x, y))
    return canvas


def draw_caption(frame: Image.Image, text: str, font_path: str) -> Image.Image:
    frame = frame.copy()
    draw = ImageDraw.Draw(frame)
    lines, font = fit_text_lines(text, font_path, max_width=214, max_height=76)
    line_boxes = [_text_size(line, font) for line in lines]
    line_height = max(height for _, height in line_boxes) + 6
    total_height = line_height * len(lines)
    y = 240 - total_height - 8
    for line, (width, height) in zip(lines, line_boxes):
        x = (240 - width) // 2
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(35, 35, 35, 255))
        y += line_height
    return frame


def animated_frames(base: Image.Image, text: str, font_path: str, frame_count: int = 5) -> list[Image.Image]:
    frames: list[Image.Image] = []
    for index in range(frame_count):
        phase = math.sin(index / frame_count * math.tau)
        scale = 1.0 + phase * 0.025
        shift_y = int(phase * -4)
        subject = base.copy()
        new_size = (max(1, int(subject.width * scale)), max(1, int(subject.height * scale)))
        subject = subject.resize(new_size, Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (240, 240), (0, 0, 0, 0))
        canvas.alpha_composite(subject, ((240 - subject.width) // 2, (240 - subject.height) // 2 + shift_y))
        frames.append(draw_caption(canvas, text, font_path))
    return frames


def caption_source_frames(raw_frames: list[Image.Image], text: str, font_path: str) -> list[Image.Image]:
    frames: list[Image.Image] = []
    for raw in raw_frames:
        frames.append(draw_caption(contain(raw, WECHAT_SPEC["main"]["size"], margin=22), text, font_path))
    return frames


def save_gif_under_limit(frames: list[Image.Image], path: Path, max_bytes: int = 500_000) -> int:
    attempts = [
        {"frames": frames, "duration": 110, "colors": 128},
        {"frames": frames[:4], "duration": 130, "colors": 96},
        {"frames": frames[:3], "duration": 150, "colors": 64},
        {"frames": frames[:2], "duration": 180, "colors": 48},
    ]
    last_size = 0
    for attempt in attempts:
        palette_frames = [
            frame.convert("RGBA").quantize(colors=attempt["colors"], method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
            for frame in attempt["frames"]
        ]
        palette_frames[0].save(
            path,
            save_all=True,
            append_images=palette_frames[1:],
            duration=attempt["duration"],
            loop=0,
            optimize=True,
            disposal=2,
        )
        last_size = path.stat().st_size
        if last_size < max_bytes:
            return last_size
    raise ValueError(f"Could not compress {path.name} below {max_bytes} bytes; last size was {last_size}.")


def save_png_under_limit(image: Image.Image, path: Path, max_bytes: int) -> int:
    image.save(path, optimize=True)
    size = path.stat().st_size
    if size > max_bytes:
        image = image.convert("P", palette=Image.Palette.ADAPTIVE, colors=128)
        image.save(path, optimize=True)
        size = path.stat().st_size
    if size > max_bytes:
        raise ValueError(f"{path.name} is {size} bytes, above {max_bytes}.")
    return size


def source_images(source_dir: Path) -> list[Path]:
    paths = sorted(
        path for path in source_dir.iterdir() if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    )
    if not paths:
        raise ValueError(f"No source images found in {source_dir}.")
    return paths


def remove_light_background(image: Image.Image, threshold: int = 248) -> Image.Image:
    rgba = image.convert("RGBA")
    pixels = []
    source_pixels = rgba.get_flattened_data() if hasattr(rgba, "get_flattened_data") else rgba.getdata()
    for red, green, blue, alpha in source_pixels:
        if alpha and red >= threshold and green >= threshold and blue >= threshold:
            pixels.append((red, green, blue, 0))
        else:
            pixels.append((red, green, blue, alpha))
    rgba.putdata(pixels)
    return rgba


def split_sheet(sheet_path: Path, output_dir: Path, rows: int, cols: int, transparent_light: bool = True) -> list[Path]:
    if rows <= 0 or cols <= 0:
        raise ValueError("rows and cols must be positive.")
    image = Image.open(sheet_path).convert("RGBA")
    output_dir.mkdir(parents=True, exist_ok=True)
    for stale in output_dir.glob("*.png"):
        stale.unlink()

    written: list[Path] = []
    index = 1
    for row in range(rows):
        for col in range(cols):
            left = image.width * col // cols
            upper = image.height * row // rows
            right = image.width * (col + 1) // cols
            lower = image.height * (row + 1) // rows
            cell = image.crop((left, upper, right, lower))
            if transparent_light:
                cell = remove_light_background(cell)
            path = output_dir / f"{index:02d}.png"
            cell.save(path, optimize=True)
            written.append(path)
            index += 1
    return written


def make_thumbnail(source: Image.Image, size: tuple[int, int]) -> Image.Image:
    thumb = contain(source, size, margin=max(4, size[0] // 10))
    return thumb


def make_banner(sources: Iterable[Image.Image], pack_name: str, persona: str) -> Image.Image:
    banner = Image.new("RGB", WECHAT_SPEC["banner"]["size"], (255, 232, 92))
    draw = ImageDraw.Draw(banner)
    colors = [(55, 85, 255), (255, 101, 80), (36, 178, 125), (35, 35, 35)]
    for idx, color in enumerate(colors):
        draw.rounded_rectangle((36 + idx * 166, 40 + (idx % 2) * 55, 186 + idx * 166, 245 + (idx % 2) * 55), 28, fill=color)
    for idx, source in enumerate(list(sources)[:5]):
        sticker = contain(source, (150, 150), margin=12).convert("RGBA")
        x = 54 + idx * 135
        y = 118 + int(math.sin(idx) * 22)
        banner.paste(Image.alpha_composite(Image.new("RGBA", sticker.size, (0, 0, 0, 0)), sticker).convert("RGB"), (x, y), sticker)
    # Banner intentionally avoids text to match WeChat guidance.
    return banner


def relative_to_output(path: Path, output_dir: Path) -> str:
    return str(path.relative_to(output_dir)).replace("\\", "/")


def clean_generated_outputs(output_dir: Path) -> None:
    for relative_dir in GENERATED_DIRS:
        shutil.rmtree(output_dir / relative_dir, ignore_errors=True)
    for relative_file in GENERATED_FILES:
        path = output_dir / relative_file
        if path.exists():
            path.unlink()


def build_pack(
    source_dir: Path,
    output_dir: Path,
    entries: list[MemeEntry],
    mode: str = "wechat",
    pack_name: str = "Agent Meme Pack",
    style: str = "clean-sticker",
    persona: str = "科研打工人",
    author: str = "Agent Meme Forge",
    source_layout: str = "auto",
) -> dict:
    pack_size = validate_pack_size(len(entries), mode)
    if source_dir.resolve() == output_dir.resolve():
        raise ValueError("source-dir and output-dir must be different.")
    clean_generated_outputs(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    named_dir = output_dir / "named-gifs"
    main_dir = output_dir / "wechat-submit" / "main"
    thumbs_dir = output_dir / "wechat-submit" / "thumbs"
    for directory in (named_dir, main_dir, thumbs_dir):
        directory.mkdir(parents=True, exist_ok=True)

    image_paths = source_images(source_dir)
    font_path = find_default_font()
    used_names: set[str] = set()
    manifest_items: list[dict] = []
    cached_sources: list[Image.Image] = []

    for index, entry in enumerate(entries, start=1):
        image_path = image_paths[(index - 1) % len(image_paths)]
        raw_frames, animation_source, detected_layout = load_source_frames(image_path, source_layout)
        raw = raw_frames[0]
        cached_sources.append(raw)
        if len(raw_frames) > 1:
            frames = caption_source_frames(raw_frames, entry.text, font_path)
        else:
            base = contain(raw, WECHAT_SPEC["main"]["size"], margin=22)
            frames = animated_frames(base, entry.text, font_path)
            animation_source = "single_bounce"

        named_slug = ensure_unique_name(entry.name, used_names)
        named_gif = named_dir / f"{named_slug}.gif"
        numbered_gif = main_dir / f"{index:02d}.gif"
        gif_size = save_gif_under_limit(frames, numbered_gif, WECHAT_SPEC["main"]["max_bytes"])
        shutil.copyfile(numbered_gif, named_gif)

        thumb = make_thumbnail(raw, WECHAT_SPEC["thumb"]["size"])
        thumb_path = thumbs_dir / f"{index:02d}.png"
        thumb_size = save_png_under_limit(thumb, thumb_path, WECHAT_SPEC["thumb"]["max_bytes"])

        manifest_items.append(
            {
                "index": index,
                "name": entry.name,
                "text": entry.text,
                "keyword": entry.keyword,
                "scene": entry.scene,
                "motion": entry.motion,
                "source": str(image_path),
                "animation_source": animation_source,
                "source_layout": detected_layout,
                "source_frame_count": len(raw_frames),
                "wechat_gif": relative_to_output(numbered_gif, output_dir),
                "named_gif": relative_to_output(named_gif, output_dir),
                "thumbnail": relative_to_output(thumb_path, output_dir),
                "gif_bytes": gif_size,
                "thumb_bytes": thumb_size,
            }
        )

    cover = make_thumbnail(cached_sources[0], WECHAT_SPEC["cover"]["size"])
    cover_path = output_dir / "wechat-submit" / "cover.png"
    cover_size = save_png_under_limit(cover, cover_path, WECHAT_SPEC["cover"]["max_bytes"])

    icon = make_thumbnail(cached_sources[0], WECHAT_SPEC["icon"]["size"])
    icon_path = output_dir / "wechat-submit" / "icon.png"
    icon_size = save_png_under_limit(icon, icon_path, WECHAT_SPEC["icon"]["max_bytes"])

    banner = make_banner(cached_sources, pack_name, persona)
    banner_path = output_dir / "wechat-submit" / "banner.png"
    banner_size = save_png_under_limit(banner, banner_path, WECHAT_SPEC["banner"]["max_bytes"])

    manifest = {
        "pack_name": pack_name,
        "pack_size": pack_size,
        "mode": mode,
        "style": style,
        "persona": persona,
        "author": author,
        "wechat": {key: {"size": list(value["size"]), "max_bytes": value["max_bytes"], "format": value["format"]} for key, value in WECHAT_SPEC.items()},
        "assets": {
            "cover": {"path": relative_to_output(cover_path, output_dir), "bytes": cover_size},
            "icon": {"path": relative_to_output(icon_path, output_dir), "bytes": icon_size},
            "banner": {"path": relative_to_output(banner_path, output_dir), "bytes": banner_size},
        },
        "items": manifest_items,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    with (output_dir / "manifest.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "index",
                "name",
                "keyword",
                "text",
                "scene",
                "animation_source",
                "source_layout",
                "source_frame_count",
                "wechat_gif",
                "named_gif",
                "thumbnail",
                "gif_bytes",
                "thumb_bytes",
            ],
        )
        writer.writeheader()
        for item in manifest_items:
            writer.writerow({field: item[field] for field in writer.fieldnames})
    return manifest


def write_default_entries(path: Path, persona: str, pack_size: int) -> None:
    entries = [asdict(entry) for entry in default_entries(persona, pack_size)]
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def write_plan(path: Path, plan: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")


def load_entries(path: Path) -> list[MemeEntry]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [MemeEntry(**item) for item in data]


def cmd_list_options() -> None:
    print(
        json.dumps(
            {
                "personas": sorted(PERSONA_ENTRIES),
                "styles": sorted(STYLE_PROMPTS),
                "input_modes": ["reference_image", "text_concept"],
                "animation_layouts": sorted(SHEET_LAYOUTS),
                "source_layouts": ["auto", "single", *sorted(SHEET_LAYOUTS)],
                "wechat_pack_sizes": [16, 24],
                "self_use_pack_sizes": [18],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build WeChat-ready animated meme GIF packs.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-options", help="Print supported personas and pack sizes.")

    entries_parser = sub.add_parser("write-default-entries", help="Write a default meme entry manifest.")
    entries_parser.add_argument("--persona", default="科研打工人")
    entries_parser.add_argument("--pack-size", type=int, default=24)
    entries_parser.add_argument("--output", required=True, type=Path)

    plan_parser = sub.add_parser("plan-pack", help="Write meme entries plus image_gen prompts for a reference image or text concept.")
    plan_parser.add_argument("--subject", required=True, help="Reference concept, character note, or text-only mascot description.")
    plan_parser.add_argument("--reference-image", default="", help="Optional path or label for the uploaded reference image.")
    plan_parser.add_argument("--persona", default="科研打工人")
    plan_parser.add_argument("--style", default="clean-sticker")
    plan_parser.add_argument("--pack-size", type=int, default=24)
    plan_parser.add_argument("--mode", default="wechat", choices=["wechat", "self_use"])
    plan_parser.add_argument("--tone", default="职场发疯但安全")
    plan_parser.add_argument("--pack-name", default="Agent Meme Pack")
    plan_parser.add_argument("--animation-layout", default=DEFAULT_ANIMATION_LAYOUT, choices=sorted(SHEET_LAYOUTS))
    plan_parser.add_argument("--output", required=True, type=Path)

    split_parser = sub.add_parser("split-sheet", help="Split an image_gen contact sheet into numbered source PNGs.")
    split_parser.add_argument("--input", required=True, type=Path)
    split_parser.add_argument("--output-dir", required=True, type=Path)
    split_parser.add_argument("--rows", required=True, type=int)
    split_parser.add_argument("--cols", required=True, type=int)
    split_parser.add_argument("--keep-light-bg", action="store_true", help="Do not turn near-white sheet backgrounds transparent.")

    build_parser = sub.add_parser("build-pack", help="Build GIFs, thumbnails, WeChat assets, and manifests.")
    build_parser.add_argument("--source-dir", required=True, type=Path)
    build_parser.add_argument("--output-dir", required=True, type=Path)
    build_parser.add_argument("--entries", type=Path)
    build_parser.add_argument("--mode", default="wechat", choices=["wechat", "self_use"])
    build_parser.add_argument("--pack-name", default="Agent Meme Pack")
    build_parser.add_argument("--style", default="clean-sticker")
    build_parser.add_argument("--persona", default="科研打工人")
    build_parser.add_argument("--author", default="Agent Meme Forge")
    build_parser.add_argument("--pack-size", type=int, default=24)
    build_parser.add_argument(
        "--source-layout",
        default="auto",
        help="How to read source images: auto, single, or an explicit sheet layout such as 1x4, 2x2, 2x3.",
    )

    args = parser.parse_args(argv)
    if args.command == "list-options":
        cmd_list_options()
        return 0
    if args.command == "write-default-entries":
        write_default_entries(args.output, args.persona, args.pack_size)
        return 0
    if args.command == "plan-pack":
        try:
            plan = plan_pack(
                subject=args.subject,
                persona=args.persona,
                style=args.style,
                pack_size=args.pack_size,
                mode=args.mode,
                tone=args.tone,
                reference_image=args.reference_image or None,
                pack_name=args.pack_name,
                animation_layout=args.animation_layout,
            )
            write_plan(args.output, plan)
            return 0
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    if args.command == "split-sheet":
        try:
            files = split_sheet(args.input, args.output_dir, args.rows, args.cols, transparent_light=not args.keep_light_bg)
            print(json.dumps({"count": len(files), "files": [str(path) for path in files]}, ensure_ascii=False, indent=2))
            return 0
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    if args.command == "build-pack":
        try:
            entries = load_entries(args.entries) if args.entries else default_entries(args.persona, args.pack_size)
            build_pack(
                args.source_dir,
                args.output_dir,
                entries,
                args.mode,
                args.pack_name,
                args.style,
                args.persona,
                args.author,
                args.source_layout,
            )
            return 0
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
