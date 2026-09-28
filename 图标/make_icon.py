# -*- coding: utf-8 -*-
"""PKPM2PDMS v2.1.0 —— 插件图标生成脚本（可复现）。

设计目标
--------
**深蓝底 + 白色门式刚架 + 白色右向箭头**，16 px 也要能辨认。
"门式刚架"= 两根竖柱 + 一根横梁（Π 形，像汉字「门」），柱脚略外扩；
右侧一个右向箭头（矩形杆 + 三角头），表示"转换 / 导出"。

可辨性依据（都在 ``GEOM`` 里，可核对）
--------------------------------------
* 所有前景笔画宽度 ≥ 图标边长的 **12 %**（要求 ≥ 8 %）：
  竖柱 0.120、横梁 0.135、柱脚 0.075(高)、箭头杆 0.130、箭头三角(高/宽) 0.340/0.165。
  16 px 下分别是 1.92 / 2.16 / 1.20 / 2.08 / 5.44 / 2.64 像素 —— 最细的柱脚也有 1.2 px，
  其余都 ≥ 1.9 px，配合 8× 超采样 + LANCZOS 缩小时轮廓不会糊掉。
* 颜色对比：白 (#FFFFFF) 对底 (#1F4E79~#2E75B6) 的亮度比 ≈ 8:1 以上，纯色块不需要描边。
* 前景被拆成"互不重叠的大色块"（不是细线），缩小后仍是实心形状。

用法
----
::

    python make_icon.py                    # 写到脚本同目录
    python make_icon.py --out-dir <目录>    # 指定输出目录
    python make_icon.py --quiet            # 只打印自检结果

产出
----
* ``pkpm2pdms.ico``        多尺寸 16/24/32/48/64/128/256（**经典 BMP/DIB 帧**，
                           兼容 csc /win32icon 等老工具 —— 见 :func:`generate` 里的说明）
* ``pkpm2pdms_256.png``    256 px 单张
* ``小尺寸预览.png``        16/24/32/48/64 并排放大，上排最近邻（真实像素）+ 下排平滑（实际观感）

依赖：Pillow（本机 12.3.0 实测）。只用公开 API，无随机数、无时间戳 —— 同样输入必得同样输出。
"""

from __future__ import annotations

import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- 设计常量（唯一真源）

#: 背景渐变（纵向：上 → 下）
COLOR_TOP = (0x1F, 0x4E, 0x79)      # #1F4E79 深蓝
COLOR_BOTTOM = (0x2E, 0x75, 0xB6)   # #2E75B6 中蓝
COLOR_FG = (0xFF, 0xFF, 0xFF)       # 前景纯白
COLOR_SHEET_BG = (0xFF, 0xFF, 0xFF)  # 预览图纸底
COLOR_CELL_BG = (0xDC, 0xE6, 0xF1)   # 预览单元格底（让圆角外的透明看得见）
COLOR_TEXT = (0x20, 0x20, 0x20)
COLOR_TEXT_DIM = (0x60, 0x60, 0x60)

#: 圆角方形背景的圆角半径（占边长比例）
CORNER_RADIUS = 0.17

#: 前景几何（全部按 0..1 归一化，原点左上、y 向下）
GEOM = {
    # 横梁：x0, y0, x1, y1
    "beam":   (0.105, 0.245, 0.475, 0.380),
    "col_l":  (0.105, 0.245, 0.225, 0.780),
    "col_r":  (0.355, 0.245, 0.475, 0.780),
    # 柱脚：向外多出 0.045（"略外扩"）；高度 0.095 保证 ≥ 8% 线宽
    "foot_l": (0.060, 0.685, 0.225, 0.780),
    "foot_r": (0.355, 0.685, 0.520, 0.780),
    # 箭头杆
    "shaft":  (0.605, 0.455, 0.795, 0.585),
}

#: 箭头三角头三个顶点（与箭头杆有 0.030 重叠，避免出现接缝）
ARROW_HEAD = ((0.765, 0.350), (0.930, 0.520), (0.765, 0.690))

#: ico 内的尺寸（顺序无关，Pillow 会排序后逐个写入）
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)

#: 超采样倍率（先画大图再 LANCZOS 缩小 —— 抗锯齿）
SUPERSAMPLE = 8

#: 小尺寸预览：显示高度（要能被 16/24/32/48/64 整除，取 192 = 12×16 = 8×24 = 6×32 = 4×48 = 3×64）
PREVIEW_HEIGHT = 192
PREVIEW_SIZES = (16, 24, 32, 48, 64)

#: 笔画宽度下限（占边长比例）—— 用于自检断言
MIN_STROKE_RATIO = 0.08


# ---------------------------------------------------------------- 绘制

def _gradient_column(size: int) -> Image.Image:
    """竖向渐变的 1×size 列图（再横拉成方图；纯 Python 循环，size ≤ 2048 时耗时毫秒级）。"""
    col = Image.new("RGB", (1, size))
    px = col.load()
    span = max(size - 1, 1)
    for y in range(size):
        t = y / span
        px[0, y] = tuple(
            int(round(COLOR_TOP[i] + (COLOR_BOTTOM[i] - COLOR_TOP[i]) * t)) for i in range(3)
        )
    return col


