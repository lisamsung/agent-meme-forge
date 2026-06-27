#!/usr/bin/env python3

import argparse
import csv
import html as html_lib
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageSequence


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
    Path("qc_report.json"),
    Path("preview.html"),
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
    "Vibe Coding": "terminal windows, code editor, AI pair-programming, debugging, tests, refactor pressure, deploy rituals, monitoring dashboards, coffee, late-night shipping",
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
    "1x8": (1, 8),
    "2x2": (2, 2),
    "2x3": (2, 3),
    "2x4": (2, 4),
    "3x3": (3, 3),
    "4x4": (4, 4),
}

DEFAULT_ANIMATION_LAYOUT = "2x4"
QUALITY_MODES = {"preview", "standard", "submission"}
MOTION_PROFILES = {"micro", "standard", "action"}
SOURCE_MODES = {"keyposes", "motion_sheet", "single_bounce"}
DEFAULT_SOURCE_MODE = "keyposes"
IMAGE_PROVIDER_CODEX_BUILTIN = "codex_builtin_image_gen"
IMAGE_PROVIDER_OPENAI_IMAGES_API = "openai_images_api"
IMAGE_PROVIDER_EXTERNAL_FILES = "external_files"
IMAGE_PROVIDER_AI_STUDIO_HERMES = "ai_studio_hermes"
IMAGE_PROVIDERS = {
    IMAGE_PROVIDER_CODEX_BUILTIN,
    IMAGE_PROVIDER_OPENAI_IMAGES_API,
    IMAGE_PROVIDER_EXTERNAL_FILES,
    IMAGE_PROVIDER_AI_STUDIO_HERMES,
}
IMAGE_PROVIDER_ALIASES = {
    "codex": IMAGE_PROVIDER_CODEX_BUILTIN,
    "codex_builtin": IMAGE_PROVIDER_CODEX_BUILTIN,
    "image_gen": IMAGE_PROVIDER_CODEX_BUILTIN,
    "builtin": IMAGE_PROVIDER_CODEX_BUILTIN,
    "openai": IMAGE_PROVIDER_OPENAI_IMAGES_API,
    "openai_api": IMAGE_PROVIDER_OPENAI_IMAGES_API,
    "openai_images": IMAGE_PROVIDER_OPENAI_IMAGES_API,
    "openai_images_api": IMAGE_PROVIDER_OPENAI_IMAGES_API,
    "external": IMAGE_PROVIDER_EXTERNAL_FILES,
    "external_batch": IMAGE_PROVIDER_EXTERNAL_FILES,
    "external_files": IMAGE_PROVIDER_EXTERNAL_FILES,
    "ai_studio": IMAGE_PROVIDER_AI_STUDIO_HERMES,
    "hermes": IMAGE_PROVIDER_AI_STUDIO_HERMES,
    "ai_studio_hermes": IMAGE_PROVIDER_AI_STUDIO_HERMES,
}
DEFAULT_IMAGE_PROVIDER = IMAGE_PROVIDER_CODEX_BUILTIN
DEFAULT_KEYPOSE_LAYOUT = "2x2"
KEYPOSE_LAYOUTS = {"2x2", "1x4"}
MOTION_SHEET_LAYOUTS = {"2x4", "4x4"}
DEFAULT_RENDER_FRAME_COUNT = 16
CAPTION_RESERVED_HEIGHT = 76
MIN_CAPTION_RESERVED_HEIGHT = 42
CAPTION_BOTTOM_PADDING = 12
CAPTION_ALLOWED_SUBJECT_OVERLAP = 4
SUBJECT_CANVAS_SIZE = WECHAT_SPEC["main"]["size"]


QC_LIMITS = {
    "preview": {
        "min_area_ratio": 0.004,
        "center_drift_ratio": 0.60,
        "size_drift_ratio": 0.85,
        "require_multiframe": False,
        "required_layout": None,
        "required_layouts": None,
    },
    "standard": {
        "min_area_ratio": 0.006,
        "center_drift_ratio": 0.40,
        "size_drift_ratio": 0.45,
        "require_multiframe": True,
        "required_layout": None,
        "required_layouts": None,
    },
    "submission": {
        "min_area_ratio": 0.008,
        "center_drift_ratio": 0.30,
        "size_drift_ratio": 0.25,
        "require_multiframe": True,
        "required_layout": None,
        "required_layouts": {"2x4", "4x4"},
    },
}

MOTION_PROFILE_LIMITS = {
    "micro": {"center_drift_ratio": 0.07, "size_drift_ratio": 0.18, "alignment_mode": "stable"},
    "standard": {"center_drift_ratio": None, "size_drift_ratio": None, "alignment_mode": "preserve"},
    "action": {"center_drift_ratio": 0.34, "size_drift_ratio": 0.32, "alignment_mode": "preserve"},
}

CONTINUITY_LIMITS = {
    "micro": {
        "max_rgb_step": 0.36,
        "max_alpha_step": 0.50,
        "max_area_jump": 0.42,
        "max_center_step": 8.0,
        "max_loop_closure": 0.24,
        "min_motion_energy": 0.006,
        "max_caption_zone_alpha": 0.08,
    },
    "standard": {
        "max_rgb_step": 0.45,
        "max_alpha_step": 0.42,
        "max_area_jump": 0.55,
        "max_center_step": 26.0,
        "max_loop_closure": 0.30,
        "min_motion_energy": 0.008,
        "max_caption_zone_alpha": 0.10,
    },
    "action": {
        "max_rgb_step": 0.58,
        "max_alpha_step": 0.55,
        "max_area_jump": 0.78,
        "max_center_step": 34.0,
        "max_loop_closure": 0.36,
        "min_motion_energy": 0.010,
        "max_caption_zone_alpha": 0.12,
    },
}

FACE_QC_LIMITS = {
    "micro": {"max_shape_drift": 0.30, "max_head_center_step": 10.0},
    "standard": {"max_shape_drift": 0.34, "max_head_center_step": 22.0},
    "action": {"max_shape_drift": 0.42, "max_head_center_step": 32.0},
}

PROP_QC_LIMITS = {
    "min_lifetime": 2,
    "max_position_jump": 72.0,
    "max_area_jump": 1.35,
}

TEMPLATE_ACTING_LIMITS = {
    "soul_offline": {"max_center_step": 22.0, "max_head_center_step": 22.0, "max_shape_drift": 0.56},
    "loading_loop": {"max_center_step": 22.0, "max_head_center_step": 22.0, "max_shape_drift": 0.34},
    "pretend_understand": {"max_center_step": 22.0, "max_head_center_step": 22.0, "max_shape_drift": 0.34},
}

