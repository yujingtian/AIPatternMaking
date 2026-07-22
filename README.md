# 女性弯腰头牛仔裤打版程序

将版师手工打版流程程序化，自动计算版型关键点并导出DXF和SVG文件。

## 功能特性

- **前片打版**：根据尺寸参数自动计算牛仔裤前片版型
  - 弯腰头设计
  - 前门襟裁片
  - 月牙袋（含袋贴、袋布、小表袋）
- **后片打版**：自动计算牛仔裤后片版型
  - 困势线与后浪曲线
  - 落档设计
  - 腰省设计
  - 腰头（4cm宽）
  - 机头
  - 后口袋
- **前片与后片共用坐标系**：前后片水平参考线一致，便于缝合
- **同时导出DXF和SVG两种格式**
  - DXF格式：可直接用于CAD软件，包含参考线层、轮廓线层、关键点标注层
  - SVG格式：可在浏览器中预览，包含参考线、尺寸标注、图例
- **完整版和简化版DXF可选**

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 快速开始（使用默认参数，含前后片）

```bash
python run.py
```

这会使用文档中的示例参数，同时输出DXF（完整版+简化版）和SVG：
- 腰围: 70cm
- 臀围: 90cm
- 膝围: 36cm
- 裤口: 39cm
- 前浪: 24cm
- 后浪: 34.5cm
- 裤长: 100cm

### 自定义参数（同时输出DXF+SVG）

```bash
python main.py --waist 72 --hip 94 --knee 38 --hem 40 --front-rise 25 --length 102
```

### 只输出SVG

```bash
python main.py --svg-only
```

### 只输出DXF

```bash
python main.py --dxf-only --simple
```

### 指定输出文件名

```bash
python main.py --output my_pattern
```

### SVG自定义选项

```bash
python main.py --svg-scale 3.0 --no-ref --no-dim
```

### 查看帮助

```bash
python main.py --help
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--waist` | 腰围 (cm) | 70.0 |
| `--hip` | 臀围 (cm) | 90.0 |
| `--knee` | 膝围 (cm) | 36.0 |
| `--hem` | 裤口 (cm) | 39.0 |
| `--front-rise` | 前浪 (cm) | 24.0 |
| `--length` | 裤长 (cm) | 100.0 |
| `--waist-ease` | 腰围松量 (cm) | 0.3 |
| `--hip-ease` | 臀围松量 (cm) | 0.2 |
| `--dart-width` | 省道宽 (cm) | 0.6 |
| `--front-rise-curve` | 前浪曲线凹陷程度 | 1.5 |
| `--output, -o` | 输出文件名（不含扩展名） | jeans_pattern |
| `--simple` | 导出简化版DXF（仅轮廓） | 否 |
| `--units` | 输出单位 (mm/cm) | mm |
| `--dxf` | 输出DXF格式 | 自动 |
| `--svg` | 输出SVG格式 | 自动 |
| `--dxf-only` | 只输出DXF | 否 |
| `--svg-only` | 只输出SVG | 否 |
| `--svg-scale` | SVG显示缩放比例 | 2.0 |
| `--no-ref` | SVG不包含参考线 | 否 |
| `--no-dim` | SVG不包含尺寸标注 | 否 |
| `--no-print` | 不打印计算结果 | 否 |

## 输出文件

程序会生成以下文件：

### DXF文件

1. **jeans_pattern.dxf** - 完整版DXF，包含：
   - 前片：参考线层、轮廓线层、关键点层、标注层
   - 后片：参考线层、轮廓线层、关键点层、标注层
   - 裁片：前门襟、袋贴、小表袋、袋布等独立裁片

2. **jeans_pattern_simple.dxf** - 简化版DXF，仅包含闭合轮廓线（使用`run.py`生成）

### SVG文件

**jeans_pattern.svg** - SVG预览图，包含：
- 前片与后片版型轮廓（浅蓝色填充）
- 参考线（蓝色虚线）
- 关键点标注（红色十字）
- 尺寸标注（带箭头）
- 图例说明

可直接在浏览器中打开查看!

## 项目结构

```
AIPatternMaking/
├── src/
│   ├── __init__.py
│   ├── types.py              # 数据类型定义（前片+后片）
│   ├── pattern_calculator.py # 前片核心计算逻辑
│   ├── back_pattern_calculator.py # 后片核心计算逻辑
│   ├── dxf_exporter.py       # DXF导出功能（支持前后片）
│   └── svg_exporter.py       # SVG导出功能（支持前后片）
├── main.py                   # 命令行主程序
├── run.py                    # 快速启动脚本（含前后片）
├── requirements.txt          # Python依赖
├── README.md                 # 本文件
├── 版师打版流程.md          # 原版前片打版流程文档
└── 版师后片打版流程.md      # 后片打版流程文档
```

## 前片计算流程

程序严格按照《版师打版流程.md》中的步骤进行计算：

1. **建立基础参考线与大矩形框架**
   - 外侧缝参考线 X=0
   - 内侧缝参考线 X=臀围/4-1+0.2
   - 五条水平参考线：脚口、膝围、立裆、臀围、腰围