def render(size: int, supersample: int = SUPERSAMPLE) -> Image.Image:
    """画出 ``size``×``size`` 的图标（RGBA，圆角外透明）。"""
    k = size * supersample

    # 1) 圆角方形 + 渐变底
    grad = _gradient_column(k).resize((k, k), Image.NEAREST)
    mask = Image.new("L", (k, k), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, k - 1, k - 1), radius=int(round(CORNER_RADIUS * k)), fill=255
    )
    img = Image.new("RGBA", (k, k), (0, 0, 0, 0))
    img.paste(grad, (0, 0), mask)
    del grad, mask

    # 2) 白色门式刚架 + 右箭头
    d = ImageDraw.Draw(img)
    for key in ("beam", "col_l", "col_r", "foot_l", "foot_r", "shaft"):
        x0, y0, x1, y1 = GEOM[key]
        d.rectangle((x0 * k, y0 * k, x1 * k, y1 * k), fill=COLOR_FG)
    d.polygon([(x * k, y * k) for x, y in ARROW_HEAD], fill=COLOR_FG)
    del d

    # 3) 缩小到目标尺寸（LANCZOS 抗锯齿）
    return img.resize((size, size), Image.LANCZOS)


def stroke_widths_px(size: int):
    """返回 16 px 尺度的笔画宽度清单（供自检打印）。"""
    out = []
    for key in ("beam", "col_l", "col_r", "foot_l", "foot_r", "shaft"):
        x0, y0, x1, y1 = GEOM[key]
        w, h = (x1 - x0), (y1 - y0)
        out.append((key, min(w, h), min(w, h) * size))
    head_w = ARROW_HEAD[1][0] - ARROW_HEAD[0][0]
    head_h = ARROW_HEAD[2][1] - ARROW_HEAD[0][1]
    out.append(("arrow_head(min宽/高)", min(head_w, head_h), min(head_w, head_h) * size))
    return out


# ---------------------------------------------------------------- 预览图纸

_FONT_CANDIDATES = (
    r"C:\Windows\Fonts\msyh.ttc",     # 微软雅黑
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",   # 黑体
    r"C:\Windows\Fonts\simsun.ttc",   # 宋体
)


def _load_font(px: int):
    """尽量加载中文字体；失败则退到 Pillow 内置位图字体（返回 (font, has_cjk)）。"""
    for path in _FONT_CANDIDATES:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, px), True
            except Exception:
                continue
    return ImageFont.load_default(), False