MOTION_TEMPLATE_IDS = {
    "soul_offline",
    "loading_loop",
    "pretend_understand",
    "typing_panic",
    "fake_smile",
    "absurd_recoil",
    "steady_breath",
    "paper_overflow",
}


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
    "Vibe Coding": [
        MemeEntry("灵感来了", "灵感\n来了!", "灵感", "突然想到一个可做的小功能或实现路线", "lightbulb pop and claw raise"),
        MemeEntry("构思中", "构思中...", "构思", "开始拆需求和想架构时", "sketch pad and pencil thinking loop"),
        MemeEntry("写代码中", "写代码中...", "写码", "正在进入实现状态", "terminal typing with focused eyes"),
        MemeEntry("专注模式", "专注\n模式", "专注", "需要不被打扰地推进代码", "code screen visor focus pulse"),
        MemeEntry("调试中", "调试中...", "调试", "拿放大镜找问题", "magnifier scan and suspicious squint"),
        MemeEntry("发现Bug", "发现\nBug!", "bug", "发现明显 bug 或复现问题时", "bug alert recoil"),
        MemeEntry("报错了", "报错了...", "报错", "运行或构建直接红了", "error sign slam and angry shake"),
        MemeEntry("谁动了我的代码", "谁动了\n我的代码?", "甩锅", "代码突然变坏需要追责时", "question bubble and side-eye"),
        MemeEntry("让我看看", "让我\n看看...", "检查", "准备接手排查或 review", "lean toward monitor and blink"),
        MemeEntry("不确定", "不确定...", "犹豫", "方案还没完全想稳", "question mark hover"),
        MemeEntry("试试这个", "试试\n这个?", "尝试", "提出一个可试的方案", "small speech bubble and claw point"),
        MemeEntry("搞定", "搞定!", "完成", "修完或做完一个小闭环", "sparkle victory claw"),
        MemeEntry("测试中", "测试中...", "测试", "跑测试等待结果", "testing tube and progress bar loop"),
        MemeEntry("测试通过", "测试\n通过!", "通过", "测试变绿或验收通过", "green check pop"),
        MemeEntry("测试失败", "测试\n失败...", "失败", "测试红了需要返工", "red cross drop"),
        MemeEntry("重构中", "重构中...", "重构", "整理结构但还没结束", "steam puff and code block rearrange"),
        MemeEntry("优化中", "优化中...", "优化", "在提速或减资源消耗", "up arrows and calm nod"),
        MemeEntry("性能起飞", "性能\n起飞!", "性能", "优化后速度明显变快", "rocket launch recoil"),
        MemeEntry("加个TODO", "加个\nTODO", "TODO", "先记账暂缓处理", "todo sign pop"),
        MemeEntry("查文档中", "查文档中...", "文档", "翻 API 或框架文档", "open book page flip"),
        MemeEntry("部署中", "部署中...", "部署", "正在发布或上传", "cloud upload pulse"),
        MemeEntry("上线啦", "上线啦!", "上线", "发布成功可以庆祝", "confetti and proud claw"),
        MemeEntry("监控中", "监控中...", "监控", "上线后盯监控面板", "dashboard heartbeat watch"),
        MemeEntry("今晚又加班", "今晚\n又加班", "加班", "晚上继续赶交付", "night laptop and exhausted blink"),
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


def parse_quality_mode(quality_mode: str) -> str:
    if quality_mode not in QUALITY_MODES:
        raise ValueError(f"Unsupported quality mode '{quality_mode}'. Use one of: {', '.join(sorted(QUALITY_MODES))}.")
    return quality_mode


def parse_motion_profile(motion_profile: str) -> str:
    if motion_profile not in MOTION_PROFILES:
        raise ValueError(
            f"Unsupported motion profile '{motion_profile}'. Use one of: {', '.join(sorted(MOTION_PROFILES))}."
        )
    return motion_profile


def parse_source_mode(source_mode: str) -> str:
    if source_mode not in SOURCE_MODES:
        raise ValueError(f"Unsupported source_mode '{source_mode}'. Use one of: {', '.join(sorted(SOURCE_MODES))}.")
    return source_mode


def parse_image_provider(image_provider: str) -> str:
    normalized = IMAGE_PROVIDER_ALIASES.get(image_provider, image_provider)
    if normalized not in IMAGE_PROVIDERS:
        raise ValueError(
            f"Unsupported image_provider '{image_provider}'. Use one of: {', '.join(sorted(IMAGE_PROVIDERS))}."
        )
    return normalized


def default_imagegen_cli_path() -> Path:
    candidates: list[Path] = []
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        candidates.append(Path(codex_home) / "skills" / ".system" / "imagegen" / "scripts" / "image_gen.py")
    home = Path.home()
    candidates.extend(
        [
            home / ".codex-switcher" / "skills" / ".system" / "imagegen" / "scripts" / "image_gen.py",
            home / ".codex" / "skills" / ".system" / "imagegen" / "scripts" / "image_gen.py",
        ]
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0] if candidates else Path("image_gen.py")


def parse_keypose_layout(layout: str) -> str:
    parse_sheet_layout(layout)
    if layout not in KEYPOSE_LAYOUTS:
        raise ValueError(f"Unsupported keypose layout '{layout}'. Use one of: {', '.join(sorted(KEYPOSE_LAYOUTS))}.")
    return layout


def pixel_data(image: Image.Image):
    return image.get_flattened_data() if hasattr(image, "get_flattened_data") else image.getdata()


def motion_profile_for_motion(motion: str) -> str:
    normalized = motion.lower()
    if any(token in normalized for token in ["blink", "nod", "understand", "blank", "loading"]):
        return "micro"
    if any(
        token in normalized
        for token in [
            "recoil",
            "jump",
            "hit",
            "swoop",
            "shake",
            "tremble",
            "panic",
            "paper",
            "scroll",
            "document",
            "literature",
            "typing",
            "terminal",
            "compile",
            "keyboard",
            "summon",
            "glow",
            "sparkle",
            "ritual",
        ]
    ):
        return "action"
    return "standard"


def alignment_mode_for_profile(motion_profile: str) -> str:
    return str(MOTION_PROFILE_LIMITS[parse_motion_profile(motion_profile)]["alignment_mode"])


def motion_template_for_entry(entry: MemeEntry) -> str:
    text = f"{entry.name} {entry.text} {entry.scene} {entry.motion}".lower()
    if any(token in text for token in ["收到离线", "灵魂", "offline", "ghost", "fade", "sleep"]):
        return "soul_offline"
    if any(token in text for token in ["加载", "loading", "progress", "进度条"]):
        return "loading_loop"
    if any(token in text for token in ["装懂", "懂", "understand", "nod", "blink"]):
        return "pretend_understand"
    if any(token in text for token in ["写", "typing", "keyboard", "terminal", "compile", "编译"]):
        return "typing_panic"
    if any(token in text for token in ["假笑", "礼貌", "笑不出来", "smile"]):
        return "fake_smile"
    if any(token in text for token in ["离谱", "合理", "recoil", "jump", "hit", "swoop"]):
        return "absurd_recoil"
    if any(token in text for token in ["文献", "论文", "paper", "scroll", "document", "literature"]):
        return "paper_overflow"
    return "steady_breath"


def keypose_beats_for_template(template_id: str, entry: MemeEntry) -> list[str]:
    name = entry.name
    beats = {
        "soul_offline": [
            f"{name}: readable start pose, polite bright smile, one hand slightly raised like replying received, eyes open and face large",
            f"{name}: obvious head nod down, eyelids droop hard and shoulders sink, smile freezes into a tired polite mask, same crop and silhouette",
            f"{name}: peak offline gag, head tilted and empty smile, body sagging, leave clean space above the head for a local soul puff effect",
            f"{name}: loop return pose, empty but friendly smile with half-open eyes, hand returns close to the body, same outfit and scale",
        ],
        "loading_loop": [
            f"{name}: character faces a small laptop or invisible task panel just below frame, smiling but clearly starting to buffer, face large",
            f"{name}: visible buffering freeze, eyes droop and shoulders sink, hands hover near the same spot as if waiting for a slow loading bar",
            f"{name}: peak stuck expression with unfocused pupils and awkward frozen smile, leave clean space near the head for local loading dots",
            f"{name}: character pops back to focused start pose with a tiny recoil, same prop area, same body scale, loopable",
        ],
        "pretend_understand": [
            f"{name}: polite start pose, thinking finger near chin or small listening nod, bright smile, eyes open and attentive",
            f"{name}: obvious nod down as if understanding, slow blink, controlled smile, shoulders stay aligned, same hand pose and crop",
            f"{name}: peak confused-confidence gag, eyes drift sideways, eyebrows lifted, mouth tries too hard to stay professional",
            f"{name}: forced confident smile with a compact thumbs-up or hand gesture close to body, loopable back to pose 1",
        ],
        "typing_panic": [
            f"{name}: hands placed on keyboard or laptop, nervous start",
            f"{name}: hands start typing faster, shoulders tense",
            f"{name}: peak tiny panic typing, sweat or speed marks close to subject",
            f"{name}: exhausted reset pose, hands still on keyboard for loop",
        ],
        "fake_smile": [
            f"{name}: neutral polite expression, shoulders square",
            f"{name}: mouth corners lift into a controlled fake smile",
            f"{name}: smile twitches with tiny stress mark, eyes strained",
            f"{name}: returns to polite neutral smile, same crop",
        ],
        "absurd_recoil": [
            f"{name}: normal pose before noticing something strange",
            f"{name}: eyes widen and body leans back slightly",
            f"{name}: peak absurd reaction, eyebrows high, small shock marks close to head",
            f"{name}: settles into stunned loopable pose, same scale",
        ],
        "steady_breath": [
            f"{name}: tense but centered start pose",
            f"{name}: shoulders rise slightly, small inhale",
            f"{name}: shoulders drop, expression calms but still tired",
            f"{name}: returns to centered start pose, loopable",
        ],
        "paper_overflow": [
            f"{name}: sees a small paper stack, worried eyes",
            f"{name}: paper stack grows but stays near the character",
            f"{name}: papers surround the character at peak chaos, no edge crossing",
            f"{name}: character pops back exhausted, papers settle for loop",
        ],
    }
    return beats.get(template_id, beats["steady_breath"])


def local_effects_for_template(template_id: str) -> list[str]:
    return {
        "soul_offline": ["soul_puff"],
        "loading_loop": ["loading_dots"],
        "pretend_understand": ["sweat_drop", "awkward_lines"],
    }.get(template_id, [])


def qc_policy_for_template(template_id: str) -> dict[str, object]:
    return {
        "min_prop_lifetime": PROP_QC_LIMITS["min_lifetime"],
        "max_prop_position_jump": PROP_QC_LIMITS["max_position_jump"],
        "max_prop_area_jump": PROP_QC_LIMITS["max_area_jump"],
        "allow_local_effects": local_effects_for_template(template_id),
        "protect_head_shape": True,
    }


def _base_timeline(frame_count: int) -> list[dict[str, float | int]]:
    pose_sequence = [1, 1, 1, 2, 2, 2, 3, 3, 3, 3, 2, 2, 4, 4, 1, 1]
    dx_sequence = [0, 0, 0, 0, 0, 0, -1, 0, 1, 0, 0, 0, 0, 0, 0, 0]
    dy_sequence = [0, -1, 0, 1, 2, 1, 0, -2, -3, -1, 1, 0, 0, -1, 0, 1]
    scale_sequence = [1.0, 1.01, 1.0, 0.995, 0.985, 0.99, 1.0, 1.015, 1.02, 1.01, 0.995, 1.0, 1.005, 1.0, 1.0, 1.002]
    rotation_sequence = [0, 0, 0, -0.8, -1.0, -0.6, 0, 0.8, 1.0, 0.6, -0.3, 0, 0.3, 0, 0, 0]
    timeline = [
        {
            "pose": pose_sequence[index],
            "dx": dx_sequence[index],
            "dy": dy_sequence[index],
            "scale": scale_sequence[index],
            "rotation": rotation_sequence[index],
            "hold": 1,
        }
        for index in range(len(pose_sequence))
    ]
    if frame_count == len(timeline):
        return timeline
    if frame_count < len(timeline):
        if frame_count <= 1:
            return timeline[:1]
        selected: list[dict[str, float | int]] = []
        for index in range(frame_count):
            source_index = round(index * (len(timeline) - 1) / (frame_count - 1))
            selected.append(dict(timeline[source_index]))
        selected[-1]["pose"] = 1
        selected[-1]["dx"] = 0
        selected[-1]["dy"] = 0
        selected[-1]["scale"] = 1.0
        selected[-1]["rotation"] = 0
        return selected
    expanded = []
    while len(expanded) < frame_count:
        expanded.extend(dict(item) for item in timeline)
    return expanded[:frame_count]


def timeline_for_template(template_id: str, frame_count: int = DEFAULT_RENDER_FRAME_COUNT) -> list[dict[str, float | int]]:
    timeline = _base_timeline(frame_count)
    if template_id == "soul_offline":
        pose = [1, 1, 2, 2, 2, 3, 3, 3, 3, 2, 2, 4, 4, 1, 1, 1]
        dx = [0, 0, 0, 0, 0, -1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0]
        dy = [0, 1, 3, 5, 4, 2, 0, -2, -3, 0, 2, 1, -1, 0, 1, 0]
        scale = [1.0, 0.998, 0.992, 0.985, 0.99, 1.0, 1.012, 1.022, 1.015, 1.0, 0.995, 1.006, 1.012, 1.0, 0.998, 1.0]
        rotation = [0, -0.2, -0.8, -1.2, -0.8, -0.2, 0.5, 1.0, 0.7, 0.1, -0.4, 0.3, 0.6, 0, 0, 0]
        for index, step in enumerate(timeline):
            step["pose"] = pose[index % 16]
            step["dx"] = dx[index % 16]
            step["dy"] = dy[index % 16]
            step["scale"] = scale[index % 16]
            step["rotation"] = rotation[index % 16]
            step["effect"] = "soul_puff" if 5 <= index % 16 <= 11 else ""
    elif template_id == "loading_loop":
        for index, step in enumerate(timeline):
            step["pose"] = [1, 1, 2, 2, 2, 3, 3, 3, 3, 2, 2, 4, 4, 1, 1, 1][index % 16]
            step["dy"] = [0, 1, 3, 4, 3, 1, 0, -2, 0, 2, 3, 1, -1, 0, 1, 0][index % 16]
            step["dx"] = [0, 0, 0, 1, 0, -1, 0, 1, -1, 0, 1, 0, -1, 0, 0, 0][index % 16]
            step["scale"] = [1.0, 1.0, 0.992, 0.988, 0.992, 1.0, 1.006, 1.01, 1.006, 0.996, 0.992, 1.0, 1.012, 1.006, 1.0, 1.0][index % 16]
            step["rotation"] = [0, 0.2, -0.8, -1.0, -0.6, 0.4, 0, 0.8, -0.8, 0.4, -0.4, 0.2, 0.8, 0.2, 0, 0][index % 16]
            step["effect"] = "loading_dots"
    elif template_id == "pretend_understand":
        pose = [1, 1, 2, 2, 2, 3, 3, 3, 3, 4, 4, 3, 2, 1, 1, 1]
        dx = [0, 0, 0, 0, 0, 1, 2, 3, 2, 1, 0, 1, 0, 0, 0, 0]
        dy = [0, 1, 3, 4, 3, 1, 0, -1, 0, 1, 0, 0, 2, 0, 1, 0]
        scale = [1.0, 1.004, 1.0, 0.994, 0.998, 1.0, 1.006, 1.01, 1.006, 1.014, 1.01, 1.004, 1.0, 1.0, 1.002, 1.0]
        rotation = [0, 0.2, -0.8, -1.0, -0.6, 0.4, 0.8, 1.2, 0.8, -0.4, -0.8, 0.3, -0.4, 0, 0, 0]
        for index, step in enumerate(timeline):
            step["pose"] = pose[index % 16]
            step["dx"] = dx[index % 16]
            step["dy"] = dy[index % 16]
            step["scale"] = scale[index % 16]
            step["rotation"] = rotation[index % 16]
            step["effect"] = "sweat_drop" if 5 <= index % 16 <= 10 else ("awkward_lines" if 6 <= index % 16 <= 11 else "")
    elif template_id == "typing_panic":
        for index, step in enumerate(timeline):
            step["dx"] = [-1, 1, -1, 1][index % 4]
            step["dy"] = [0, -1, 0, 1][index % 4]
            step["scale"] = 1.0 + (0.012 if index % 2 else 0.0)
    elif template_id == "absurd_recoil":
        for index, step in enumerate(timeline):
            step["dx"] = [0, 0, -1, -2, -3, -4, -5, -4, -3, -2, -1, 0, 1, 0, 0, 0][index % 16]
            step["rotation"] = [0, 0, -0.5, -1.0, -1.5, -1.8, -2.0, -1.2, -0.8, 0, 0.5, 0.2, 0, 0, 0, 0][index % 16]
    elif template_id == "steady_breath":
        for index, step in enumerate(timeline):
            step["pose"] = [1, 1, 2, 2, 2, 3, 3, 3, 2, 2, 4, 4, 1, 1, 1, 1][index % 16]
            step["scale"] = 1.0 + [0, 0.004, 0.008, 0.012, 0.008, 0.002, -0.004, -0.006, -0.004, 0, 0.004, 0.002, 0, 0, 0, 0][index % 16]
            step["rotation"] = 0
    return timeline


def motion_template_plan_for_entry(entry: MemeEntry, frame_count: int = DEFAULT_RENDER_FRAME_COUNT) -> dict[str, object]:
    template_id = motion_template_for_entry(entry)
    return {
        "motion_template": template_id,
        "keypose_beats": keypose_beats_for_template(template_id, entry),
        "timeline": timeline_for_template(template_id, frame_count),
        "local_effects": local_effects_for_template(template_id),
        "qc_policy": qc_policy_for_template(template_id),
        "allowed_effects": {
            "soul_offline": "tiny soul or thought puff must persist for several adjacent frames, never one-frame flash",
            "loading_loop": "loading marks must stay close to the head or laptop and persist across the loading beat",
            "pretend_understand": "sweat drop or awkward lines must stay near the head for several adjacent frames, never one-frame flash",
            "paper_overflow": "papers may grow over multiple beats but cannot teleport or touch cell edges",
        }.get(template_id, "small close-to-subject effects only; no one-frame props"),
        "continuity_acceptance": (
            "neighboring rendered frames must have stable center, no sudden area jump, no one-frame prop flash, "
            "and the final frame must loop back cleanly to the first frame"
        ),
        "regenerate_hint": (
            f"Regenerate {entry.name} as four stable key poses for template {template_id}: same identity, same crop, same prop set, "
            "pure #FF00FF background, no text, no separator lines, no extra in-between frames."
        ),
    }


def animation_frames_for_entry(entry: MemeEntry, frame_count: int = 4) -> list[str]:
    motion = entry.motion.lower()
    name = entry.name
    if any(token in motion for token in ["paper pile", "scroll", "document", "literature"]):
        frames = [
            f"{name}: character notices one small paper stack, worried eyes",
            f"{name}: character reaches toward the paper stack with hesitation",
            f"{name}: paper stack grows quickly around the character",
            f"{name}: papers start flying around the character",
            f"{name}: character is half buried, eyes wide and panicked",
            f"{name}: paper pile reaches peak chaos around the character",
            f"{name}: character pops back up exhausted, loopable return pose",
            f"{name}: character settles with a tiny defeated sigh, ready to loop",
        ]
    elif any(token in motion for token in ["typing", "terminal", "compile", "keyboard"]):
        frames = [
            f"{name}: character freezes at the keyboard before starting",
            f"{name}: character leans in with nervous focus",
            f"{name}: frantic typing begins, hands slightly blurred",
            f"{name}: typing accelerates, sweat appears",
            f"{name}: peak panic typing with sweat and screen glow",
            f"{name}: character jolts as if a new problem appears",
            f"{name}: tiny exhausted pause, still loopable back to frame 1",
            f"{name}: character resets hands on keyboard for loop",
        ]
    elif any(token in motion for token in ["shake", "tremble", "wobble", "panic"]):
        frames = [
            f"{name}: character holds a tense neutral pose",
            f"{name}: character shakes slightly to the left",
            f"{name}: character snaps back through center",
            f"{name}: character shakes harder to the right with sweat",
            f"{name}: character squeezes eyes shut at peak stress",
            f"{name}: character snaps back to tense center, loopable",
            f"{name}: character breathes once but is still worried",
            f"{name}: character returns to tense neutral pose",
        ]
    elif any(token in motion for token in ["nod", "understand", "blink"]):
        frames = [
            f"{name}: character starts with a polite alive-looking pose, eyes open",
            f"{name}: eyelids droop clearly, shoulders sink slightly, same silhouette and hand pose",
            f"{name}: slow blink closes, mouth freezes into a forced calm smile",
            f"{name}: eyes reopen halfway with pupils drifting aside, same hand pose",
            f"{name}: readable nod down, head moves 8 to 14 pixels, glasses tilt slightly",
            f"{name}: nod rebounds up with eyebrows lifted and empty confidence",
            f"{name}: character returns to blank stare, eyes open wider like the soul rebooted",
            f"{name}: same as frame 1, loopable return pose with stable center",
        ]
    elif any(token in motion for token in ["recoil", "jump", "hit", "swoop"]):
        frames = [
            f"{name}: character sees the problem approaching",
            f"{name}: character begins to lean back",
            f"{name}: character recoils backward with wide eyes",
            f"{name}: character flails at mid recoil",
            f"{name}: peak exaggerated impact pose",
            f"{name}: character rebounds forward slightly",
            f"{name}: character settles back while still shocked",
            f"{name}: character holds a loopable stunned pose",
        ]
    elif any(token in motion for token in ["droop", "flatline", "data", "chart"]):
        frames = [
            f"{name}: character holds a chart hopefully",
            f"{name}: character points at the chart with cautious optimism",
            f"{name}: chart line starts falling",
            f"{name}: character notices the bad trend",
            f"{name}: chart droops or flatlines, character deflates",
            f"{name}: character's shoulders sink lower",
            f"{name}: character stares at the result in silence",
            f"{name}: character returns to holding the sad chart, loopable",
        ]
    elif any(token in motion for token in ["summon", "glow", "sparkle", "ritual"]):
        frames = [
            f"{name}: small glow appears near the character",
            f"{name}: character notices the glow",
            f"{name}: glow expands and character notices",
            f"{name}: glow circles around the character",
            f"{name}: peak summon or ritual panic pose",
            f"{name}: glow starts fading while character stays tense",
            f"{name}: glow fades while character remains stressed",
            f"{name}: character settles into a loopable worried pose",
        ]
    elif any(token in motion for token in ["fade", "sleep", "ghost"]):
        frames = [
            f"{name}: character sits normally but tired",
            f"{name}: character eyelids droop",
            f"{name}: character starts sinking or fading",
            f"{name}: character fades further with sleepy posture",
            f"{name}: character is mostly mentally gone",
            f"{name}: character begins returning faintly",
            f"{name}: character returns faintly for a loopable beat",
            f"{name}: character settles back into tired start pose",
        ]
    else:
        frames = [
            f"{name}: readable starting expression",
            f"{name}: anticipation beat before the action",
            f"{name}: action starts, body language changes clearly",
            f"{name}: action escalates with a clearer silhouette",
            f"{name}: peak exaggerated reaction pose",
            f"{name}: reaction starts settling",
            f"{name}: settle pose that loops back cleanly",
            f"{name}: final loopable return pose",
        ]
    if frame_count <= len(frames):
        return frames[:frame_count]
    return expand_frame_plan(frames, frame_count)


def expand_frame_plan(frames: list[str], frame_count: int) -> list[str]:
    if not frames:
        return []
    expanded: list[str] = []
    subject = frames[0].split(":", 1)[0] if ":" in frames[0] else "character"
    for index, frame in enumerate(frames):
        expanded.append(frame)
        if len(expanded) >= frame_count:
            break
        next_index = (index + 1) % len(frames)
        expanded.append(
            f"{subject}: in-between from beat {index + 1} toward beat {next_index + 1}, "
            "smooth pose transition with matching face, hands, outfit cues, scale, and cell center"
        )
        if len(expanded) >= frame_count:
            break
    while len(expanded) < frame_count:
        expanded.append(
            f"{subject}: in-between loop recovery beat {len(expanded) + 1}, keep the same identity and smooth timing"
        )
    return expanded[:frame_count]


def sheet_prompt_rules(layout: str) -> str:
    rows, cols = parse_sheet_layout(layout)
    cells = rows * cols
    extra_motion_rule = (
        "For 4x4 or other 16-frame sheets, use the extra frames for anticipation, pose change, overshoot, recovery, and loop smoothing; do not make sixteen near-duplicates. "
        if cells >= 16
        else ""
    )
    return (
        f"Motion sheet rules: exactly {cells} equal cells in a {layout} grid "
        f"({rows} row{'s' if rows != 1 else ''}, {cols} column{'s' if cols != 1 else ''}), reading left-to-right and top-to-bottom. "
        "No borders, no separator lines, no panel frames, no numbers. "
        "Same character identity, same outfit cues, same color anchors, same bounding box, and same pixel scale in every cell. "
        "The entire subject and any prop or effect must fit fully inside each cell with clear margin; nothing may cross a cell edge. "
        "Make the frames feel like smooth in-between animation, not eight unrelated drawings: no camera cuts, no sudden pose swaps, no random new props, and keep the head anchor, shoulder line, outfit, and crop nearly fixed unless the frame plan explicitly moves them. "
        f"{extra_motion_rule}"
        "For Codex image_gen runs, prefer a pure solid #FF00FF background unless the tool is confirmed to export real alpha transparency to a local PNG file. "
        "If using a confirmed alpha-capable image interface, transparent PNG background is acceptable; verify it is real alpha, not visible pixels. "
        "If the image tool or API model cannot output true alpha transparency, use a 100% solid flat #FF00FF magenta background for local chroma-key removal. "
        "Never use gradients, shadows, colored washes, textured backgrounds, or fake checkerboard transparency behind the cells."
    )


def keypose_prompt_rules(layout: str, render_frame_count: int) -> str:
    rows, cols = parse_sheet_layout(layout)
    cells = rows * cols
    return (
        f"Keypose sheet rules: exactly {cells} key poses in a {layout} grid "
        f"({rows} row{'s' if rows != 1 else ''}, {cols} column{'s' if cols != 1 else ''}), reading left-to-right and top-to-bottom. "
        f"Do not generate the final {render_frame_count} animation frames. The local processor will render the final {render_frame_count}-frame GIF from these four poses using deterministic holds, anticipation, rebound, and loop closure. "
        "No borders, no separator lines, no panel frames, no numbers. "
        "Same character identity, same outfit cues, same color anchors, same bounding box, same hand/prop continuity, and same pixel scale in every key pose. "
        "Keep the same silhouette and hand pose continuity unless the four-pose acting plan explicitly changes it. "
        "The entire subject and any prop or effect must fit fully inside each cell with clear margin; nothing may cross a cell edge. "
        "Make the four poses semantically different but continuous: start, anticipation or drift, peak gag, loopable return. "
        "Do not make unrelated illustrations, camera cuts, crop changes, random props, teleporting hands, or one-frame-only effects. "
        "For Codex image_gen runs, prefer a pure solid #FF00FF background unless the tool is confirmed to export real alpha transparency to a local PNG file. "
        "If using a confirmed alpha-capable image interface, transparent PNG background is acceptable; verify it is real alpha, not visible pixels. "
        "Never use gradients, shadows, colored washes, textured backgrounds, or fake checkerboard transparency behind the cells."
    )


def visual_gag_for_entry(entry: MemeEntry) -> str:
    motion = entry.motion.lower()
    if any(token in motion for token in ["paper", "scroll", "document", "literature"]):
        return "papers multiply around the character until the reaction reads before the caption appears"
    if any(token in motion for token in ["typing", "terminal", "compile", "keyboard"]):
        return "tiny frantic keyboard or screen glow drives the joke without any visible text"
    if any(token in motion for token in ["shake", "tremble", "wobble", "panic"]):
        return "small stress tremble escalates into a clear peak pose, then loops back"
    if any(token in motion for token in ["droop", "flatline", "data", "chart"]):
        return "a simple chart or prop physically deflates while the character tries to stay calm"
    if any(token in motion for token in ["summon", "glow", "sparkle", "ritual"]):
        return "a tight halo or glow appears close to the character and never crosses the cell edge"
    if any(token in motion for token in ["fade", "sleep", "ghost"]):
        return "the character visibly powers down or mentally exits, then returns to loop"
    return "the face and body language carry the joke clearly at 240x240 before the caption is added"


MEME_QUALITY_BAR = {
    "principle": "没人用的表情包就是垃圾表情包。A sticker nobody wants to send is waste.",
    "pass_criteria": [
        "answers a real chat situation without extra explanation",
        "has a short reusable caption with emotional payoff",
        "uses a visual gag or acting choice that makes the caption funnier",
        "is safe for public WeChat review while still feeling alive",
    ],
    "reject_if": [
        "only cute or decorative",
        "generic mood with no send trigger",
        "private joke that strangers cannot reuse",
        "pretty pose that does not add humor, tension, or reaction value",
    ],
}


def emotional_value_for_entry(entry: MemeEntry) -> str:
    text = f"{entry.name} {entry.text} {entry.scene} {entry.motion}".lower()
    if any(token in text for token in ["收到", "加载", "已读", "懂"]):
        return "low-pressure reply that buys time without sounding cold"
    if any(token in text for token in ["离谱", "合理", "问题", "崩", "翻车", "bug"]):
        return "shared disbelief and comic relief when things go wrong"
    if any(token in text for token in ["写", "ddl", "加班", "交", "进度", "返修"]):
        return "deadline survival humor that says I am trying but suffering"
    if any(token in text for token in ["咖啡", "早八", "睡", "灵魂", "退场"]):
        return "energy-depleted self-mockery that is easy to send repeatedly"
    return "quick emotional shorthand that makes the chat reply more playful"


def sendability_gate_for_entry(entry: MemeEntry) -> dict[str, str]:
    visual_gag = visual_gag_for_entry(entry)
    return {
        "reuse_trigger": entry.scene,
        "emotional_value": emotional_value_for_entry(entry),
        "creative_hook": visual_gag,
        "pass_if": "someone could send this directly in a chat to answer the situation, and the motion makes the caption funnier",
        "reject_if": "only cute or decorative, generic mood, private-context joke, or a pretty pose with no reusable chat purpose",
    }


def qc_acceptance_for_entry(layout: str) -> str:
    rows, cols = parse_sheet_layout(layout)
    return (
        f"Must be exactly {rows * cols} frames in a {layout} sheet; no fake checkerboard; "
        "true alpha or solid #FF00FF only; subject visible in every cell; no edge touch; "
        "same character identity, scale, and center across frames."
    )


def motion_profile_prompt(motion_profile: str) -> str:
    profile = parse_motion_profile(motion_profile)
    if profile == "micro":
        return (
            "Motion amplitude profile: medium-readable micro-motion with expressive details. Keep the crop and subject center anchored; "
            "use clear eyelid, pupil, eyebrow, mouth, glasses, shoulder-sink, and 8 to 14 pixel head-nod changes. "
            "The pose should match the caption and be readable at 240px, but there must be no lateral drift."
        )
    if profile == "action":
        return (
            "Motion amplitude profile: exaggerated sticker acting. Use anticipation, bigger silhouette changes, arms or shoulders, props, squash/stretch, overshoot, and recovery so the pose carries the caption. "
            "Keep the character fully inside the cell, preserve identity and scale, and make neighboring frames continuous instead of jump-cut."
        )
    return (
        "Motion amplitude profile: standard sticker loop. Use readable face, hand, shoulder, or prop changes that match the meme caption while keeping identity, scale, and crop stable. "
        "The four key poses should show a clear acting arc: start, anticipation, peak gag, and loopable recovery; avoid four nearly identical pretty poses."
    )


def regenerate_hint_for_entry(entry: MemeEntry, layout: str) -> str:
    caption = entry.text.replace("\n", " / ")
    return (
        f"Regenerate {entry.name} as a cleaner {layout} no-text motion sheet. "
        f"Keep the caption idea '{caption}' out of the image. Use a larger readable face, fewer props, "
        "more margin inside every cell, identical character scale, and transparent PNG or pure #FF00FF only. "
        "If the result is only cute or decorative, redesign the acting so it answers the chat scene and makes the caption funnier."
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
    source_mode: str = DEFAULT_SOURCE_MODE,
    keypose_layout: str = DEFAULT_KEYPOSE_LAYOUT,
    render_frame_count: int = DEFAULT_RENDER_FRAME_COUNT,
) -> dict:
    caption = entry.text.replace("\n", " / ")
    source_mode = parse_source_mode(source_mode)
    motion_profile = motion_profile_for_motion(entry.motion)
    sendability_gate = sendability_gate_for_entry(entry)
    template_plan = motion_template_plan_for_entry(entry, render_frame_count)
    if source_mode == "keyposes":
        source_layout = parse_keypose_layout(keypose_layout)
        frame_plan = animation_frames_for_entry(entry, render_frame_count)
        keypose_lines = "\n".join(
            f"Key pose {pose_index}: {description}"
            for pose_index, description in enumerate(template_plan["keypose_beats"], start=1)
        )
        prompt = (
            "Create one raw no-text keypose sheet for a Chinese WeChat animated meme GIF sticker pack.\n"
            f"Character card: {character_card}\n"
            f"Subject reminder: {subject.strip() or 'uploaded reference character'}.\n"
            f"Visual style: {style_prompt(style)}.\n"
            f"Persona context: {persona}; useful visual cues: {persona_prompt(persona)}.\n"
            f"Meme item {index:02d}: {entry.name}. Chat send scenario: {entry.scene}. "
            f"The final Chinese caption will be added later by a local processor as \"{caption}\"; do not draw any text.\n"
            "Sendability gate: this must be a sticker people want to send, not just a nice illustration. "
            f"Reuse trigger: {sendability_gate['reuse_trigger']}. Emotional value: {sendability_gate['emotional_value']}. "
            f"Creative hook: {sendability_gate['creative_hook']}. If it is only cute or decorative, generic, or not useful as a chat reply, it fails.\n"
            f"Acting direction: {entry.motion}. Motion template: {template_plan['motion_template']}. "
            "The four key poses must be stable source poses for deterministic local animation, not a full freehand animation sheet.\n"
            f"{keypose_prompt_rules(source_layout, render_frame_count)}\n"
            f"{motion_profile_prompt(motion_profile)}\n"
            f"Four keypose acting plan:\n{keypose_lines}\n"
            f"Local render timeline summary: {render_frame_count} frames will be rendered from these key poses by the processor; keep pose identity and props compatible with that timeline. "
            f"The processor will add these local non-text effects later: {', '.join(template_plan['local_effects']) or 'none'}; do not draw them as random one-frame details.\n"
            f"Continuity acceptance: {template_plan['continuity_acceptance']}.\n"
            f"Tone: {tone}; funny, slightly unhinged, but safe for public WeChat review.\n"
            "Composition: one character only, centered, full character or large bust visible, oversized readable face, crisp silhouette, "
            "simple transparent-friendly background, no clutter, no tiny joke-critical props, high contrast, designed to read at 240x240.\n"
            f"Hard negative rules: {HARD_IMAGE_RULES}."
        )
        frame_count = render_frame_count
        raw_layout = source_layout
    else:
        raw_layout = animation_layout
        rows, cols = parse_sheet_layout(animation_layout)
        frame_plan = animation_frames_for_entry(entry, rows * cols)
        frame_lines = "\n".join(
            f"Frame {frame_index}: {description}" for frame_index, description in enumerate(frame_plan, start=1)
        )
        frame_count = len(frame_plan)
        prompt = (
            "Create one raw no-text motion sheet for a Chinese WeChat animated meme GIF sticker pack.\n"
            f"Character card: {character_card}\n"
            f"Subject reminder: {subject.strip() or 'uploaded reference character'}.\n"
            f"Visual style: {style_prompt(style)}.\n"
            f"Persona context: {persona}; useful visual cues: {persona_prompt(persona)}.\n"
            f"Meme item {index:02d}: {entry.name}. Chat send scenario: {entry.scene}. "
            f"The final Chinese caption will be added later by a local processor as \"{caption}\"; do not draw any text.\n"
            "Sendability gate: this must be a sticker people want to send, not just a nice illustration. "
            f"Reuse trigger: {sendability_gate['reuse_trigger']}. Emotional value: {sendability_gate['emotional_value']}. "
            f"Creative hook: {sendability_gate['creative_hook']}. If it is only cute or decorative, generic, or not useful as a chat reply, it fails.\n"
            f"Acting direction: exaggerated readable reaction, {entry.motion}; make the emotion understandable before the caption is added.\n"
            f"{sheet_prompt_rules(animation_layout)}\n"
            f"{motion_profile_prompt(motion_profile)}\n"
            f"Frame-by-frame acting plan:\n{frame_lines}\n"
            "Motion continuity: use small readable in-between changes between neighboring frames; avoid flicker, teleporting hands, changing camera distance, changing face proportions, or adding/removing props that are not in the frame plan.\n"
            f"Tone: {tone}; funny, slightly unhinged, but safe for public WeChat review.\n"
            "Composition: one character only, centered, full character or large bust visible, oversized readable face, crisp silhouette, "
            "simple transparent-friendly background, no clutter, no tiny joke-critical props, high contrast, designed to read at 240x240.\n"
            f"Hard negative rules: {HARD_IMAGE_RULES}."
        )
    return {
        "index": index,
        "name": entry.name,
        "meme_name": entry.name,
        "caption": entry.text,
        "send_scene": entry.scene,
        "scene": entry.scene,
        "motion_type": entry.motion,
        "motion": entry.motion,
        "motion_profile": motion_profile,
        "source_mode": source_mode,
        "animation_layout": raw_layout,
        "keypose_layout": keypose_layout if source_mode == "keyposes" else "",
        "render_frame_count": render_frame_count if source_mode == "keyposes" else frame_count,
        "motion_template": template_plan["motion_template"],
        "keypose_beats": template_plan["keypose_beats"],
        "timeline": template_plan["timeline"],
        "local_effects": template_plan["local_effects"],
        "qc_policy": template_plan["qc_policy"],
        "continuity_acceptance": template_plan["continuity_acceptance"],
        "frames": frame_plan,
        "frame_beats": frame_plan,
        "8_frame_beats": frame_plan if frame_count == 8 else frame_plan[:8],
        f"{frame_count}_frame_beats": frame_plan,
        "visual_gag": visual_gag_for_entry(entry),
        "sendability_gate": sendability_gate,
        "negative_prompt": HARD_IMAGE_RULES,
        "qc_acceptance": qc_acceptance_for_entry(raw_layout),
        "regenerate_hint": template_plan["regenerate_hint"] if source_mode == "keyposes" else regenerate_hint_for_entry(entry, animation_layout),
        "raw_image_filename": f"{index:02d}-{slug_filename(entry.name)}-{raw_layout}.png",
        "prompt": prompt,
    }


def shell_join(parts: list[str]) -> str:
    return " ".join(shlex.quote(str(part)) for part in parts)


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
    quality_mode: str = "submission",
    source_mode: str = DEFAULT_SOURCE_MODE,
    keypose_layout: str = DEFAULT_KEYPOSE_LAYOUT,
    render_frame_count: int = DEFAULT_RENDER_FRAME_COUNT,
    image_provider: str = DEFAULT_IMAGE_PROVIDER,
) -> dict:
    validate_pack_size(pack_size, mode)
    source_mode = parse_source_mode(source_mode)
    image_provider = parse_image_provider(image_provider)
    if source_mode == "keyposes":
        source_layout = parse_keypose_layout(keypose_layout)
    else:
        parse_sheet_layout(animation_layout)
        source_layout = animation_layout
    parse_quality_mode(quality_mode)
    entries = default_entries(persona, pack_size)
    character_card = build_character_card(subject, style, reference_image)
    prompts = [
        image_prompt_for_entry(
            entry,
            index,
            subject,
            persona,
            style,
            character_card,
            tone,
            animation_layout,
            source_mode,
            keypose_layout,
            render_frame_count,
        )
        for index, entry in enumerate(entries, start=1)
    ]
    pack_slug = slug_filename(pack_name)
    raw_output_dir = f"output/raw-frames/{pack_slug}"
    output_dir = f"output/{pack_slug}"
    processor_command_args = [
        "python",
        "skills/generate-meme-gif-pack/scripts/meme_pack.py",
        "build-pack",
        "--source-dir",
        raw_output_dir,
        "--output-dir",
        output_dir,
        "--persona",
        persona,
        "--style",
        style,
        "--pack-size",
        str(pack_size),
        "--mode",
        mode,
        "--pack-name",
        pack_name,
        "--source-layout",
        source_layout,
        "--source-mode",
        source_mode,
        "--keypose-layout",
        keypose_layout,
        "--render-frame-count",
        str(render_frame_count),
        "--quality-mode",
        quality_mode,
        "--strict-qc",
        "--strict-continuity-qc",
    ]
    accept_generated_command_args = [
        "python",
        "skills/generate-meme-gif-pack/scripts/meme_pack.py",
        "accept-generated",
        "--plan",
        "output/<plan-json>",
        "--index",
        "1",
        "--image",
        "path/to/generated.png",
        "--source-dir",
        raw_output_dir,
    ]
    first_three_instruction = (
        "The first 3 are a QC checkpoint, not a stopping point. If the user requested a full pack, "
        "do not end the task after the first-3 preview."
    )
    completion_definition = (
        f"Complete only when {pack_size} accepted raw images have been built into preview.html, "
        "named-gifs/*.gif, wechat-submit/main/*.gif, manifest.json, and qc_report.json."
    )
    base_pause_conditions = [
        "user explicitly requested first-3 preview only",
        "image generation tooling is unavailable",
        "generated image only exists as an unsaved attachment and the user must export a local file",
        "strict QC or continuity QC fails repeatedly after regeneration attempts and user decision is needed",
        "the user explicitly pauses or changes the task",
    ]
    generate_raw_batch_command_args = [
        "python",
        "skills/generate-meme-gif-pack/scripts/meme_pack.py",
        "generate-raw-batch",
        "--plan",
        "output/<plan-json>",
        "--provider",
        IMAGE_PROVIDER_OPENAI_IMAGES_API,
        "--concurrency",
        "3",
    ]
    if image_provider == IMAGE_PROVIDER_CODEX_BUILTIN:
        requires_agent_tooling = {
            "image_generation_tool": "image_gen",
            "local_processor": "scripts/meme_pack.py",
            "provider_mode": "terminal_action",
            "same_turn_postprocess_supported": False,
            "tool_boundary": (
                "Codex built-in image_gen is a terminal action in this environment. The local processor "
                "cannot generate images, and the agent must not assume it can run accept-generated or QC "
                "in the same turn after calling image_gen."
            ),
        }
        image_handoff = {
            "tool_output_requirement": (
                "When using Codex built-in image_gen, call image_gen as the final action for the current "
                "turn. In the next turn, after the generated PNG has been saved/exported to a local file, "
                "run accept-generated and QC."
            ),
            "accept_generated_command": shell_join(accept_generated_command_args),
            "index_file": f"{raw_output_dir}/generated-index.json",
            "blocked_without_local_file": True,
            "terminal_action": True,
            "same_turn_postprocessing": False,
            "next_turn_resume": "Run accept-generated with the saved file path, then qc-sheet/build-preview or build-pack.",
        }
        workflow_contract = {
            "first_three_policy": "The first 3 are a QC checkpoint, not a stopping point.",
            "continue_after_preview": (
                "If the user requested a full pack, continue across turns after generated files are "
                "available; do not promise same-turn postprocessing after Codex built-in image_gen."
            ),
            "completion_definition": completion_definition,
            "same_turn_continuation": False,
            "allowed_pause_conditions": [
                "waiting for the next turn with exported Codex image_gen files",
                *base_pause_conditions,
            ],
        }
        agent_instructions = [
            (
                "Codex built-in image_gen is a terminal action. Use it only as the final action of the "
                "current turn for the next required no-text keypose sheet; do not try to run "
                "accept-generated or QC in the same turn after calling it."
            ),
            (
                "Before calling image_gen, write/review the plan and identify the target image_prompts "
                "index, raw_image_filename, and prompt. Do not describe the sticker pack as complete "
                "after a raw keypose sheet is generated."
            ),
            (
                "When the user returns in the next turn with a saved/exported local image file, run "
                "meme_pack.py accept-generated with the plan JSON, sticker index, generated image path, "
                "and raw output directory so QC/build-pack can find the exact planned filename."
            ),
            f"Run meme_pack.py qc-sheet --source-mode {source_mode} --source-layout {source_layout} --quality-mode {quality_mode} on accepted sheets and regenerate any fail or weak warning using regenerate_hint.",
            (
                f"{first_three_instruction} For built-in image_gen this checkpoint may span multiple turns; "
                "after the first 3 pass QC, resume in the next turn with the remaining prompts until the "
                "full pack reaches the completion definition."
            ),
            f"Save raw generated no-text images using raw_image_filename under {raw_output_dir}; accept-generated writes generated-index.json as the handoff audit trail.",
            "Replace any weak joke before generation: every sticker must pass meme_quality_bar and image_prompts[].sendability_gate; if it is only cute or decorative, rewrite the caption, scene, visual gag, and motion.",
            "Reject and regenerate any raw sheet that contains text, speech bubbles, official logos, brand marks, wrong grid count, a tiny face, edge-crossing props, or a character that drifts from the character card.",
            f"After all planned raw sheets are accepted, run meme_pack.py build-pack with --source-mode {source_mode} --source-layout {source_layout} --quality-mode {quality_mode} --strict-qc --strict-continuity-qc plus the same persona, style, pack_size, mode, and pack_name.",
        ]
    elif image_provider == IMAGE_PROVIDER_OPENAI_IMAGES_API:
        requires_agent_tooling = {
            "image_generation_tool": image_provider,
            "local_processor": "scripts/meme_pack.py",
            "provider_mode": "scriptable_api",
            "same_turn_postprocess_supported": True,
            "tool_boundary": (
                "This provider is scriptable. generate-raw-batch reads plan image_prompts, calls the "
                "configured image generation CLI/API, writes planned raw filenames, records "
                "generated-index.json, then the local processor can QC/build in the same workflow."
            ),
        }
        image_handoff = {
            "tool_output_requirement": (
                "Run generate-raw-batch to create local raw PNG files from every planned image_prompt, "
                "then run build-preview or build-pack."
            ),
            "generate_raw_batch_command": shell_join(generate_raw_batch_command_args),
            "accept_generated_command": shell_join(accept_generated_command_args),
            "index_file": f"{raw_output_dir}/generated-index.json",
            "blocked_without_local_file": False,
            "terminal_action": False,
            "same_turn_postprocessing": True,
        }
        workflow_contract = {
            "first_three_policy": "The first 3 are a QC checkpoint, not a stopping point.",
            "continue_after_preview": (
                "Use generate-raw-batch for scriptable generation, inspect/build the first-3 preview, "
                "then continue to the remaining planned prompts or the full build in the same workflow."
            ),
            "completion_definition": completion_definition,
            "same_turn_continuation": True,
            "allowed_pause_conditions": base_pause_conditions,
        }
        agent_instructions = [
            "Use meme_pack.py generate-raw-batch with the plan JSON to generate planned raw keypose PNGs through the OpenAI Images API provider. Do not use Codex built-in image_gen for this automated provider path.",
            "For a cautious first pass, generate and inspect the first 3 planned prompts before the full pack; for fully automated runs, keep regenerate-on-fail behavior and continue until all planned raw files exist.",
            f"Run meme_pack.py qc-sheet --source-mode {source_mode} --source-layout {source_layout} --quality-mode {quality_mode} on accepted sheets and regenerate any fail or weak warning using regenerate_hint.",
            f"{first_three_instruction} After QC passes, continue to the remaining prompts in the same workflow.",
            f"After raw sheets are generated, run meme_pack.py build-pack with --source-mode {source_mode} --source-layout {source_layout} --quality-mode {quality_mode} --strict-qc --strict-continuity-qc plus the same persona, style, pack_size, mode, and pack_name.",
        ]
    else:
        requires_agent_tooling = {
            "image_generation_tool": image_provider,
            "local_processor": "scripts/meme_pack.py",
            "provider_mode": "external_or_scriptable_files",
            "same_turn_postprocess_supported": True,
            "tool_boundary": (
                "The local processor cannot generate images. The external provider or operator must "
                "produce local image files before accept-generated/QC can run."
            ),
        }
        image_handoff = {
            "tool_output_requirement": (
                "After each provider output is available as a local PNG/GIF file, run accept-generated "
                "and continue QC/build steps in the same workflow."
            ),
            "accept_generated_command": shell_join(accept_generated_command_args),
            "index_file": f"{raw_output_dir}/generated-index.json",
            "blocked_without_local_file": True,
            "terminal_action": False,
            "same_turn_postprocessing": True,
        }
        workflow_contract = {
            "first_three_policy": "The first 3 are a QC checkpoint, not a stopping point.",
            "continue_after_preview": (
                "If the user requested a full pack, continue to the remaining prompts in the same "
                "workflow after QC passes."
            ),
            "completion_definition": completion_definition,
            "same_turn_continuation": True,
            "allowed_pause_conditions": base_pause_conditions,
        }
        agent_instructions = [
            "Use the external batch-capable image provider to generate the first 3 image_prompts before committing to all planned image_prompts. Save each raw no-text motion sheet exactly as raw_image_filename.",
            "After each image generation result is saved/exported as a local image, run meme_pack.py accept-generated with the plan JSON, sticker index, generated image path, and raw output directory so QC/build-pack can find the exact planned filename.",
            f"Run meme_pack.py qc-sheet --source-mode {source_mode} --source-layout {source_layout} --quality-mode {quality_mode} on those first 3 accepted sheets and regenerate any fail or weak warning using regenerate_hint.",
            f"{first_three_instruction} After QC passes, continue to the remaining prompts in the same workflow.",
            "After the first 3 sheets pass QC, generate one no-text motion sheet per remaining planned image_prompts item.",
            f"Save raw generated no-text images using raw_image_filename under {raw_output_dir}; accept-generated writes generated-index.json as the handoff audit trail.",
            "Replace any weak joke before generation: every sticker must pass meme_quality_bar and image_prompts[].sendability_gate; if it is only cute or decorative, rewrite the caption, scene, visual gag, and motion.",
            "Reject and regenerate any raw sheet that contains text, speech bubbles, official logos, brand marks, wrong grid count, a tiny face, edge-crossing props, or a character that drifts from the character card.",
            f"After raw sheets are accepted, run meme_pack.py build-pack with --source-mode {source_mode} --source-layout {source_layout} --quality-mode {quality_mode} --strict-qc --strict-continuity-qc plus the same persona, style, pack_size, mode, and pack_name.",
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
        "quality_mode": quality_mode,
        "source_mode": source_mode,
        "image_provider": image_provider,
        "raw_output_dir": raw_output_dir,
        "character_card": character_card,
        "animation": {
            "source_mode": source_mode,
            "source_layout": source_layout,
            "keypose_layout": keypose_layout if source_mode == "keyposes" else "",
            "keypose_count": parse_sheet_layout(keypose_layout)[0] * parse_sheet_layout(keypose_layout)[1]
            if source_mode == "keyposes"
            else 0,
            "frames_per_sticker": parse_sheet_layout(source_layout)[0] * parse_sheet_layout(source_layout)[1],
            "rendered_frame_count": render_frame_count if source_mode == "keyposes" else parse_sheet_layout(source_layout)[0] * parse_sheet_layout(source_layout)[1],
            "quality_mode": quality_mode,
            "rules": keypose_prompt_rules(keypose_layout, render_frame_count)
            if source_mode == "keyposes"
            else sheet_prompt_rules(animation_layout),
        },
        "meme_quality_bar": MEME_QUALITY_BAR,
        "items": [asdict(entry) for entry in entries],
        "image_prompts": prompts,
        "requires_agent_tooling": requires_agent_tooling,
        "image_handoff": image_handoff,
        "workflow_contract": workflow_contract,
        "agent_instructions": agent_instructions,
        "processor_command_args": processor_command_args,
        "processor_command": shell_join(processor_command_args),
    }


