# 女性弯腰头牛仔裤前片打版程序

将版师手工打版流程程序化，自动计算版型关键点并导出DXF和SVG文件。

## 功能特性

- 根据尺寸参数自动计算牛仔裤前片版型
- 支持自定义腰围、臀围、膝围、裤口、前浪、裤长等参数
- **同时导出DXF和SVG两种格式**
- DXF格式：可直接用于CAD软件，包含参考线层、轮廓线层、关键点标注层
- SVG格式：可在浏览器中预览，包含参考线、尺寸标注、图例
- 完整版和简化版DXF可选

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 快速开始（使用默认参数）

```bash
python run.py
```

这会使用文档中的示例参数，同时输出DXF（完整版+简化版）和SVG：
- 腰围: 70cm
- 臀围: 90cm
- 膝围: 36cm
- 裤口: 39cm
- 前浪: 24cm
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
   - 参考线层（蓝色）
   - 轮廓线层（白色/黑色）
   - 关键点层（红色）
   - 标注层（绿色）

2. **jeans_pattern_simple.dxf** - 简化版DXF，仅包含闭合轮廓线（使用`run.py`生成）

### SVG文件

**jeans_pattern.svg** - SVG预览图，包含：
- 版型轮廓（浅蓝色填充）
- 参考线（蓝色虚线）
- 关键点标注（红色十字）
- 尺寸标注（带箭头）
- 图例说明

可直接在浏览器中打开查看！

## 项目结构

```
AIPatternMaking/
├── src/
│   ├── __init__.py
│   ├── types.py              # 数据类型定义
│   ├── pattern_calculator.py # 核心计算逻辑
│   ├── dxf_exporter.py       # DXF导出功能
│   └── svg_exporter.py       # SVG导出功能（新增）
├── main.py                   # 命令行主程序
├── run.py                    # 快速启动脚本
├── requirements.txt          # Python依赖
├── README.md                 # 本文件
└── 版师打版流程.md          # 原版打版流程文档
```

## 计算流程

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
   - 取立裆总宽度中点，向外缝微移0.6cm

5. **计算膝围与脚口顶点**
   - 以裤中线为基准分配宽度

6. **连接侧缝与内侧缝**
   - 绘制圆顺曲线

7. **完善腰围线**
   - 贝塞尔曲线绘制弯腰头

## 作为库使用

```python
from src.types import PatternParams
from src.pattern_calculator import JeansPatternCalculator
from src.dxf_exporter import DXFExporter
from src.svg_exporter import SVGExporter

# 创建参数
params = PatternParams(
    waist=70.0,
    hip=90.0,
    knee=36.0,
    hem=39.0,
    front_rise=24.0,
    pants_length=100.0
)

# 计算版型
calculator = JeansPatternCalculator(params)
points = calculator.calculate()

# 导出DXF
dxf_exporter = DXFExporter(units='mm')
dxf_exporter.export(points, 'output.dxf')

# 导出SVG
svg_exporter = SVGExporter(units='mm', scale=2.0)
svg_exporter.export(points, 'output.svg')
```

## 技术栈

- Python 3.8+
- ezdxf - DXF文件生成
- 原生Python生成SVG（无需额外依赖）

## 许可证

本项目仅供学习和参考使用。