def _text_size(draw, text, font):
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def build_preview(images) -> Image.Image:
    """把 16/24/32/48/64 并排放大：上排最近邻（真实像素）、下排平滑（实际观感）。

    每个尺寸都放大到 ``PREVIEW_HEIGHT``（192 = 12×16 = 8×24 = 6×32 = 4×48 = 3×64），
    所以上排放大的倍率都是整数、不含插值。
    """
    gap = 24
    margin = 24
    cell = PREVIEW_HEIGHT
    n = len(PREVIEW_SIZES)
    width = margin * 2 + n * cell + (n - 1) * gap

    f_title, cjk = _load_font(20)
    f_label, _ = _load_font(16)
    f_note, _ = _load_font(14)
    assert cjk, "没找到中文字体，预览图纸的文字会退化为 ASCII"

    # 先量高度，再建画布 —— 避免行与行压在一起
    probe = Image.new("RGB", (width, 8), COLOR_SHEET_BG)
    dp = ImageDraw.Draw(probe)
    h_title = _text_size(dp, "Ag", f_title)[1]
    h_label = _text_size(dp, "Ag", f_label)[1]
    h_note = _text_size(dp, "Ag", f_note)[1]
    row_h = h_label + 6 + cell + 4 + h_note
    height = margin + h_title + 12 + row_h + 14 + row_h + margin

    sheet = Image.new("RGB", (width, height), COLOR_SHEET_BG)
    d = ImageDraw.Draw(sheet)

    def put(text, x, y, font, fill=COLOR_TEXT):
        d.text((x, y), text, font=font, fill=fill)

    y = margin
    put("PKPM2PDMS 插件图标 —— 小尺寸预览（16 / 24 / 32 / 48 / 64 px）", margin, y, f_title)
    y += h_title + 12

    def draw_row(y0, resample, caption):
        for i, s in enumerate(PREVIEW_SIZES):
            x0 = margin + i * (cell + gap)
            lab = "%d px   ( %d x )" % (s, cell // s)
            tw = _text_size(d, lab, f_label)[0]
            put(lab, x0 + (cell - tw) // 2, y0, f_label, COLOR_TEXT_DIM)
            top = y0 + h_label + 6
            d.rectangle((x0, top, x0 + cell - 1, top + cell - 1), fill=COLOR_CELL_BG)
            sheet.paste(images[s].resize((cell, cell), resample), (x0, top))
            d.rectangle((x0, top, x0 + cell - 1, top + cell - 1), outline=(0xB0, 0xBE, 0xD0))
        put(caption, margin, top + cell + 4, f_note, COLOR_TEXT_DIM)
        return y0 + row_h

    y = draw_row(y, Image.NEAREST, "上排 = 最近邻放大（看真实像素；每格都是整数倍，无插值）")
    y += 14
    y = draw_row(y, Image.LANCZOS, "下排 = 平滑放大（看实际观感，与系统里显示的样子一致）")

    return sheet


# ---------------------------------------------------------------- 产出与自检

def human(path: str) -> str:
    return "%s (%d 字节)" % (path, os.path.getsize(path))


def generate(out_dir: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    images = {s: render(s) for s in sorted(set(ICO_SIZES) | set(PREVIEW_SIZES))}

    ico_path = os.path.join(out_dir, "pkpm2pdms.ico")
    png_path = os.path.join(out_dir, "pkpm2pdms_256.png")
    preview_path = os.path.join(out_dir, "小尺寸预览.png")

    sizes = [(s, s) for s in ICO_SIZES]
    # bitmap_format="bmp" -> 每个尺寸写成**经典 BMP/DIB 帧**（不是 PNG 帧）。
    # 理由：Pillow 缺省会把帧写成 PNG；而 PNG 帧的 ICO 是 Vista+ 的扩展，
    # .NET Framework 3.5 的 csc.exe /win32icon（B 包 build.cmd 要用）对 PNG 帧
    # 存在拒绝/解析失败的风险。BMP 帧是 ICO 的原始格式，所有工具都认 —— 代价只是文件大一些。
    images[256].save(
        ico_path,
        format="ICO",
        sizes=sizes,
        bitmap_format="bmp",
        append_images=[images[s] for s in ICO_SIZES if s != 256],
    )
    images[256].save(png_path, format="PNG")
    build_preview(images).save(preview_path, format="PNG")
    return {"ico": ico_path, "png256": png_path, "preview": preview_path}


def verify(paths: dict) -> int:
    """用 PIL 重新打开 ICO，打印每个尺寸；并打印三个产物的字节数。"""
    bad = 0
    ico = Image.open(paths["ico"])
    print("自检 1：重新打开 %s" % paths["ico"])
    print("        format=%s  ico.info['sizes']=%s"
          % (ico.format, sorted(ico.info.get("sizes", set()))))
    frames = []
    for s in ICO_SIZES:
        try:
            ico.size = (s, s)
            ico.load()
            got = ico.size
            raw = ico.convert("RGBA").tobytes()
            solid = sum(1 for i in range(0, len(raw), 4) if raw[i + 3] > 0)
            frames.append((s, got[0], got[1], len(raw), solid))
            print("        %3d x %-3d -> 实际 %s  解码 RGBA %7d 字节  不透明像素 %6d (%.1f%%)"
                  % (s, s, "%dx%d" % got, len(raw), solid, 100.0 * solid / (s * s)))
            if got != (s, s):
                bad += 1
        except Exception as exc:
            print("        %3d x %-3d -> 读取失败：%s" % (s, s, exc))
            bad += 1
    print("        共 %d 个尺寸帧：%s" % (len(frames), ", ".join(str(f[0]) for f in frames)))

    print("")
    print("自检 2：笔画宽度（阈值 边长 × %.0f%%）" % (MIN_STROKE_RATIO * 100))
    for key, ratio, px16 in stroke_widths_px(16):
        flag = "OK " if ratio >= MIN_STROKE_RATIO else "太细"
        print("        %-22s 占边长 %.3f  16px 下 %.2f px   %s" % (key, ratio, px16, flag))
        if ratio < MIN_STROKE_RATIO:
            bad += 1

    print("")
    print("自检 3：产物")
    for label, key in (("ico          ", "ico"), ("256 png      ", "png256"), ("小尺寸预览 png", "preview")):
        p = paths[key]
        print("        %s %-46s %9d 字节" % (label, os.path.basename(p), os.path.getsize(p)))
    return bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="生成 PKPM2PDMS v2.1.0 插件图标（可复现）")
    ap.add_argument("--out-dir", default=os.path.dirname(os.path.abspath(__file__)),
                    help="输出目录（缺省：本脚本所在目录）")
    ap.add_argument("--quiet", action="store_true", help="不打印生成过程")
    args = ap.parse_args(argv)

    if not args.quiet:
        print("=" * 78)
        print("生成 PKPM2PDMS 插件图标（深蓝底 + 白门式刚架 + 白右箭头）")
        print("=" * 78)
        print("输出目录 : " + args.out_dir)
        print("ico 尺寸 : " + ", ".join(str(s) for s in ICO_SIZES))
        print("超采样   : %dx + LANCZOS" % SUPERSAMPLE)
        print("")

    paths = generate(args.out_dir)
    if not args.quiet:
        for key in ("ico", "png256", "preview"):
            print("  已写出 " + human(paths[key]))
        print("")
    bad = verify(paths)
    print("")
    print("结论：%s（失败 %d 项）" % ("全部通过" if bad == 0 else "有问题", bad))
    print("人工看图：" + paths["preview"])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