def default_entries(persona: str, pack_size: int = 24) -> list[MemeEntry]:
    validate_pack_size(pack_size, "wechat" if pack_size in {16, 24} else "self_use")
    persona_entries = PERSONA_ENTRIES.get(persona, PERSONA_ENTRIES["科研打工人"])
    if persona == "Vibe Coding":
        ordered = [*persona_entries, *COMMON_ENTRIES, *FILLER_ENTRIES]
    else:
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


def _caption_text_candidates(text: str) -> list[str]:
    normalized = text.replace("\\n", "\n").strip()
    blocks = [block.strip() for block in normalized.splitlines() if block.strip()]
    candidates: list[str] = []
    if len(blocks) > 1:
        candidates.append("".join(blocks))
        candidates.append(" ".join(blocks))
    candidates.append(normalized)
    unique: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in unique:
            unique.append(candidate)
    return unique or [""]


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
    single_line_min_size = max(min_font_size, min(max_font_size, 26))
    for size in range(max_font_size, single_line_min_size - 1, -1):
        font = _font(font_path, size)
        for candidate in _caption_text_candidates(text):
            lines = _wrap_text(candidate, font, max_width)
            line_height = max(_text_size(line, font)[1] for line in lines) + 6
            if (
                len(lines) == 1
                and line_height <= max_height
                and all(_text_size(line, font)[0] <= max_width for line in lines)
            ):
                return lines, font
    for size in range(max_font_size, min_font_size - 1, -1):
        font = _font(font_path, size)
        lines = _wrap_text(text, font, max_width)
        line_height = max(_text_size(line, font)[1] for line in lines) + 6
        if line_height * len(lines) <= max_height and all(_text_size(line, font)[0] <= max_width for line in lines):
            return lines, font
    font = _font(font_path, min_font_size)
    lines = _wrap_text(text, font, max_width)
    return _truncate_lines_to_height(lines, font, max_width, max_height), font


