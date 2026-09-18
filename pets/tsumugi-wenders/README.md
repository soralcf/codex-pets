# 紬文德斯 / Tsumugi Wenders

![动作总览](previews/contact-sheet.png)

以暖金色双马尾、绿色眼睛、粉色 X 发夹和水手制服为核心特征制作的 Codex v2 动态角色形象。形象气质参考[萌娘百科角色资料](https://zh.moegirl.org.cn/%E4%8C%B7%E6%96%87%E5%BE%B7%E6%96%AF)，呈现认真、坦率、温柔又好奇的性格。

## Install

From the repository root:

```bash
mkdir -p ~/.codex/pets/tsumugi-wenders
cp pets/tsumugi-wenders/pet.json ~/.codex/pets/tsumugi-wenders/
cp pets/tsumugi-wenders/spritesheet.webp ~/.codex/pets/tsumugi-wenders/
```

然后在 ChatGPT 桌面应用的 **Settings → Pets** 中刷新并选择“紬文德斯”。

## 2026-09-18 动作修复

- 重绘待机、左右跑步、跳跃和失败五行动作，保留人物的金发、绿瞳、发夹和制服设定。
- 修复失败和待机行的纵向切片：原图中的头发被切断后混入相邻帧。现在按完整人物轮廓提取，无法识别完整姿势时直接报错，不再退回等宽切片。
- 跳跃采用统一缩放比例，保留起跳、腾空、落地的位置关系，去掉首帧突然放大的效果。
- 审阅动作按脚部锚点对齐；保留动作的头发外缘做局部白色底边修复，不改透明度、脸部或衣服内部细节。16 向视线的姿势和透明轮廓保持不变。

| 动作 | 修复前脚部横向漂移 | 修复后 |
| --- | ---: | ---: |
| 待机 | 5.90 px | 0.62 px |
| 失败 | 11.40 px | 0.75 px |
| 审阅 | 6.31 px | 0.70 px |

用浏览器打开本地的 [逐帧对照页](previews/compare.html)，可以暂停、逐帧切换、慢放和改变背景颜色。也可直接查看[失败动作对照](previews/failed-comparison.webp)、[跳跃对照](previews/jumping-comparison.webp)、[向右跑对照](previews/running-right-comparison.webp)和[向左跑对照](previews/running-left-comparison.webp)。

本次核对的桌面播放器将非待机动作播放三遍，再进入慢速待机；跳跃固定读取 5 帧，左右跑步固定读取 8 帧。重复次数和每帧时长由播放器决定，不能靠增加精灵图中的图片数量改变。对照页复现这一节奏，也提供持续循环。跑步仍是有限帧数下的风格化步态，部分步幅和末帧停顿不完全均匀。

## Validation

- Sprite contract: v2
- Atlas: `1536 × 2288`, RGBA WebP, `8 × 11`
- Standard animations: 9 rows
- Look directions: 16
- Transparent RGB residue: 0 pixels
- Deterministic atlas validation: passed with no errors or warnings
- Regenerated rows: silhouette, pose continuity and animation QA; see the current report below
- Look directions: original three independent blind reviews retained as historical evidence; this repair preserves their geometry and alpha exactly

查看[16 向视线图](previews/look-directions.png)、[结构和透明边缘验证](qa/validation.json)、[动作检查](qa/final-visual-qa.json)与[位置测量](qa/motion-review.json)。原图检查报告不能证明动作没有切片问题，本次另外检查了人物轮廓内部的竖直切边。

## Sources and rebuild

本次通过 OpenAI 内置图像生成工具重绘。采用的原始行图、提示词和参考图保存在 [sources/2026-09-18](sources/2026-09-18/manifest.json)，被否决的候选图未打包。前一版精灵图保留在 [previews/before-2026-09-18.webp](previews/before-2026-09-18.webp)，用于对照和还原。

需要带 Pillow、NumPy 的 Python，以及已安装的 `hatch-pet` 技能。以下命令从仓库根目录运行，构建到临时目录，不覆盖安装文件：

```bash
PET_BUILD_DIR=$(mktemp -d)
mkdir -p "$PET_BUILD_DIR/decoded" "$PET_BUILD_DIR/qa"
cp pets/tsumugi-wenders/sources/2026-09-18/decoded/*.png "$PET_BUILD_DIR/decoded/"
python3 tools/register_tsumugi_rows.py \
  --run-dir "$PET_BUILD_DIR" --skill-dir "$HOME/.codex/skills/hatch-pet"
python3 tools/repair_tsumugi.py \
  --source pets/tsumugi-wenders/previews/before-2026-09-18.webp \
  --replacement-frames "$PET_BUILD_DIR/frames" --output-dir "$PET_BUILD_DIR/final"
python3 "$HOME/.codex/skills/hatch-pet/scripts/validate_atlas.py" \
  "$PET_BUILD_DIR/final/spritesheet.webp" --require-v2 --chroma-key '#FF00FF'
```

`tools/review_tsumugi.py` 可以重新生成前后对照动画与脚部位移报告。构建过程对每一行动作使用共同缩放比例，保留真实的屈膝高度变化；透明背景清理在最终缩放后完成，避免重采样再次带入背景色。

## Notice

This is unofficial fan-made artwork for personal customization. The underlying character and design belong to their respective rights holders.