2. **确定立裆宽**
   - 立裆宽 = 臀围×0.04（约3.5cm）
   - 从内侧缝继续向右延伸

3. **细化绘制前浪基础线**
   - 计算角平分线辅助点
   - 绘制凹曲线

4. **确定裤中线**
   - 取立裆总宽度中点，向外缝侧微移0.6cm

5. **计算膝围与脚口顶点**
   - 以裤中线为基准分配宽度

6. **连接侧缝与内侧缝**
   - 绘制圆顺曲线

7. **完善腰围线**
   - 贝塞尔曲线绘制弯腰头

8. **绘制腰头**
   - 上腰头与下腰头（4cm宽）

9. **绘制前门襟**
   - 门襟弧线与独立裁片

10. **绘制月牙袋**
    - 袋口弧线、省道、袋贴、袋布、小表袋

## 后片计算流程

程序严格按照《版师后片打版流程.md》中的步骤进行计算：

1. **建立基础参考线与大矩形框架**
   - 外侧缝参考线 X=0
   - 内侧缝参考线 X=臀围/4+1+0.2（比前片宽2cm）
   - 五条水平参考线Y坐标与前片一致

2. **确定后腰头线宽度**
   - 后腰围外缝顶点向内收0.5cm
   - 后腰围宽 = 腰围/4+0.3+2cm省道

3. **确定后立裆宽和落档**
   - 后立裆宽 = 臀围×0.1（约9cm）
   - 落档1cm

4. **绘制后浪基础线**
   - 困势线（腰围内缝顶点→臀围内缝顶点→落档线交点）
   - 角平分线辅助点
   - 二次+三次贝塞尔曲线绘制凹曲线

5. **确定裤中线**
   - 取立裆总宽度中点，向外侧缝侧平移2.5cm

6. **计算膝围与脚口顶点**
   - 后片单侧宽 = (围度/2 + 0.6×2)/2

7. **连接侧缝与内侧缝**
   - 外缝：腰外→臀外→膝外→脚口外
   - 内缝：立裆宽顶点→膝内→脚口内

8. **绘制最终腰围线**
   - 从后立裆宽顶点沿后浪量后浪长找新腰围内缝顶点
   - 从新腰围内缝顶点作后浪垂线，与外缝延长线相交得新腰围外缝顶点

9. **绘制腰省**
   - 省中点取腰围线中点
   - 省尖沿腰围线垂线向下11cm
   - 省宽2cm

10. **绘制腰头**
    - 沿外缝向下4cm
    - 沿后浪向下4cm
    - 下腰头曲线与上腰头平行

11. **绘制机头**
    - 从下腰头内端点沿后浪向下7cm
    - 从下腰头外端点沿外缝向下3.5cm

12. **绘制后口袋**
    - 口袋中线与省中线平行，向外缝侧平移1.3cm
    - 口袋上口与机头线平行，向下2.5cm
    - 口袋高12cm，上口宽12cm
    - 袋口两角微调

## 作为库使用

```python
from src.types import PatternParams, PatternPoints, BackPatternPoints
from src.pattern_calculator import JeansPatternCalculator
from src.back_pattern_calculator import BackPanelCalculator
from src.dxf_exporter import DXFExporter, SimpleDXFExporter
from src.svg_exporter import SVGExporter

# 创建参数
params = PatternParams(
    waist=70.0,
    hip=90.0,
    knee=36.0,
    hem=39.0,
    front_rise=24.0,
    back_rise=34.5,  # 后浪长
    pants_length=100.0
)

# 计算前片
front_calculator = JeansPatternCalculator(params)
front_points = front_calculator.calculate()

# 计算后片
back_calculator = BackPanelCalculator(params)
back_points = back_calculator.calculate()

# 导出DXF（同时包含前片和后片）
dxf_exporter = DXFExporter(units='mm')
dxf_exporter.export(front_points, 'output.dxf', back_points=back_points)

# 导出SVG（同时包含前片和后片）
svg_exporter = SVGExporter(units='mm', scale=2.0)
svg_exporter.export(front_points, 'output.svg', back_points=back_points)
```

## 后片裁片拆分

程序自动计算并导出以下后片裁片：

1. **后片整体轮廓裁片**
   - 闭合轮廓：从机头外缝顶点开始，经机头内缝顶点、后浪曲线、后立裆宽顶点、内缝曲线、脚口线、外缝曲线，回到机头外缝顶点
   - 包含对位线：后口袋轮廓、腰省
   - 单独显示在DXF/SVG最下方

2. **后腰头裁片（省道拼合）**
   - 省道拼合：将省道内侧的腰头部分旋转平移，使省道内端点与省外端点重合
   - 闭合轮廓：下腰头外→省道外→下腰头内（拼合后）→上腰头内（拼合后）→上腰头外→外缝边→下腰头外
   - 单独显示在后片裁片下方

3. **后口袋裁片**
   - 闭合轮廓：上内→上外→下外→下中→下内→上内
   - 单独显示在后腰头裁片下方

## 技术栈

- Python 3.8+
- ezdxf - DXF文件生成
- 原生Python生成SVG（无需额外依赖）

## 许可证

本项目仅供学习和参考使用。