def caption_text_height(lines: list[str], font: ImageFont.ImageFont) -> int:
    line_boxes = [_text_size(line, font) for line in lines]
    line_height = max(height for _, height in line_boxes) + 6
    return line_height * len(lines)


def caption_reserved_height_for_text(text: str, font_path: str) -> int:
    lines, font = fit_text_lines(text, font_path, max_width=214, max_height=CAPTION_RESERVED_HEIGHT)
    reserved = caption_text_height(lines, font) + CAPTION_BOTTOM_PADDING - CAPTION_ALLOWED_SUBJECT_OVERLAP
    return max(MIN_CAPTION_RESERVED_HEIGHT, min(CAPTION_RESERVED_HEIGHT, reserved))


def slug_filename(name: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|\s]+', "", name).strip(".")
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
    if ratio >= 7.0:
        return "1x8"
    if 3.3 <= ratio < 7.0:
        return "1x4"
    if 1.8 <= ratio <= 2.3:
        return "2x4"
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
    source_pixels = pixel_data(rgba)
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
            spill_delta = min(red, blue) - green
            if alpha and red >= 145 and blue >= 120 and green <= 145 and spill_delta >= 28:
                spill_strength = min(1.0, spill_delta / 150)
                alpha = int(alpha * max(0.08, 1.0 - 1.18 * spill_strength))
                neutral = max(0, min(255, int(green * 1.08)))
                red = int(red * (1.0 - 0.58 * spill_strength) + neutral * (0.30 * spill_strength))
                blue = int(blue * (1.0 - 0.66 * spill_strength) + neutral * (0.38 * spill_strength))
            pixels.append((red, green, blue, alpha))
    rgba.putdata(pixels)
    return rgba


