# 校园消费记账应用图标

设计：蓝绿色圆角底板、米白账本、确认勾与金色硬币。无文字，强调记账及预算管理，匹配界面已有蓝色标题。

文件：
- `app-icon.png`：原始透明背景图，1254 × 1254，RGBA。
- `app-icon.ico`：Windows 多尺寸图标，16/24/32/48/64/128/256 像素。

使用内置 imagegen 生成，未使用 API/CLI。PNG 保留原始透明通道，ICO 仅做格式转换与多尺寸导出。入口和窗口按源码绝对位置寻找图标，不依赖启动目录。

## 实际生成提示词

```text
Use case: logo-brand. Asset type: a single production-ready desktop application icon for a Chinese campus personal expense tracker, used in PyQt6 Windows title bar and .ico. Design a polished, minimal rounded-square app icon: deep teal / campus blue rounded tile, a clean ivory ledger notebook with two simple ledger strokes, and one warm gold coin overlapping the lower right of the notebook, small tasteful checkmark on notebook. Friendly, precise, high quality restrained soft 3D depth with crisp vector-like geometry and subtle highlights, no excessive gloss. One coherent silhouette, strong contrast and very few details, legible at 16x16 and 32x32. Centered straight-on square composition, icon occupies 88% of square with consistent safe margins, fully visible, transparent pixels outside the rounded-square tile. Actual transparent background, no checkerboard painted into image, no text, no letters, no currency glyphs, no mockup, no labels, no presentation sheet, no surrounding objects, no watermark. Output only this one icon.
```