def soften_alpha_edges(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    softened = alpha.filter(ImageFilter.GaussianBlur(radius=0.45))
    clipped = ImageChops.darker(alpha, softened)
    rgba.putalpha(clipped.point(lambda value: 0 if value < 8 else min(255, value)))
    return rgba


def clean_generated_frame_background(image: Image.Image) -> Image.Image:
    return soften_alpha_edges(remove_light_background(remove_chroma_background(image)))


def _magenta_distance(red: int, green: int, blue: int) -> float:
    return math.sqrt((red - 255) ** 2 + green**2 + (blue - 255) ** 2)


def detect_checkerboard_background(image: Image.Image) -> bool:
    sample = image.convert("RGBA").resize((48, 48), Image.Resampling.NEAREST)
    labels: list[int] = []
    light = 0
    dark = 0
    gray_total = 0
    for red, green, blue, alpha in pixel_data(sample):
        if alpha < 240 or max(red, green, blue) - min(red, green, blue) > 8:
            labels.append(-1)
            continue
        if 232 <= red <= 246:
            light += 1
            gray_total += 1
            labels.append(1)
        elif 195 <= red <= 215:
            dark += 1
            gray_total += 1
            labels.append(0)
        else:
            labels.append(-1)
    total = sample.width * sample.height
    if gray_total / total < 0.22 or min(light, dark) / total < 0.04:
        return False
    transitions = 0
    comparable = 0
    for y in range(sample.height):
        for x in range(sample.width - 1):
            left = labels[y * sample.width + x]
            right = labels[y * sample.width + x + 1]
            if left >= 0 and right >= 0:
                comparable += 1
                transitions += int(left != right)
    for y in range(sample.height - 1):
        for x in range(sample.width):
            top = labels[y * sample.width + x]
            bottom = labels[(y + 1) * sample.width + x]
            if top >= 0 and bottom >= 0:
                comparable += 1
                transitions += int(top != bottom)
    return comparable > 0 and transitions / comparable > 0.10


def detect_background_mode(image: Image.Image) -> str:
    rgba = image.convert("RGBA")
    if detect_checkerboard_background(rgba):
        return "checkerboard"
    total = max(1, rgba.width * rgba.height)
    transparent = magenta = solid_light = 0
    for red, green, blue, alpha in pixel_data(rgba):
        if alpha < 16:
            transparent += 1
        elif _magenta_distance(red, green, blue) < 48 or (red >= 210 and blue >= 190 and green <= 90):
            magenta += 1
        elif red >= 248 and green >= 248 and blue >= 248:
            solid_light += 1
    if transparent / total > 0.08:
        return "transparent"
    if magenta / total > 0.20:
        return "magenta"
    if solid_light / total > 0.25:
        return "solid_light"
    return "unknown"


def connected_components(image: Image.Image, min_area: int = 1) -> list[dict[str, object]]:
    alpha = image.convert("RGBA").getchannel("A")
    pixels = alpha.load()
    width, height = image.size
    visited = [[False] * width for _ in range(height)]
    components: list[dict[str, object]] = []

    for y in range(height):
        for x in range(width):
            if visited[y][x] or pixels[x, y] == 0:
                continue
            queue: deque[tuple[int, int]] = deque([(x, y)])
            visited[y][x] = True
            coords: list[tuple[int, int]] = []
            min_x = max_x = x
            min_y = max_y = y
            touches_edge = False
            while queue:
                cx, cy = queue.popleft()
                coords.append((cx, cy))
                min_x = min(min_x, cx)
                min_y = min(min_y, cy)
                max_x = max(max_x, cx)
                max_y = max(max_y, cy)
                if cx == 0 or cy == 0 or cx == width - 1 or cy == height - 1:
                    touches_edge = True
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < width and 0 <= ny < height and not visited[ny][nx] and pixels[nx, ny] > 0:
                        visited[ny][nx] = True
                        queue.append((nx, ny))
            if len(coords) >= min_area:
                components.append(
                    {
                        "area": len(coords),
                        "bbox": (min_x, min_y, max_x + 1, max_y + 1),
                        "touches_edge": touches_edge,
                        "pixels": coords,
                    }
                )
    components.sort(key=lambda item: int(item["area"]), reverse=True)
    return components


def _bbox_distance(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> int:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    dx = max(bx0 - ax1, ax0 - bx1, 0)
    dy = max(by0 - ay1, ay0 - by1, 0)
    return max(dx, dy)


def _component_artifact_reason(rgba: Image.Image, component: dict[str, object]) -> str:
    bbox = tuple(component["bbox"])
    x0, y0, x1, y1 = bbox
    width = x1 - x0
    height = y1 - y0
    area = int(component["area"])
    if area <= 0:
        return ""

    if height <= max(3, int(rgba.height * 0.018)) and width >= max(36, int(rgba.width * 0.28)):
        return "separator_line"
    if width <= max(3, int(rgba.width * 0.018)) and height >= max(36, int(rgba.height * 0.28)):
        return "separator_line"

    pixels = rgba.load()
    neutral_grid_pixels = 0
    for x, y in component["pixels"]:
        red, green, blue, alpha = pixels[x, y]
        if alpha == 0:
            continue
        spread = max(red, green, blue) - min(red, green, blue)
        is_checker_gray = spread <= 14 and (
            (196 <= red <= 216 and 196 <= green <= 216 and 196 <= blue <= 216)
            or (230 <= red <= 247 and 230 <= green <= 247 and 230 <= blue <= 247)
        )
        if is_checker_gray:
            neutral_grid_pixels += 1

    small_component_limit = max(480, int(rgba.width * rgba.height * 0.012))
    if area <= small_component_limit and neutral_grid_pixels / area >= 0.72:
        return "checkerboard"
    return ""


def filter_subject_components(
    image: Image.Image,
    min_component_area: int = 8,
    keep_distance: int = 18,
) -> tuple[Image.Image, dict[str, object]]:
    rgba = image.convert("RGBA")
    components = connected_components(rgba, min_area=1)
    sized_components = [component for component in components if int(component["area"]) >= min_component_area]
    artifact_counts = {"checkerboard": 0, "separator_line": 0}
    kept = []
    for component in sized_components:
        reason = _component_artifact_reason(rgba, component)
        if reason:
            artifact_counts[reason] += 1
            continue
        kept.append(component)
    if not kept:
        return Image.new("RGBA", rgba.size, (0, 0, 0, 0)), {
            "component_count": len(components),
            "kept_component_count": 0,
            "removed_component_count": len(components),
            "removed_artifact_component_count": sum(artifact_counts.values()),
            "removed_checkerboard_component_count": artifact_counts["checkerboard"],
            "removed_separator_line_count": artifact_counts["separator_line"],
        }

    largest = kept[0]
    largest_bbox = tuple(largest["bbox"])
    keep_components = [
        component
        for component in kept
        if component is largest or _bbox_distance(largest_bbox, tuple(component["bbox"])) <= keep_distance
    ]
    keep_pixels = {coord for component in keep_components for coord in component["pixels"]}
    output = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    source = rgba.load()
    target = output.load()
    for x, y in keep_pixels:
        target[x, y] = source[x, y]
    return output, {
        "component_count": len(components),
        "kept_component_count": len(keep_components),
        "removed_component_count": len(components) - len(keep_components),
        "removed_artifact_component_count": sum(artifact_counts.values()),
        "removed_checkerboard_component_count": artifact_counts["checkerboard"],
        "removed_separator_line_count": artifact_counts["separator_line"],
        "largest_component_area": int(largest["area"]),
        "largest_component_bbox": list(largest_bbox),
    }


def bbox_touches_edge(bbox: tuple[int, int, int, int] | None, width: int, height: int, margin: int = 1) -> bool:
    if not bbox:
        return False
    x0, y0, x1, y1 = bbox
    return x0 <= margin or y0 <= margin or x1 >= width - margin or y1 >= height - margin


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def bbox_drift_metrics(bboxes: list[tuple[int, int, int, int]], cell_size: tuple[int, int]) -> dict[str, float]:
    if not bboxes:
        return {"center_ratio": 1.0, "size_ratio": 1.0, "area_ratio": 1.0}
    widths = [max(1, box[2] - box[0]) for box in bboxes]
    heights = [max(1, box[3] - box[1]) for box in bboxes]
    areas = [width * height for width, height in zip(widths, heights)]
    centers_x = [(box[0] + box[2]) / 2 for box in bboxes]
    centers_y = [(box[1] + box[3]) / 2 for box in bboxes]
    med_width = max(1.0, _median([float(width) for width in widths]))
    med_height = max(1.0, _median([float(height) for height in heights]))
    med_area = max(1.0, _median([float(area) for area in areas]))
    med_center_x = _median(centers_x)
    med_center_y = _median(centers_y)
    max_center_delta = max(math.hypot(cx - med_center_x, cy - med_center_y) for cx, cy in zip(centers_x, centers_y))
    max_size_delta = max(
        max(abs(width - med_width) / med_width, abs(height - med_height) / med_height)
        for width, height in zip(widths, heights)
    )
    max_area_delta = max(abs(area - med_area) / med_area for area in areas)
    return {
        "center_ratio": round(max_center_delta / max(cell_size), 4),
        "size_ratio": round(max(max_size_delta, max_area_delta), 4),
        "area_ratio": round(max_area_delta, 4),
    }


def qc_limits_for(quality_mode: str, motion_profile: str) -> dict[str, object]:
    limits = dict(QC_LIMITS[parse_quality_mode(quality_mode)])
    profile_limits = MOTION_PROFILE_LIMITS[parse_motion_profile(motion_profile)]
    for key in ("center_drift_ratio", "size_drift_ratio"):
        if profile_limits[key] is not None:
            limits[key] = profile_limits[key]
    return limits


def analyze_frames_for_qc(
    frames: list[Image.Image], quality_mode: str, motion_profile: str = "standard"
) -> tuple[list[dict[str, object]], list[str], list[str], dict[str, float], bool]:
    limits = qc_limits_for(quality_mode, motion_profile)
    errors: list[str] = []
    warnings: list[str] = []
    frame_reports: list[dict[str, object]] = []
    bboxes: list[tuple[int, int, int, int]] = []
    edge_touch = False

    for index, frame in enumerate(frames, start=1):
        cleaned = clean_generated_frame_background(frame)
        filtered, component_info = filter_subject_components(cleaned)
        bbox = filtered.getbbox()
        cell_area = max(1, filtered.width * filtered.height)
        alpha_pixels = sum(1 for pixel in pixel_data(filtered.getchannel("A")) if pixel > 0)
        area_ratio = alpha_pixels / cell_area
        touches_edge = bbox_touches_edge(bbox, filtered.width, filtered.height, margin=1)
        edge_touch = edge_touch or touches_edge
        if bbox:
            bboxes.append(bbox)
        frame_report = {
            "index": index,
            "bbox": list(bbox) if bbox else None,
            "alpha_area_ratio": round(area_ratio, 4),
            "edge_touch": touches_edge,
            **component_info,
        }
        frame_reports.append(frame_report)
        checkerboard_residue_count = int(component_info.get("removed_checkerboard_component_count", 0))
        separator_line_count = int(component_info.get("removed_separator_line_count", 0))
        if checkerboard_residue_count >= 4:
            warnings.append(
                f"frame {index} has fake checkerboard residue near the subject; regenerate with true alpha or pure #FF00FF"
            )
        if separator_line_count:
            warnings.append(f"frame {index} has sheet separator line residue; regenerate without panel borders or lines")
        if not bbox or area_ratio < float(limits["min_area_ratio"]):
            errors.append(f"frame {index} has no readable subject or subject is too small")
        if touches_edge:
            errors.append(f"frame {index} subject touches the cell edge")

    drift = bbox_drift_metrics(bboxes, frames[0].size if frames else (1, 1))
    if len(bboxes) > 1 and drift["center_ratio"] > float(limits["center_drift_ratio"]):
        errors.append(f"frame center drift is too high: {drift['center_ratio']}")
    if len(bboxes) > 1 and drift["size_ratio"] > float(limits["size_drift_ratio"]):
        errors.append(f"frame size drift is too high: {drift['size_ratio']}")
    if len(bboxes) > 1 and quality_mode == "preview" and drift["size_ratio"] > 0.45:
        warnings.append(f"preview frame size drift is visible: {drift['size_ratio']}")
    return frame_reports, warnings, errors, drift, edge_touch


def qc_sheet(
    input_path: Path,
    source_layout: str = "auto",
    quality_mode: str = "submission",
    strict: bool = True,
    motion_profile: str = "standard",
    source_mode: str = "motion_sheet",
) -> dict:
    quality_mode = parse_quality_mode(quality_mode)
    motion_profile = parse_motion_profile(motion_profile)
    source_mode = parse_source_mode(source_mode)
    image = Image.open(input_path)
    errors: list[str] = []
    warnings: list[str] = []
    background_mode = detect_background_mode(image.convert("RGBA"))
    if background_mode == "checkerboard":
        errors.append("fake checkerboard transparency detected")
    elif background_mode == "solid_light":
        warnings.append("solid light background detected; use true alpha or pure #FF00FF for submission-safe cleanup")
    elif background_mode == "unknown":
        warnings.append("background is not transparent, #FF00FF, or clean white; chroma cleanup may leave artifacts")

    if getattr(image, "is_animated", False):
        frames = [frame.convert("RGBA") for frame in ImageSequence.Iterator(image)]
        detected_layout = "gif"
        animation_source = "animated_gif"
    else:
        rgba = image.convert("RGBA")
        detected_layout = infer_sheet_layout(input_path, rgba, source_layout)
        if detected_layout == "single":
            frames = [rgba]
            animation_source = "single"
        else:
            frames = split_sheet_frames(rgba, detected_layout)
            animation_source = "sheet"

    limits = QC_LIMITS[quality_mode]
    required_layout = limits["required_layout"]
    if required_layout and detected_layout != required_layout:
        errors.append(f"{quality_mode} mode requires {required_layout} motion sheets; got {detected_layout}")
    required_layouts = limits.get("required_layouts")
    if quality_mode == "submission":
        if source_mode == "keyposes":
            required_layouts = KEYPOSE_LAYOUTS
        elif source_mode == "motion_sheet":
            required_layouts = MOTION_SHEET_LAYOUTS
    if required_layouts and source_mode != "single_bounce" and detected_layout not in required_layouts:
        allowed = ", ".join(sorted(required_layouts))
        errors.append(f"{quality_mode} mode requires one of {allowed} {source_mode} sheets; got {detected_layout}")
    if bool(limits["require_multiframe"]) and source_mode != "single_bounce" and len(frames) <= 1:
        errors.append("single_bounce sources are preview-only; use a real 2x4 or 4x4 motion sheet for submission")
    if source_mode == "single_bounce" and quality_mode == "submission":
        errors.append("single_bounce sources are preview-only; use keyposes or 2x4 motion sheets for submission")
    if detected_layout in SHEET_LAYOUTS:
        expected_count = parse_sheet_layout(detected_layout)[0] * parse_sheet_layout(detected_layout)[1]
        if len(frames) != expected_count:
            errors.append(f"expected {expected_count} frames for {detected_layout}, got {len(frames)}")
    frame_qc_profile = "action" if source_mode == "keyposes" else motion_profile
    frame_reports, frame_warnings, frame_errors, drift, edge_touch = analyze_frames_for_qc(
        frames, quality_mode, frame_qc_profile
    )
    if source_mode == "keyposes":
        frame_errors = [error for error in frame_errors if not error.startswith("frame size drift")]
    warnings.extend(frame_warnings)
    errors.extend(frame_errors)

    status = "fail" if errors else ("warning" if warnings else "pass")
    if status == "warning" and strict and quality_mode == "submission":
        errors.extend(warnings)
        status = "fail"
    return {
        "input": str(input_path),
        "status": status,
        "quality_mode": quality_mode,
        "source_mode": source_mode,
        "motion_profile": motion_profile,
        "strict": strict,
        "animation_source": animation_source,
        "source_layout": detected_layout,
        "frame_count": len(frames),
        "background_mode": background_mode,
        "edge_touch": edge_touch,
        "bbox_drift": drift,
        "warnings": warnings,
        "errors": errors,
        "frames": frame_reports,
    }


def write_qc_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


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


def normalize_motion_frames(
    raw_frames: list[Image.Image],
    size: tuple[int, int] = SUBJECT_CANVAS_SIZE,
    caption_reserved_height: int = CAPTION_RESERVED_HEIGHT,
    margin: int = 18,
    alignment_mode: str = "preserve",
) -> tuple[list[Image.Image], dict[str, object]]:
    if alignment_mode not in {"preserve", "stable"}:
        raise ValueError("alignment_mode must be 'preserve' or 'stable'.")
    cleaned_frames: list[Image.Image] = []
    bboxes: list[tuple[int, int, int, int]] = []
    component_reports: list[dict[str, object]] = []
    for raw in raw_frames:
        cleaned = clean_generated_frame_background(raw)
        filtered, component_report = filter_subject_components(cleaned)
        bbox = filtered.getbbox()
        component_reports.append(component_report)
        if bbox:
            bboxes.append(bbox)
        cleaned_frames.append(filtered)

    if bboxes and alignment_mode == "preserve":
        left = max(0, min(box[0] for box in bboxes) - 2)
        upper = max(0, min(box[1] for box in bboxes) - 2)
        right = min(cleaned_frames[0].width, max(box[2] for box in bboxes) + 2)
        lower = min(cleaned_frames[0].height, max(box[3] for box in bboxes) + 2)
        common_crop = (left, upper, right, lower)
        cropped_frames = [frame.crop(common_crop) for frame in cleaned_frames]
    elif bboxes:
        common_crop = None
        cropped_frames = []
        for frame in cleaned_frames:
            bbox = frame.getbbox()
            cropped_frames.append(frame.crop(bbox) if bbox else frame)
    else:
        common_crop = None
        cropped_frames = cleaned_frames

    max_width = max((frame.width for frame in cropped_frames if frame.width), default=1)
    max_height = max((frame.height for frame in cropped_frames if frame.height), default=1)
    target_width = size[0] - margin * 2
    target_height = size[1] - caption_reserved_height - margin
    scale = min(target_width / max_width, target_height / max_height)
    scale = max(0.1, scale)
    normalized: list[Image.Image] = []
    visual_height = size[1] - caption_reserved_height
    for cropped in cropped_frames:
        canvas = Image.new("RGBA", size, (0, 0, 0, 0))
        if cropped.getbbox():
            new_width = max(1, int(cropped.width * scale))
            new_height = max(1, int(cropped.height * scale))
            resized = cropped.resize((new_width, new_height), Image.Resampling.LANCZOS)
            x = (size[0] - new_width) // 2
            y = max(4, (visual_height - new_height) // 2)
            canvas.alpha_composite(resized, (x, y))
        normalized.append(canvas)
    return normalized, {
        "scale_normalized": True,
        "alignment_mode": alignment_mode,
        "normalization_scale": round(scale, 4),
        "source_bbox_count": len(bboxes),
        "common_crop": common_crop,
        "component_reports": component_reports,
    }


def _transform_canvas_sprite(frame: Image.Image, step: dict[str, float | int]) -> Image.Image:
    bbox = frame.getbbox()
    canvas = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    if not bbox:
        return canvas
    sprite = frame.crop(bbox)
    scale = float(step.get("scale", 1.0))
    rotation = float(step.get("rotation", 0.0))
    dx = int(round(float(step.get("dx", 0))))
    dy = int(round(float(step.get("dy", 0))))
    opacity = float(step.get("opacity", 1.0))
    if abs(scale - 1.0) > 0.001:
        new_size = (max(1, int(sprite.width * scale)), max(1, int(sprite.height * scale)))
        sprite = sprite.resize(new_size, Image.Resampling.LANCZOS)
    if abs(rotation) > 0.001:
        sprite = sprite.rotate(rotation, resample=Image.Resampling.BICUBIC, expand=True)
    if opacity < 1.0:
        alpha = sprite.getchannel("A").point(lambda value: int(value * max(0.0, min(1.0, opacity))))
        sprite.putalpha(alpha)
    center_x = (bbox[0] + bbox[2]) / 2 + dx
    center_y = (bbox[1] + bbox[3]) / 2 + dy
    x = int(round(center_x - sprite.width / 2))
    y = int(round(center_y - sprite.height / 2))
    canvas.alpha_composite(sprite, (x, y))
    return canvas


def _draw_template_effects(frame: Image.Image, template_id: str, frame_index: int, step: dict[str, float | int]) -> Image.Image:
    effect = str(step.get("effect", ""))
    if not effect:
        return frame
    bbox = frame.getbbox()
    if not bbox:
        return frame
    canvas = frame.copy()
    draw = ImageDraw.Draw(canvas, "RGBA")
    x0, y0, x1, y1 = bbox
    width = x1 - x0
    head_x = (x0 + x1) / 2
    head_y = y0 + max(10, (y1 - y0) * 0.22)
    phase = frame_index % 16

    if template_id == "soul_offline" and effect == "soul_puff":
        lift = max(0, phase - 5) * 2
        cx = int(min(210, max(30, head_x + width * 0.20)))
        cy = int(max(16, head_y - 18 - lift))
        draw.ellipse((cx - 9, cy - 11, cx + 9, cy + 11), fill=(245, 245, 255, 160), outline=(72, 95, 180, 210), width=2)
        draw.ellipse((cx - 3, cy - 5, cx + 3, cy + 2), fill=(72, 95, 180, 160))
        draw.ellipse((cx - 16, cy + 10, cx - 8, cy + 18), fill=(245, 245, 255, 130), outline=(72, 95, 180, 180), width=1)
        draw.ellipse((cx - 23, cy + 22, cx - 18, cy + 27), fill=(245, 245, 255, 110), outline=(72, 95, 180, 150), width=1)
    elif template_id == "loading_loop" and effect == "loading_dots":
        base_x = int(min(206, max(34, head_x + width * 0.28)))
        base_y = int(max(22, min(118, head_y - 8)))
        active = phase % 3
        for dot in range(3):
            radius = 4 + (2 if dot == active else 0)
            alpha = 235 if dot == active else 145
            dx = dot * 11
            draw.ellipse(
                (base_x + dx - radius, base_y - radius, base_x + dx + radius, base_y + radius),
                fill=(80, 135, 255, alpha),
                outline=(30, 65, 160, min(255, alpha + 10)),
                width=1,
            )
    elif template_id == "pretend_understand" and effect in {"sweat_drop", "awkward_lines"}:
        sx = int(min(212, max(34, head_x + width * 0.32)))
        sy = int(max(20, min(120, head_y - 2)))
        if 5 <= phase <= 10:
            drop = [(sx, sy - 8), (sx + 7, sy + 5), (sx - 5, sy + 6)]
            draw.polygon(drop, fill=(90, 165, 255, 205), outline=(40, 80, 180, 230))
        if 6 <= phase <= 11:
            lx = int(max(18, head_x - width * 0.42))
            ly = int(max(16, head_y - 10))
            for offset in (0, 8, 16):
                draw.line((lx - 3, ly + offset, lx - 13, ly + offset - 5), fill=(95, 105, 190, 190), width=3)
    return canvas


def render_keypose_motion(
    raw_keyposes: list[Image.Image],
    motion_template: str,
    frame_count: int = DEFAULT_RENDER_FRAME_COUNT,
    motion_profile: str = "standard",
    caption_reserved_height: int = CAPTION_RESERVED_HEIGHT,
) -> tuple[list[Image.Image], dict[str, object]]:
    if motion_template not in MOTION_TEMPLATE_IDS:
        motion_template = "steady_breath"
    motion_profile = parse_motion_profile(motion_profile)
    if len(raw_keyposes) < 2:
        raise ValueError("keypose rendering requires at least 2 key poses.")
    normalized_keyposes, normalization_meta = normalize_motion_frames(
        raw_keyposes,
        caption_reserved_height=caption_reserved_height,
        alignment_mode=alignment_mode_for_profile(motion_profile),
    )
    timeline = timeline_for_template(motion_template, frame_count)
    rendered: list[Image.Image] = []
    for index, step in enumerate(timeline):
        pose_index = max(1, min(len(normalized_keyposes), int(step.get("pose", 1)))) - 1
        transformed = _transform_canvas_sprite(normalized_keyposes[pose_index], step)
        rendered.append(_draw_template_effects(transformed, motion_template, index, step))
    return rendered, {
        **normalization_meta,
        "source_mode": "keyposes",
        "motion_template": motion_template,
        "local_effects": local_effects_for_template(motion_template),
        "qc_policy": qc_policy_for_template(motion_template),
        "rendered_frame_count": len(rendered),
        "keypose_count": len(raw_keyposes),
        "caption_reserved_height": caption_reserved_height,
        "timeline": timeline,
    }


def _subject_zone(frame: Image.Image, caption_reserved_height: int = CAPTION_RESERVED_HEIGHT) -> Image.Image:
    return frame.convert("RGBA").crop((0, 0, frame.width, max(1, frame.height - caption_reserved_height)))


def _alpha_bbox_area_center(frame: Image.Image) -> tuple[tuple[int, int, int, int] | None, int, tuple[float, float] | None]:
    cleaned = clean_generated_frame_background(frame)
    components = [
        component
        for component in connected_components(cleaned, min_area=24)
        if not _component_artifact_reason(cleaned, component)
    ]
    if components:
        bbox = tuple(components[0]["bbox"])
        area = int(components[0]["area"])
    else:
        alpha = cleaned.convert("RGBA").getchannel("A")
        bbox = alpha.point(lambda value: 255 if value > 24 else 0).getbbox()
        area = sum(1 for value in pixel_data(alpha) if value > 24)
    center = None
    if bbox:
        center = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
    return bbox, area, center


def _head_proxy_for_frame(
    frame: Image.Image,
    caption_reserved_height: int = CAPTION_RESERVED_HEIGHT,
) -> dict[str, object] | None:
    zone = clean_generated_frame_background(_subject_zone(frame, caption_reserved_height))
    components = [
        component
        for component in connected_components(zone, min_area=24)
        if not _component_artifact_reason(zone, component)
    ]
    if not components:
        return None
    bbox = tuple(components[0]["bbox"])
    x0, y0, x1, y1 = bbox
    height = max(1, y1 - y0)
    head_bbox = (x0, y0, x1, min(y1, y0 + max(12, int(height * 0.54))))
    crop = zone.crop(head_bbox).getchannel("A").point(lambda value: 255 if value > 24 else 0)
    mask = crop.resize((48, 48), Image.Resampling.BILINEAR)
    center = ((head_bbox[0] + head_bbox[2]) / 2, (head_bbox[1] + head_bbox[3]) / 2)
    aspect = (head_bbox[2] - head_bbox[0]) / max(1, head_bbox[3] - head_bbox[1])
    return {"bbox": head_bbox, "center": center, "mask": mask, "aspect": aspect}


def _mask_difference(left: Image.Image, right: Image.Image) -> float:
    total = 0.0
    count = 0
    for left_value, right_value in zip(pixel_data(left), pixel_data(right)):
        total += abs(int(left_value) - int(right_value)) / 255
        count += 1
    return total / max(1, count)


def _head_shape_report(frames: list[Image.Image], caption_reserved_height: int, motion_profile: str) -> dict[str, object]:
    proxies = [_head_proxy_for_frame(frame, caption_reserved_height) for frame in frames]
    valid = [proxy for proxy in proxies if proxy]
    if len(valid) < 2:
        return {"face_shape_drift_score": 0.0, "max_head_center_step_px": 0.0}

    shape_scores: list[float] = []
    center_steps: list[float] = []
    for index in range(len(proxies)):
        current = proxies[index]
        nxt = proxies[(index + 1) % len(proxies)]
        if not current or not nxt:
            continue
        mask_drift = _mask_difference(current["mask"], nxt["mask"])
        aspect_left = float(current["aspect"])
        aspect_right = float(nxt["aspect"])
        aspect_drift = abs(aspect_right - aspect_left) / max(0.1, min(aspect_left, aspect_right))
        shape_scores.append(max(mask_drift, aspect_drift))
        left_center = current["center"]
        right_center = nxt["center"]
        center_steps.append(math.hypot(right_center[0] - left_center[0], right_center[1] - left_center[1]))

    return {
        "face_shape_drift_score": round(max(shape_scores) if shape_scores else 0.0, 4),
        "max_head_center_step_px": round(max(center_steps) if center_steps else 0.0, 2),
    }


def _visible_frame_delta(left: Image.Image, right: Image.Image, caption_reserved_height: int = CAPTION_RESERVED_HEIGHT) -> dict[str, float]:
    left_rgba = _subject_zone(left, caption_reserved_height)
    right_rgba = _subject_zone(right, caption_reserved_height)
    visible = 0
    rgb_delta = 0.0
    alpha_delta = 0.0
    for left_pixel, right_pixel in zip(pixel_data(left_rgba), pixel_data(right_rgba)):
        left_alpha = left_pixel[3]
        right_alpha = right_pixel[3]
        if left_alpha <= 24 and right_alpha <= 24:
            continue
        visible += 1
        rgb_delta += (
            abs(left_pixel[0] - right_pixel[0])
            + abs(left_pixel[1] - right_pixel[1])
            + abs(left_pixel[2] - right_pixel[2])
        ) / (255 * 3)
        alpha_delta += abs(left_alpha - right_alpha) / 255
    if not visible:
        return {"rgb": 0.0, "alpha": 0.0}
    return {"rgb": rgb_delta / visible, "alpha": alpha_delta / visible}


def _component_count_for_frame(frame: Image.Image, caption_reserved_height: int = CAPTION_RESERVED_HEIGHT) -> int:
    cleaned = clean_generated_frame_background(_subject_zone(frame, caption_reserved_height))
    _, info = filter_subject_components(cleaned, min_component_area=5)
    return int(info.get("kept_component_count", info.get("component_count", 0)))


def _bbox_iou(left: tuple[int, int, int, int], right: tuple[int, int, int, int]) -> float:
    lx0, ly0, lx1, ly1 = left
    rx0, ry0, rx1, ry1 = right
    ix0 = max(lx0, rx0)
    iy0 = max(ly0, ry0)
    ix1 = min(lx1, rx1)
    iy1 = min(ly1, ry1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    intersection = (ix1 - ix0) * (iy1 - iy0)
    left_area = max(1, (lx1 - lx0) * (ly1 - ly0))
    right_area = max(1, (rx1 - rx0) * (ry1 - ry0))
    return intersection / max(1, left_area + right_area - intersection)


def _prop_components_for_frame(frame: Image.Image, caption_reserved_height: int = CAPTION_RESERVED_HEIGHT) -> list[dict[str, object]]:
    cleaned = clean_generated_frame_background(_subject_zone(frame, caption_reserved_height))
    components = [
        component
        for component in connected_components(cleaned, min_area=24)
        if not _component_artifact_reason(cleaned, component)
    ]
    if len(components) <= 1:
        return []
    largest_area = int(components[0]["area"])
    min_prop_area = max(120, int(largest_area * 0.018))
    props: list[dict[str, object]] = []
    for component in components[1:]:
        area = int(component["area"])
        if area < min_prop_area:
            continue
        bbox = tuple(component["bbox"])
        center = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
        props.append({"bbox": bbox, "center": center, "area": area})
    return props


def _component_matches(left: dict[str, object], right: dict[str, object]) -> bool:
    left_bbox = tuple(left["bbox"])
    right_bbox = tuple(right["bbox"])
    if _bbox_iou(left_bbox, right_bbox) >= 0.16:
        return True
    left_center = left["center"]
    right_center = right["center"]
    distance = math.hypot(right_center[0] - left_center[0], right_center[1] - left_center[1])
    area_scale = math.sqrt(max(float(left["area"]), float(right["area"])))
    return distance <= max(18.0, area_scale * 0.8)


def _bbox_has_visible_alpha(
    frame: Image.Image,
    bbox: tuple[int, int, int, int],
    component_area: int,
    caption_reserved_height: int = CAPTION_RESERVED_HEIGHT,
) -> bool:
    zone = _subject_zone(frame, caption_reserved_height).convert("RGBA")
    x0 = max(0, bbox[0] - 4)
    y0 = max(0, bbox[1] - 4)
    x1 = min(zone.width, bbox[2] + 4)
    y1 = min(zone.height, bbox[3] + 4)
    if x1 <= x0 or y1 <= y0:
        return False
    alpha = zone.crop((x0, y0, x1, y1)).getchannel("A")
    visible = sum(1 for value in pixel_data(alpha) if value > 24)
    return visible >= max(32, int(component_area * 0.28))


def _transient_component_frames(frames: list[Image.Image], caption_reserved_height: int = CAPTION_RESERVED_HEIGHT) -> list[int]:
    per_frame = [_prop_components_for_frame(frame, caption_reserved_height) for frame in frames]
    transient_frames: list[int] = []
    for index, components in enumerate(per_frame):
        previous_components = per_frame[index - 1]
        next_components = per_frame[(index + 1) % len(per_frame)]
        for component in components:
            has_previous = any(_component_matches(component, previous) for previous in previous_components)
            has_next = any(_component_matches(component, next_component) for next_component in next_components)
            bbox = tuple(component["bbox"])
            area = int(component["area"])
            has_previous_alpha = _bbox_has_visible_alpha(frames[index - 1], bbox, area, caption_reserved_height)
            has_next_alpha = _bbox_has_visible_alpha(frames[(index + 1) % len(frames)], bbox, area, caption_reserved_height)
            if not has_previous and not has_next and not has_previous_alpha and not has_next_alpha:
                transient_frames.append(index + 1)
                break
    return transient_frames


def _nearest_prop(left: dict[str, object], candidates: list[dict[str, object]]) -> tuple[dict[str, object] | None, float]:
    nearest: dict[str, object] | None = None
    nearest_distance = float("inf")
    left_center = left["center"]
    for candidate in candidates:
        candidate_center = candidate["center"]
        distance = math.hypot(candidate_center[0] - left_center[0], candidate_center[1] - left_center[1])
        if distance < nearest_distance:
            nearest = candidate
            nearest_distance = distance
    return nearest, nearest_distance


def _prop_motion_report(frames: list[Image.Image], caption_reserved_height: int = CAPTION_RESERVED_HEIGHT) -> dict[str, object]:
    per_frame = [_prop_components_for_frame(frame, caption_reserved_height) for frame in frames]
    transient_frames = _transient_component_frames(frames, caption_reserved_height)
    lifecycle_errors = [f"one-frame prop at frame {frame}" for frame in transient_frames]
    max_position_jump = 0.0
    max_area_jump = 0.0

    for index, components in enumerate(per_frame):
        next_components = per_frame[(index + 1) % len(per_frame)]
        for component in components:
            nearest, distance = _nearest_prop(component, next_components)
            if not nearest:
                continue
            area_left = max(1.0, float(component["area"]))
            area_right = max(1.0, float(nearest["area"]))
            area_jump = abs(area_right - area_left) / min(area_left, area_right)
            max_position_jump = max(max_position_jump, distance)
            max_area_jump = max(max_area_jump, area_jump)
            similar_size = area_jump <= PROP_QC_LIMITS["max_area_jump"] * 1.25
            if distance > PROP_QC_LIMITS["max_position_jump"] and similar_size:
                lifecycle_errors.append(f"prop position jump at frame {index + 1}->{(index + 1) % len(per_frame) + 1}: {distance:.1f}px")
            if area_jump > PROP_QC_LIMITS["max_area_jump"] and distance <= PROP_QC_LIMITS["max_position_jump"]:
                lifecycle_errors.append(f"prop area jump at frame {index + 1}->{(index + 1) % len(per_frame) + 1}: {area_jump:.2f}")

    return {
        "transient_component_frames": transient_frames,
        "prop_lifecycle_errors": sorted(set(lifecycle_errors)),
        "prop_position_jump": round(max_position_jump, 2),
        "prop_area_jump": round(max_area_jump, 4),
        "prop_counts": [len(components) for components in per_frame],
    }


def continuity_qc(
    frames: list[Image.Image],
    quality_mode: str = "submission",
    motion_profile: str = "standard",
    motion_template: str = "",
    strict: bool = True,
    caption_reserved_height: int = CAPTION_RESERVED_HEIGHT,
) -> dict[str, object]:
    parse_quality_mode(quality_mode)
    motion_profile = parse_motion_profile(motion_profile)
    errors: list[str] = []
    warnings: list[str] = []
    if len(frames) < 2:
        errors.append("continuity QC requires at least 2 rendered frames")
        return {
            "status": "fail",
            "warnings": warnings,
            "errors": errors,
            "metrics": {},
            "loop_closure_score": 1.0,
            "motion_energy_score": 0.0,
        }

    limits = CONTINUITY_LIMITS[motion_profile]
    zones = [_subject_zone(frame, caption_reserved_height) for frame in frames]
    bboxes: list[tuple[int, int, int, int] | None] = []
    areas: list[int] = []
    centers: list[tuple[float, float] | None] = []
    caption_zone_ratios: list[float] = []
    for frame, zone in zip(frames, zones):
        bbox, area, center = _alpha_bbox_area_center(zone)
        bboxes.append(bbox)
        areas.append(area)
        centers.append(center)
        caption_zone = frame.convert("RGBA").crop((0, max(0, frame.height - caption_reserved_height), frame.width, frame.height))
        caption_alpha = sum(1 for value in pixel_data(caption_zone.getchannel("A")) if value > 24)
        caption_zone_ratios.append(caption_alpha / max(1, caption_zone.width * caption_zone.height))

    deltas = [
        _visible_frame_delta(frames[index], frames[(index + 1) % len(frames)], caption_reserved_height)
        for index in range(len(frames))
    ]
    non_loop_deltas = deltas[:-1] or deltas
    rgb_steps = [delta["rgb"] for delta in non_loop_deltas]
    alpha_steps = [delta["alpha"] for delta in non_loop_deltas]
    loop_delta = deltas[-1]
    center_steps: list[float] = []
    area_jumps: list[float] = []
    for index in range(len(frames)):
        next_index = (index + 1) % len(frames)
        if centers[index] and centers[next_index]:
            center_steps.append(math.hypot(centers[next_index][0] - centers[index][0], centers[next_index][1] - centers[index][1]))
        median_area = max(1.0, _median([float(area) for area in areas if area > 0]))
        area_jumps.append(abs(areas[next_index] - areas[index]) / median_area)

    component_counts = [_component_count_for_frame(frame, caption_reserved_height) for frame in frames]
    median_components = _median([float(count) for count in component_counts])
    count_spike_frames: list[int] = []
    for index, count in enumerate(component_counts):
        previous_count = component_counts[index - 1]
        next_count = component_counts[(index + 1) % len(component_counts)]
        if count >= median_components + 4 and previous_count <= median_components + 1 and next_count <= median_components + 1:
            count_spike_frames.append(index + 1)
    prop_report = _prop_motion_report(frames, caption_reserved_height)
    one_frame_effects = sorted(set(count_spike_frames + list(prop_report["transient_component_frames"])))
    head_report = _head_shape_report(frames, caption_reserved_height, motion_profile)

    max_rgb_step = max(rgb_steps) if rgb_steps else 0.0
    max_alpha_step = max(alpha_steps) if alpha_steps else 0.0
    max_area_jump = max(area_jumps) if area_jumps else 0.0
    max_center_step = max(center_steps) if center_steps else 0.0
    loop_closure_score = max(loop_delta["rgb"], loop_delta["alpha"])
    motion_energy_score = sum(rgb_steps + alpha_steps) / max(1, len(rgb_steps) + len(alpha_steps))
    max_caption_zone_alpha = max(caption_zone_ratios) if caption_zone_ratios else 0.0
    face_shape_drift_score = float(head_report["face_shape_drift_score"])
    max_head_center_step = float(head_report["max_head_center_step_px"])
    face_limits = FACE_QC_LIMITS[motion_profile]
    template_limits = TEMPLATE_ACTING_LIMITS.get(motion_template, {})
    max_center_step_limit = max(float(limits["max_center_step"]), float(template_limits.get("max_center_step", limits["max_center_step"])))
    max_head_center_step_limit = max(
        float(face_limits["max_head_center_step"]),
        float(template_limits.get("max_head_center_step", face_limits["max_head_center_step"])),
    )
    max_shape_drift_limit = max(
        float(face_limits["max_shape_drift"]),
        float(template_limits.get("max_shape_drift", face_limits["max_shape_drift"])),
    )

    if max_rgb_step > float(limits["max_rgb_step"]):
        errors.append(f"neighbor frame RGB jump is too high: {max_rgb_step:.3f}")
    if max_alpha_step > float(limits["max_alpha_step"]):
        errors.append(f"neighbor frame alpha jump is too high: {max_alpha_step:.3f}")
    if max_area_jump > float(limits["max_area_jump"]):
        errors.append(f"area jump is too high: {max_area_jump:.3f}")
    if max_center_step > max_center_step_limit:
        errors.append(f"frame center step is too high: {max_center_step:.2f}px")
    if loop_closure_score > float(limits["max_loop_closure"]):
        errors.append(f"loop closure jump is too high: {loop_closure_score:.3f}")
    if motion_energy_score < float(limits["min_motion_energy"]):
        errors.append(f"motion energy is too low: {motion_energy_score:.3f}")
    if max_caption_zone_alpha > float(limits["max_caption_zone_alpha"]):
        errors.append(f"subject or effect enters caption zone: {max_caption_zone_alpha:.3f}")
    if one_frame_effects:
        errors.append(f"prop/effect appears for only one frame: {one_frame_effects}")
    if prop_report["prop_lifecycle_errors"]:
        errors.extend(str(error) for error in prop_report["prop_lifecycle_errors"])
    if face_shape_drift_score > max_shape_drift_limit:
        errors.append(f"face/head shape drift is too high: {face_shape_drift_score:.3f}")
    if max_head_center_step > max_head_center_step_limit:
        errors.append(f"head center step is too high: {max_head_center_step:.2f}px")

    status = "fail" if errors else ("warning" if warnings else "pass")
    if status == "warning" and strict and quality_mode == "submission":
        errors.extend(warnings)
        status = "fail"
    return {
        "status": status,
        "warnings": warnings,
        "errors": errors,
        "metrics": {
            "max_rgb_step": round(max_rgb_step, 4),
            "max_alpha_step": round(max_alpha_step, 4),
            "max_area_jump": round(max_area_jump, 4),
            "max_center_step_px": round(max_center_step, 2),
            "max_caption_zone_alpha": round(max_caption_zone_alpha, 4),
            "component_counts": component_counts,
            "transient_component_frames": prop_report["transient_component_frames"],
            "prop_lifecycle_errors": prop_report["prop_lifecycle_errors"],
            "prop_position_jump": prop_report["prop_position_jump"],
            "prop_area_jump": prop_report["prop_area_jump"],
            "prop_counts": prop_report["prop_counts"],
            "face_shape_drift_score": round(face_shape_drift_score, 4),
            "max_head_center_step_px": round(max_head_center_step, 2),
            "caption_reserved_height": caption_reserved_height,
            "motion_template": motion_template,
        },
        "loop_closure_score": round(loop_closure_score, 4),
        "motion_energy_score": round(motion_energy_score, 4),
    }


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
    total_height = caption_text_height(lines, font)
    y = 240 - total_height - CAPTION_BOTTOM_PADDING
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
        if raw.size == WECHAT_SPEC["main"]["size"]:
            frames.append(draw_caption(raw, text, font_path))
        else:
            frames.append(draw_caption(contain(raw, WECHAT_SPEC["main"]["size"], margin=22), text, font_path))
    return frames


def quantize_gif_frame_with_transparency(frame: Image.Image, colors: int) -> Image.Image:
    rgba = frame.convert("RGBA")
    alpha = rgba.getchannel("A")
    matte = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    rgb = Image.alpha_composite(matte, rgba).convert("RGB")
    transparent_mask = alpha.point(lambda value: 255 if value <= 36 else 0)
    rgb.paste((255, 255, 255), mask=transparent_mask)
    palette_colors = max(2, min(255, colors) - 1)
    quantized = rgb.quantize(colors=palette_colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    transparent_data = list(pixel_data(transparent_mask))
    shifted_data = [0 if transparent_data[index] else min(255, value + 1) for index, value in enumerate(pixel_data(quantized))]
    paletted = Image.new("P", rgba.size)
    paletted.putdata(shifted_data)
    palette = [255, 255, 255] + (quantized.getpalette() or [])[: 3 * 255]
    palette.extend([0] * (768 - len(palette)))
    paletted.putpalette(palette[:768])
    paletted.info["transparency"] = 0
    paletted.info["background"] = 0
    return paletted


def gif_duration_for_frame_count(frame_count: int) -> int:
    if frame_count >= 16:
        return 150
    if frame_count >= 12:
        return 125
    if frame_count >= 8:
        return 170
    if frame_count >= 6:
        return 180
    if frame_count >= 4:
        return 190
    return 240


def gif_colors_for_frame_count(frame_count: int) -> int:
    if frame_count >= 16:
        return 128
    if frame_count >= 12:
        return 112
    if frame_count >= 8:
        return 104
    if frame_count >= 6:
        return 88
    if frame_count >= 4:
        return 72
    if frame_count >= 3:
        return 64
    return 48


def gif_attempt_frame_counts(frame_count: int) -> list[int]:
    if frame_count <= 0:
        return []
    candidates = [frame_count, 16, 12, 8, 6, 4, 3, 2]
    seen: set[int] = set()
    attempts: list[int] = []
    for candidate in candidates:
        if 0 < candidate <= frame_count and candidate not in seen:
            seen.add(candidate)
            attempts.append(candidate)
    return attempts


def save_gif_under_limit(frames: list[Image.Image], path: Path, max_bytes: int = 500_000) -> int:
    if not frames:
        raise ValueError(f"Cannot save {path.name}: no frames were provided.")
    attempts = [
        {
            "frames": frames[:attempt_count],
            "duration": gif_duration_for_frame_count(attempt_count),
            "colors": gif_colors_for_frame_count(attempt_count),
        }
        for attempt_count in gif_attempt_frame_counts(len(frames))
    ]
    last_size = 0
    for attempt in attempts:
        palette_frames = [quantize_gif_frame_with_transparency(frame, attempt["colors"]) for frame in attempt["frames"]]
        palette_frames[0].save(
            path,
            save_all=True,
            append_images=palette_frames[1:],
            duration=attempt["duration"],
            loop=0,
            optimize=True,
            disposal=2,
            transparency=0,
            background=0,
        )
        last_size = path.stat().st_size
        if last_size < max_bytes:
            return last_size
    raise ValueError(f"Could not compress {path.name} below {max_bytes} bytes; last size was {last_size}.")


def gif_output_info(path: Path) -> dict[str, int]:
    with Image.open(path) as gif:
        return {
            "gif_frame_count": int(getattr(gif, "n_frames", 1)),
            "gif_duration_ms": int(gif.info.get("duration", 0) or 0),
        }


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


def require_source_images_for_entries(source_dir: Path, image_paths: list[Path], entry_count: int) -> None:
    if len(image_paths) >= entry_count:
        return
    raise ValueError(
        f"{source_dir} contains {len(image_paths)} source image(s) for {entry_count} entries. "
        "Full builds do not reuse source images automatically; use build-preview for first-pass previews "
        "or provide one generated source image per entry."
    )


def remove_light_background(image: Image.Image, threshold: int = 248) -> Image.Image:
    rgba = image.convert("RGBA")
    pixels = []
    source_pixels = pixel_data(rgba)
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
    source_mode: str = DEFAULT_SOURCE_MODE,
    keypose_layout: str = DEFAULT_KEYPOSE_LAYOUT,
    render_frame_count: int = DEFAULT_RENDER_FRAME_COUNT,
    quality_mode: str = "submission",
    strict_qc: bool = True,
    allow_qc_warnings: bool = False,
    strict_continuity_qc: bool = True,
    allow_source_reuse: bool = False,
) -> dict:
    quality_mode = parse_quality_mode(quality_mode)
    source_mode = parse_source_mode(source_mode)
    keypose_layout = parse_keypose_layout(keypose_layout)
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
    if not allow_source_reuse:
        require_source_images_for_entries(source_dir, image_paths, len(entries))
    font_path = find_default_font()
    used_names: set[str] = set()
    manifest_items: list[dict] = []
    cached_sources: list[Image.Image] = []
    qc_reports: list[dict] = []

    for index, entry in enumerate(entries, start=1):
        image_path = image_paths[(index - 1) % len(image_paths)] if allow_source_reuse else image_paths[index - 1]
        motion_profile = motion_profile_for_motion(entry.motion)
        motion_template = motion_template_for_entry(entry)
        alignment_mode = alignment_mode_for_profile(motion_profile)
        caption_reserved_height = caption_reserved_height_for_text(entry.text, font_path)
        read_layout = keypose_layout if source_mode == "keyposes" and source_layout == "auto" else source_layout
        if source_mode == "single_bounce":
            read_layout = "single"
        qc_report = qc_sheet(
            image_path,
            read_layout,
            quality_mode,
            strict=strict_qc,
            motion_profile=motion_profile,
            source_mode=source_mode,
        )
        raw_frames, animation_source, detected_layout = load_source_frames(image_path, read_layout)
        raw = raw_frames[0]
        cached_sources.append(raw)
        preview_only = False
        normalization_meta: dict[str, object] = {"scale_normalized": False}
        continuity_report: dict[str, object] = {
            "status": "pass",
            "warnings": [],
            "errors": [],
            "metrics": {},
            "loop_closure_score": 0.0,
            "motion_energy_score": 0.0,
        }
        if qc_report["status"] == "fail" and strict_qc:
            errors = "; ".join(qc_report["errors"])
            raise ValueError(f"{image_path.name} failed QC: {errors}")
        if qc_report["status"] == "warning" and strict_qc and not allow_qc_warnings:
            warnings = "; ".join(qc_report["warnings"])
            raise ValueError(f"{image_path.name} has QC warnings: {warnings}")
        if source_mode == "keyposes":
            normalized_frames, normalization_meta = render_keypose_motion(
                raw_frames,
                motion_template=motion_template,
                frame_count=render_frame_count,
                motion_profile=motion_profile,
                caption_reserved_height=caption_reserved_height,
            )
            animation_source = "keyposes"
            continuity_report = continuity_qc(
                normalized_frames,
                quality_mode,
                motion_profile,
                motion_template,
                strict=strict_continuity_qc,
                caption_reserved_height=caption_reserved_height,
            )
            if continuity_report["status"] == "fail" and strict_continuity_qc:
                errors = "; ".join(str(error) for error in continuity_report["errors"])
                raise ValueError(f"{image_path.name} failed continuity QC: {errors}")
            if continuity_report["status"] == "warning" and strict_continuity_qc and not allow_qc_warnings:
                warnings = "; ".join(str(warning) for warning in continuity_report["warnings"])
                raise ValueError(f"{image_path.name} has continuity warnings: {warnings}")
            frames = caption_source_frames(normalized_frames, entry.text, font_path)
        elif source_mode == "motion_sheet" and len(raw_frames) > 1:
            normalized_frames, normalization_meta = normalize_motion_frames(
                raw_frames,
                caption_reserved_height=caption_reserved_height,
                alignment_mode=alignment_mode,
            )
            continuity_report = continuity_qc(
                normalized_frames,
                quality_mode,
                motion_profile,
                motion_template,
                strict=strict_continuity_qc,
                caption_reserved_height=caption_reserved_height,
            )
            if continuity_report["status"] == "fail" and strict_continuity_qc:
                errors = "; ".join(str(error) for error in continuity_report["errors"])
                raise ValueError(f"{image_path.name} failed continuity QC: {errors}")
            if continuity_report["status"] == "warning" and strict_continuity_qc and not allow_qc_warnings:
                warnings = "; ".join(str(warning) for warning in continuity_report["warnings"])
                raise ValueError(f"{image_path.name} has continuity warnings: {warnings}")
            frames = caption_source_frames(normalized_frames, entry.text, font_path)
        else:
            preview_only = True
            if mode == "wechat" and quality_mode == "submission" and strict_qc:
                raise ValueError("single_bounce sources are preview-only; use 2x4 motion sheets for WeChat submission.")
            base = contain(raw, WECHAT_SPEC["main"]["size"], margin=22)
            frames = animated_frames(base, entry.text, font_path)
            animation_source = "single_bounce"

        named_slug = ensure_unique_name(entry.name, used_names)
        named_gif = named_dir / f"{named_slug}.gif"
        numbered_gif = main_dir / f"{index:02d}.gif"
        gif_size = save_gif_under_limit(frames, numbered_gif, WECHAT_SPEC["main"]["max_bytes"])
        gif_info = gif_output_info(numbered_gif)
        shutil.copyfile(numbered_gif, named_gif)

        thumb = make_thumbnail(raw, WECHAT_SPEC["thumb"]["size"])
        thumb_path = thumbs_dir / f"{index:02d}.png"
        thumb_size = save_png_under_limit(thumb, thumb_path, WECHAT_SPEC["thumb"]["max_bytes"])

        qc_item = {
            "index": index,
            "source": str(image_path),
            "qc_status": qc_report["status"],
            "qc_warnings": qc_report["warnings"],
            "qc_errors": qc_report["errors"],
            "background_mode": qc_report["background_mode"],
            "edge_touch": qc_report["edge_touch"],
            "bbox_drift": qc_report["bbox_drift"],
            "scale_normalized": bool(normalization_meta.get("scale_normalized", False)),
            "preview_only": preview_only,
            "continuity_qc_status": continuity_report["status"],
            "continuity_warnings": continuity_report["warnings"],
            "continuity_errors": continuity_report["errors"],
            "continuity_metrics": continuity_report["metrics"],
            "loop_closure_score": continuity_report["loop_closure_score"],
            "motion_energy_score": continuity_report["motion_energy_score"],
            "prop_lifecycle_errors": continuity_report["metrics"].get("prop_lifecycle_errors", []),
            "prop_position_jump": continuity_report["metrics"].get("prop_position_jump", 0.0),
            "prop_area_jump": continuity_report["metrics"].get("prop_area_jump", 0.0),
            "face_shape_drift_score": continuity_report["metrics"].get("face_shape_drift_score", 0.0),
            "max_head_center_step_px": continuity_report["metrics"].get("max_head_center_step_px", 0.0),
        }
        qc_reports.append({**qc_report, "continuity": continuity_report, "index": index, "name": entry.name})
        manifest_items.append(
            {
                "index": index,
                "name": entry.name,
                "text": entry.text,
                "keyword": entry.keyword,
                "scene": entry.scene,
                "motion": entry.motion,
                "motion_profile": motion_profile,
                "source_mode": source_mode,
                "motion_template": motion_template,
                "alignment_mode": alignment_mode,
                "source": str(image_path),
                "animation_source": animation_source,
                "source_layout": detected_layout,
                "source_frame_count": len(raw_frames),
                "rendered_frame_count": len(frames),
                "caption_reserved_height": caption_reserved_height,
                "wechat_gif": relative_to_output(numbered_gif, output_dir),
                "named_gif": relative_to_output(named_gif, output_dir),
                "thumbnail": relative_to_output(thumb_path, output_dir),
                "gif_bytes": gif_size,
                **gif_info,
                "thumb_bytes": thumb_size,
                **qc_item,
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
        "quality_mode": quality_mode,
        "source_mode": source_mode,
        "keypose_layout": keypose_layout,
        "render_frame_count": render_frame_count,
        "strict_qc": strict_qc,
        "strict_continuity_qc": strict_continuity_qc,
        "allow_qc_warnings": allow_qc_warnings,
        "wechat": {key: {"size": list(value["size"]), "max_bytes": value["max_bytes"], "format": value["format"]} for key, value in WECHAT_SPEC.items()},
        "assets": {
            "cover": {"path": relative_to_output(cover_path, output_dir), "bytes": cover_size},
            "icon": {"path": relative_to_output(icon_path, output_dir), "bytes": icon_size},
            "banner": {"path": relative_to_output(banner_path, output_dir), "bytes": banner_size},
        },
        "items": manifest_items,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "qc_report.json").write_text(
        json.dumps(
            {
                "pack_name": pack_name,
                "quality_mode": quality_mode,
                "strict_qc": strict_qc,
                "status": "fail"
                if any(
                    report["status"] == "fail" or report.get("continuity", {}).get("status") == "fail"
                    for report in qc_reports
                )
                else "pass",
                "items": qc_reports,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    with (output_dir / "manifest.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "index",
                "name",
                "keyword",
                "text",
                "scene",
                "motion_profile",
                "source_mode",
                "motion_template",
                "alignment_mode",
                "animation_source",
                "source_layout",
                "source_frame_count",
                "rendered_frame_count",
                "caption_reserved_height",
                "wechat_gif",
                "named_gif",
                "thumbnail",
                "gif_bytes",
                "gif_frame_count",
                "gif_duration_ms",
                "thumb_bytes",
                "qc_status",
                "qc_warnings",
                "qc_errors",
                "background_mode",
                "edge_touch",
                "bbox_drift",
                "scale_normalized",
                "preview_only",
                "continuity_qc_status",
                "continuity_warnings",
                "continuity_errors",
                "continuity_metrics",
                "loop_closure_score",
                "motion_energy_score",
                "prop_lifecycle_errors",
                "prop_position_jump",
                "prop_area_jump",
                "face_shape_drift_score",
                "max_head_center_step_px",
            ],
        )
        writer.writeheader()
        for item in manifest_items:
            row = {field: item[field] for field in writer.fieldnames}
            for key in (
                "qc_warnings",
                "qc_errors",
                "bbox_drift",
                "continuity_warnings",
                "continuity_errors",
                "continuity_metrics",
                "prop_lifecycle_errors",
            ):
                row[key] = json.dumps(row[key], ensure_ascii=False)
            writer.writerow(row)
    return manifest


def write_preview_html(output_dir: Path, manifest: dict) -> Path:
    rows: list[str] = []
    for item in manifest.get("items", []):
        gif_src = html_lib.escape(str(item["named_gif"]), quote=True)
        name = html_lib.escape(str(item["name"]))
        text = html_lib.escape(str(item["text"]).replace("\n", " / "))
        scene = html_lib.escape(str(item.get("scene", "")))
        status = html_lib.escape(str(item.get("continuity_qc_status", item.get("qc_status", ""))))
        rows.append(
            "      <figure>\n"
            f"        <img src=\"{gif_src}\" alt=\"{name}\" width=\"240\" height=\"240\" />\n"
            f"        <figcaption><strong>{name}</strong><span>{text}</span><small>{scene} · QC {status}</small></figcaption>\n"
            "      </figure>"
        )
    pack_name = html_lib.escape(str(manifest.get("pack_name", "Meme Preview")))
    persona = html_lib.escape(str(manifest.get("persona", "")))
    style = html_lib.escape(str(manifest.get("style", "")))
    quality_mode = html_lib.escape(str(manifest.get("quality_mode", "")))
    html = f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{pack_name} Preview</title>
    <style>
      :root {{
        color-scheme: light;
        --ink: #202124;
        --muted: #5f6368;
        --line: #dadce0;
        --bg: #f8fafd;
      }}
      body {{
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", sans-serif;
        color: var(--ink);
        background: var(--bg);
      }}
      main {{
        max-width: 940px;
        margin: 0 auto;
        padding: 28px 18px 40px;
      }}
      h1 {{
        margin: 0 0 8px;
        font-size: 28px;
        line-height: 1.25;
      }}
      .meta {{
        color: var(--muted);
        margin: 0 0 24px;
      }}
      .grid {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
        gap: 18px;
        align-items: start;
      }}
      figure {{
        margin: 0;
        background: #fff;
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 12px;
      }}
      img {{
        display: block;
        width: 240px;
        height: 240px;
        margin: 0 auto;
        background: #2f3437;
      }}
      figcaption {{
        display: grid;
        gap: 4px;
        margin-top: 10px;
        text-align: center;
      }}
      figcaption span,
      figcaption small {{
        color: var(--muted);
      }}
      figcaption small {{
        font-size: 12px;
      }}
    </style>
  </head>
  <body>
    <main>
      <h1>{pack_name}</h1>
      <p class="meta">Preview build · {len(manifest.get("items", []))} GIFs · {persona} · {style} · {quality_mode}</p>
      <section class="grid">
{chr(10).join(rows)}
      </section>
    </main>
  </body>
</html>
"""
    path = output_dir / "preview.html"
    path.write_text(html, encoding="utf-8")
    return path


def build_preview(
    source_dir: Path,
    output_dir: Path,
    entries: list[MemeEntry],
    mode: str = "preview",
    pack_name: str = "Agent Meme Preview",
    style: str = "clean-sticker",
    persona: str = "科研打工人",
    author: str = "Agent Meme Forge",
    source_layout: str = "auto",
    source_mode: str = DEFAULT_SOURCE_MODE,
    keypose_layout: str = DEFAULT_KEYPOSE_LAYOUT,
    render_frame_count: int = DEFAULT_RENDER_FRAME_COUNT,
    quality_mode: str = "submission",
    strict_qc: bool = True,
    allow_qc_warnings: bool = False,
    strict_continuity_qc: bool = True,
    preview_count: int = 3,
) -> dict:
    if preview_count <= 0:
        raise ValueError("preview_count must be positive.")
    if len(entries) < preview_count:
        raise ValueError(f"preview_count {preview_count} exceeds entry count {len(entries)}.")
    image_paths = source_images(source_dir)
    if len(image_paths) < preview_count:
        raise ValueError(f"preview_count {preview_count} requires {preview_count} source images; found {len(image_paths)}.")
    manifest = build_pack(
        source_dir=source_dir,
        output_dir=output_dir,
        entries=entries[:preview_count],
        mode=mode,
        pack_name=pack_name,
        style=style,
        persona=persona,
        author=author,
        source_layout=source_layout,
        source_mode=source_mode,
        keypose_layout=keypose_layout,
        render_frame_count=render_frame_count,
        quality_mode=quality_mode,
        strict_qc=strict_qc,
        allow_qc_warnings=allow_qc_warnings,
        strict_continuity_qc=strict_continuity_qc,
        allow_source_reuse=False,
    )
    write_preview_html(output_dir, manifest)
    return manifest


def write_default_entries(path: Path, persona: str, pack_size: int) -> None:
    entries = [asdict(entry) for entry in default_entries(persona, pack_size)]
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def write_plan(path: Path, plan: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")


def accept_generated_image(plan_path: Path, index: int, image_path: Path, source_dir: Path | None = None) -> dict:
    if index < 1:
        raise ValueError("--index must be 1-based and greater than 0.")
    if not plan_path.exists():
        raise ValueError(f"Plan JSON not found: {plan_path}")
    if not image_path.exists():
        raise ValueError(f"Generated image not found: {image_path}")

    try:
        with Image.open(image_path) as image:
            image.verify()
    except OSError as exc:
        raise ValueError(f"Generated image is not a readable image: {image_path}") from exc

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    prompts = plan.get("image_prompts") or []
    if index > len(prompts):
        raise ValueError(f"--index {index} is outside the plan image_prompts range 1..{len(prompts)}.")
    prompt = prompts[index - 1]
    raw_filename = prompt.get("raw_image_filename")
    if not raw_filename:
        name = prompt.get("name") or prompt.get("meme_name") or "meme"
        layout = prompt.get("animation_layout") or plan.get("animation", {}).get("source_layout") or DEFAULT_ANIMATION_LAYOUT
        raw_filename = f"{index:02d}-{slug_filename(name)}-{layout}.png"

    target_dir = source_dir or Path(plan.get("raw_output_dir") or "output/raw-frames")
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / raw_filename
    if image_path.resolve() != target.resolve():
        shutil.copyfile(image_path, target)

    record = {
        "index": index,
        "name": prompt.get("name") or prompt.get("meme_name") or "",
        "source_image": str(image_path),
        "saved_image": str(target),
        "raw_image_filename": raw_filename,
        "prompt_name": prompt.get("meme_name") or prompt.get("name") or "",
    }
    index_path = target_dir / "generated-index.json"
    if index_path.exists():
        try:
            handoff = json.loads(index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            handoff = {}
    else:
        handoff = {}
    items = [item for item in handoff.get("items", []) if item.get("index") != index]
    items.append(record)
    handoff.update(
        {
            "plan": str(plan_path),
            "source_dir": str(target_dir),
            "items": sorted(items, key=lambda item: item["index"]),
        }
    )
    index_path.write_text(json.dumps(handoff, ensure_ascii=False, indent=2), encoding="utf-8")
    record["handoff_index"] = str(index_path)
    return record


def imagegen_batch_jobs(plan: dict, limit: int | None = None) -> list[dict]:
    jobs: list[dict] = []
    prompts = plan.get("image_prompts") or []
    for prompt in prompts[:limit]:
        raw_filename = prompt.get("raw_image_filename")
        text = prompt.get("prompt")
        if not raw_filename:
            raise ValueError("Every image_prompt must include raw_image_filename for generate-raw-batch.")
        if not text:
            raise ValueError(f"{raw_filename} is missing prompt text.")
        jobs.append({"prompt": text, "out": raw_filename})
    if not jobs:
        raise ValueError("Plan contains no image_prompts.")
    return jobs


def write_imagegen_batch_jsonl(path: Path, jobs: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(job, ensure_ascii=False) for job in jobs) + "\n", encoding="utf-8")


def generate_raw_batch(
    plan_path: Path,
    provider: str = IMAGE_PROVIDER_OPENAI_IMAGES_API,
    imagegen_cli: Path | None = None,
    source_dir: Path | None = None,
    limit: int | None = None,
    model: str = "gpt-image-2",
    quality: str = "medium",
    size: str = "1024x1024",
    output_format: str = "png",
    background: str = "opaque",
    concurrency: int = 3,
    max_attempts: int = 2,
    force: bool = False,
    dry_run: bool = False,
) -> dict:
    provider = parse_image_provider(provider)
    if provider != IMAGE_PROVIDER_OPENAI_IMAGES_API:
        raise ValueError("generate-raw-batch currently supports --provider openai_images_api.")
    if not plan_path.exists():
        raise ValueError(f"Plan JSON not found: {plan_path}")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    raw_dir = source_dir or Path(plan.get("raw_output_dir") or "output/raw-frames")
    raw_dir.mkdir(parents=True, exist_ok=True)
    jobs = imagegen_batch_jobs(plan, limit=limit)
    jobs_path = raw_dir / "_imagegen-batch.jsonl"
    write_imagegen_batch_jsonl(jobs_path, jobs)
    cli = imagegen_cli or default_imagegen_cli_path()
    if not cli.exists():
        raise ValueError(f"image_gen.py CLI not found: {cli}")

    command = [
        sys.executable,
        str(cli),
        "generate-batch",
        "--input",
        str(jobs_path),
        "--out-dir",
        str(raw_dir),
        "--model",
        model,
        "--quality",
        quality,
        "--size",
        size,
        "--output-format",
        output_format,
        "--background",
        background,
        "--concurrency",
        str(concurrency),
        "--max-attempts",
        str(max_attempts),
    ]
    if force:
        command.append("--force")
    if dry_run:
        command.append("--dry-run")
    subprocess.run(command, check=True)

    accepted: list[dict] = []
    if not dry_run:
        for index, job in enumerate(jobs, start=1):
            generated = raw_dir / job["out"]
            accepted.append(accept_generated_image(plan_path, index, generated, raw_dir))
    return {
        "provider": provider,
        "plan": str(plan_path),
        "source_dir": str(raw_dir),
        "jobs": len(jobs),
        "jobs_jsonl": str(jobs_path),
        "dry_run": dry_run,
        "accepted": accepted,
        "command": command,
    }


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
                "quality_modes": sorted(QUALITY_MODES),
                "handoff_commands": ["plan-pack", "accept-generated", "qc-sheet", "build-preview", "build-pack"],
                "wechat_pack_sizes": [16, 24],
                "self_use_pack_sizes": [18],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def _prompt_text(
    label: str,
    default: str = "",
    required: bool = False,
    input_fn=input,
) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        value = input_fn(f"{label}{suffix}: ").strip()
        if value:
            return value
        if default:
            return default
        if not required:
            return ""
        print("This field is required.", file=sys.stderr)


def _prompt_choice(
    label: str,
    options: list[str],
    default_index: int = 0,
    input_fn=input,
    print_fn=print,
) -> str:
    print_fn(label)
    for index, option in enumerate(options, start=1):
        marker = " (default)" if index - 1 == default_index else ""
        print_fn(f"  {index}. {option}{marker}")
    while True:
        raw = input_fn(f"Choose 1-{len(options)} [{default_index + 1}]: ").strip()
        if not raw:
            return options[default_index]
        if raw in options:
            return raw
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print_fn(f"Invalid choice: {raw}")


def run_plan_wizard(input_fn=input, print_fn=print) -> dict:
    print_fn("Agent Meme Forge interactive plan wizard")
    print_fn("This wizard writes the plan JSON. Codex built-in image_gen is a terminal action, so accept/QC resumes in the next turn after a local image file is available.")
    print_fn("前三张只是质量闸门，不是交付终点；内置 image_gen 不能同一轮串联后处理，下一轮拿到本地文件后继续 accept/QC/build。")
    input_mode = _prompt_choice(
        "Step 1: choose the character source",
        ["text_concept", "reference_image"],
        default_index=0,
        input_fn=input_fn,
        print_fn=print_fn,
    )
    reference_image: str | None = None
    if input_mode == "reference_image":
        reference_image = _prompt_text("Reference image path or uploaded-image label", required=True, input_fn=input_fn)
        subject = _prompt_text(
            "Describe key traits to preserve",
            default="preserve the uploaded character",
            input_fn=input_fn,
        )
    else:
        subject = _prompt_text(
            "Describe the original character or mascot",
            default="warm geometric AI assistant mascot with cream body and coral accents, original character, no official logo",
            required=True,
            input_fn=input_fn,
        )

    persona = _prompt_choice(
        "Step 2: choose scene/persona",
        list(PERSONA_ENTRIES),
        default_index=0,
        input_fn=input_fn,
        print_fn=print_fn,
    )
    style = _prompt_choice(
        "Step 3: choose visual style",
        list(STYLE_PROMPTS),
        default_index=0,
        input_fn=input_fn,
        print_fn=print_fn,
    )
    mode = _prompt_choice(
        "Step 4: choose output mode",
        ["wechat", "self_use"],
        default_index=0,
        input_fn=input_fn,
        print_fn=print_fn,
    )
    if mode == "wechat":
        pack_size = int(_prompt_choice("Step 5: choose WeChat pack size", ["24", "16"], 0, input_fn, print_fn))
    else:
        pack_size = int(_prompt_text("Step 5: self-use sticker count", default="18", input_fn=input_fn))

    quality_mode = _prompt_choice(
        "Step 6: choose quality mode",
        ["submission", "standard", "preview"],
        default_index=0,
        input_fn=input_fn,
        print_fn=print_fn,
    )
    image_provider = _prompt_choice(
        "Step 7: choose image provider",
        [DEFAULT_IMAGE_PROVIDER, IMAGE_PROVIDER_OPENAI_IMAGES_API, IMAGE_PROVIDER_EXTERNAL_FILES, IMAGE_PROVIDER_AI_STUDIO_HERMES],
        default_index=0,
        input_fn=input_fn,
        print_fn=print_fn,
    )
    selected_layout = _prompt_choice(
        "Step 8: choose source layout (2x2/1x4 keyposes, 2x4/4x4 legacy motion sheets)",
        [DEFAULT_KEYPOSE_LAYOUT, "1x4", DEFAULT_ANIMATION_LAYOUT, "4x4", "1x8", "2x3"],
        default_index=0,
        input_fn=input_fn,
        print_fn=print_fn,
    )
    source_mode = "keyposes" if selected_layout in KEYPOSE_LAYOUTS else "motion_sheet"
    keypose_layout = selected_layout if source_mode == "keyposes" else DEFAULT_KEYPOSE_LAYOUT
    animation_layout = DEFAULT_ANIMATION_LAYOUT if source_mode == "keyposes" else selected_layout

    pack_name = _prompt_text("Step 9: pack name", default="Agent Meme Pack", input_fn=input_fn)
    tone = _prompt_text("Step 10: humor tone", default="职场发疯但安全", input_fn=input_fn)
    output = Path(_prompt_text("Step 11: output plan JSON path", default="output/meme-plan.json", input_fn=input_fn))
    plan = plan_pack(
        subject=subject,
        persona=persona,
        style=style,
        pack_size=pack_size,
        mode=mode,
        tone=tone,
        reference_image=reference_image,
        pack_name=pack_name,
        animation_layout=animation_layout,
        quality_mode=quality_mode,
        source_mode=source_mode,
        keypose_layout=keypose_layout,
        image_provider=image_provider,
    )
    write_plan(output, plan)
    print_fn(f"Plan written: {output}")
    print_fn("Next: 先生成前 3 张作为质量闸门；对内置 image_gen，先把下一张 keypose prompt 作为本轮最终动作生成；下一轮保存/导出本地文件后再运行 accept-generated、qc-sheet 和 preview/build。")
    print_fn(plan["image_handoff"]["accept_generated_command"])
    print_fn(plan["processor_command"])
    return plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build WeChat-ready animated meme GIF packs.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-options", help="Print supported personas and pack sizes.")

    sub.add_parser("plan-wizard", help="Interactively choose image source, scene/persona, style, pack size, and quality mode.")

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
    plan_parser.add_argument("--source-mode", default=DEFAULT_SOURCE_MODE, choices=sorted(SOURCE_MODES))
    plan_parser.add_argument("--keypose-layout", default=DEFAULT_KEYPOSE_LAYOUT, choices=sorted(KEYPOSE_LAYOUTS))
    plan_parser.add_argument("--render-frame-count", type=int, default=DEFAULT_RENDER_FRAME_COUNT)
    plan_parser.add_argument("--quality-mode", default="submission", choices=sorted(QUALITY_MODES))
    plan_parser.add_argument("--image-provider", default=DEFAULT_IMAGE_PROVIDER, choices=sorted(IMAGE_PROVIDERS))
    plan_parser.add_argument("--output", required=True, type=Path)

    accept_parser = sub.add_parser("accept-generated", help="Persist an image_gen result under the planned raw filename.")
    accept_parser.add_argument("--plan", required=True, type=Path, help="Plan JSON written by plan-pack or plan-wizard.")
    accept_parser.add_argument("--index", required=True, type=int, help="1-based sticker index from image_prompts.")
    accept_parser.add_argument("--image", required=True, type=Path, help="Local image file exported from image_gen.")
    accept_parser.add_argument(
        "--source-dir",
        type=Path,
        help="Raw frame directory. Defaults to raw_output_dir from the plan JSON.",
    )

    batch_parser = sub.add_parser("generate-raw-batch", help="Generate planned raw keypose PNGs with a scriptable image provider.")
    batch_parser.add_argument("--plan", required=True, type=Path, help="Plan JSON written by plan-pack or plan-wizard.")
    batch_parser.add_argument("--provider", default=IMAGE_PROVIDER_OPENAI_IMAGES_API, choices=[IMAGE_PROVIDER_OPENAI_IMAGES_API])
    batch_parser.add_argument("--imagegen-cli", type=Path, help="Path to the system imagegen scripts/image_gen.py CLI.")
    batch_parser.add_argument("--source-dir", type=Path, help="Raw frame directory. Defaults to raw_output_dir from the plan JSON.")
    batch_parser.add_argument("--limit", type=int, help="Generate only the first N image prompts.")
    batch_parser.add_argument("--model", default="gpt-image-2")
    batch_parser.add_argument("--quality", default="medium")
    batch_parser.add_argument("--size", default="1024x1024")
    batch_parser.add_argument("--output-format", default="png")
    batch_parser.add_argument("--background", default="opaque")
    batch_parser.add_argument("--concurrency", type=int, default=3)
    batch_parser.add_argument("--max-attempts", type=int, default=2)
    batch_parser.add_argument("--force", action="store_true")
    batch_parser.add_argument("--dry-run", action="store_true")

    qc_parser = sub.add_parser("qc-sheet", help="Inspect a raw motion sheet before building a WeChat pack.")
    qc_parser.add_argument("--input", required=True, type=Path)
    qc_parser.add_argument("--source-layout", default="auto")
    qc_parser.add_argument("--source-mode", default="motion_sheet", choices=sorted(SOURCE_MODES))
    qc_parser.add_argument("--quality-mode", default="submission", choices=sorted(QUALITY_MODES))
    qc_parser.add_argument("--motion-profile", default="standard", choices=sorted(MOTION_PROFILES))
    qc_parser.add_argument("--output", type=Path)
    qc_parser.add_argument("--allow-warnings", action="store_true")
    qc_parser.add_argument("--no-strict", dest="strict", action="store_false", default=True)

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
    build_parser.add_argument("--source-mode", default=DEFAULT_SOURCE_MODE, choices=sorted(SOURCE_MODES))
    build_parser.add_argument("--keypose-layout", default=DEFAULT_KEYPOSE_LAYOUT, choices=sorted(KEYPOSE_LAYOUTS))
    build_parser.add_argument("--render-frame-count", type=int, default=DEFAULT_RENDER_FRAME_COUNT)
    build_parser.add_argument("--quality-mode", default="submission", choices=sorted(QUALITY_MODES))
    build_parser.add_argument("--strict-qc", dest="strict_qc", action="store_true", default=True)
    build_parser.add_argument("--no-strict-qc", dest="strict_qc", action="store_false")
    build_parser.add_argument("--strict-continuity-qc", dest="strict_continuity_qc", action="store_true", default=True)
    build_parser.add_argument("--no-strict-continuity-qc", dest="strict_continuity_qc", action="store_false")
    build_parser.add_argument("--allow-qc-warnings", action="store_true")

    preview_parser = sub.add_parser("build-preview", help="Build an explicit small preview from the first generated raw sheets.")
    preview_parser.add_argument("--source-dir", required=True, type=Path)
    preview_parser.add_argument("--output-dir", required=True, type=Path)
    preview_parser.add_argument("--entries", type=Path)
    preview_parser.add_argument("--pack-name", default="Agent Meme Preview")
    preview_parser.add_argument("--style", default="clean-sticker")
    preview_parser.add_argument("--persona", default="科研打工人")
    preview_parser.add_argument("--author", default="Agent Meme Forge")
    preview_parser.add_argument("--preview-count", type=int, default=3)
    preview_parser.add_argument("--source-layout", default="auto")
    preview_parser.add_argument("--source-mode", default=DEFAULT_SOURCE_MODE, choices=sorted(SOURCE_MODES))
    preview_parser.add_argument("--keypose-layout", default=DEFAULT_KEYPOSE_LAYOUT, choices=sorted(KEYPOSE_LAYOUTS))
    preview_parser.add_argument("--render-frame-count", type=int, default=DEFAULT_RENDER_FRAME_COUNT)
    preview_parser.add_argument("--quality-mode", default="submission", choices=sorted(QUALITY_MODES))
    preview_parser.add_argument("--strict-qc", dest="strict_qc", action="store_true", default=True)
    preview_parser.add_argument("--no-strict-qc", dest="strict_qc", action="store_false")
    preview_parser.add_argument("--strict-continuity-qc", dest="strict_continuity_qc", action="store_true", default=True)
    preview_parser.add_argument("--no-strict-continuity-qc", dest="strict_continuity_qc", action="store_false")
    preview_parser.add_argument("--allow-qc-warnings", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "list-options":
        cmd_list_options()
        return 0
    if args.command == "plan-wizard":
        try:
            run_plan_wizard()
            return 0
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
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
                quality_mode=args.quality_mode,
                source_mode=args.source_mode,
                keypose_layout=args.keypose_layout,
                render_frame_count=args.render_frame_count,
                image_provider=args.image_provider,
            )
            write_plan(args.output, plan)
            return 0
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    if args.command == "accept-generated":
        try:
            record = accept_generated_image(args.plan, args.index, args.image, args.source_dir)
            print(json.dumps(record, ensure_ascii=False, indent=2))
            return 0
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    if args.command == "generate-raw-batch":
        try:
            record = generate_raw_batch(
                plan_path=args.plan,
                provider=args.provider,
                imagegen_cli=args.imagegen_cli,
                source_dir=args.source_dir,
                limit=args.limit,
                model=args.model,
                quality=args.quality,
                size=args.size,
                output_format=args.output_format,
                background=args.background,
                concurrency=args.concurrency,
                max_attempts=args.max_attempts,
                force=args.force,
                dry_run=args.dry_run,
            )
            print(json.dumps(record, ensure_ascii=False, indent=2))
            return 0
        except (ValueError, subprocess.CalledProcessError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    if args.command == "qc-sheet":
        try:
            report = qc_sheet(
                args.input,
                args.source_layout,
                args.quality_mode,
                strict=args.strict,
                motion_profile=args.motion_profile,
                source_mode=args.source_mode,
            )
            if args.output:
                write_qc_report(args.output, report)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            if report["status"] == "fail":
                return 2
            if report["status"] == "warning" and not args.allow_warnings:
                return 1
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
                args.source_mode,
                args.keypose_layout,
                args.render_frame_count,
                args.quality_mode,
                args.strict_qc,
                args.allow_qc_warnings,
                args.strict_continuity_qc,
            )
            return 0
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    if args.command == "build-preview":
        try:
            entries = load_entries(args.entries) if args.entries else default_entries(args.persona, max(24, args.preview_count))
            manifest = build_preview(
                args.source_dir,
                args.output_dir,
                entries,
                "preview",
                args.pack_name,
                args.style,
                args.persona,
                args.author,
                args.source_layout,
                args.source_mode,
                args.keypose_layout,
                args.render_frame_count,
                args.quality_mode,
                args.strict_qc,
                args.allow_qc_warnings,
                args.strict_continuity_qc,
                args.preview_count,
            )
            print(
                json.dumps(
                    {
                        "pack_size": manifest["pack_size"],
                        "preview_html": str(args.output_dir / "preview.html"),
                        "named_gifs": str(args.output_dir / "named-gifs"),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
