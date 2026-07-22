#!/usr/bin/env python3
"""
女性弯腰头牛仔裤前片打版程序
使用方法:
    python main.py                    # 使用默认参数
    python main.py --waist 72 --hip 94  # 自定义参数
    python main.py --help             # 查看帮助
"""
import argparse
import sys
from pathlib import Path

# 添加src目录到路径
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from src.types import PatternParams, PatternPoints
from src.pattern_calculator import JeansPatternCalculator
from src.back_pattern_calculator import BackPanelCalculator
from src.dxf_exporter import DXFExporter, SimpleDXFExporter
from src.svg_exporter import SVGExporter


def print_points_info(points: PatternPoints) -> None:
    """打印关键点信息"""
    print("\n" + "="*60)
    print("版型计算结果")
    print("="*60)

    bbox = points.bounding_box
    print(f"\n【基础框架】")
    print(f"  外侧缝参考线: X = {bbox.outer_seam_x:.2f}")
    print(f"  内侧缝参考线: X = {bbox.inner_seam_x:.2f}")
    print(f"  脚口参考线:   Y = {bbox.hem_y:.2f}")
    print(f"  膝围参考线:   Y = {bbox.knee_y:.2f}")
    print(f"  立裆参考线:   Y = {bbox.crotch_y:.2f}")
    print(f"  臀围参考线:   Y = {bbox.hip_y:.2f}")
    print(f"  腰围参考线:   Y = {bbox.waist_y:.2f}")

    print(f"\n【裤中线】")
    print(f"  裤中线位置:   X = {points.center_crease_x:.2f}")

    print(f"\n【前浪曲线关键点】")
    fr = points.front_rise
    print(f"  臀围内缝顶点:   ({fr.hip_inner_point[0]:.2f}, {fr.hip_inner_point[1]:.2f})")
    print(f"  前浪辅助点:     ({fr.rise_helper_point[0]:.2f}, {fr.rise_helper_point[1]:.2f})")
    print(f"  立裆宽顶点:     ({fr.crotch_extension_point[0]:.2f}, {fr.crotch_extension_point[1]:.2f})")
    print(f"  腰围内缝参考:   ({fr.new_waist_inner_ref[0]:.2f}, {fr.new_waist_inner_ref[1]:.2f})")

    print(f"\n【膝围与脚口】")
    kh = points.knee_hem
    print(f"  膝围内缝顶点:   ({kh.knee_inner[0]:.2f}, {kh.knee_inner[1]:.2f})")
    print(f"  膝围外缝顶点:   ({kh.knee_outer[0]:.2f}, {kh.knee_outer[1]:.2f})")
    print(f"  脚口内缝顶点:   ({kh.hem_inner[0]:.2f}, {kh.hem_inner[1]:.2f})")
    print(f"  脚口外缝顶点:   ({kh.hem_outer[0]:.2f}, {kh.hem_outer[1]:.2f})")

    print(f"\n【腰围线】")
    w = points.waist
    print(f"  腰围外缝顶点:   ({w.waist_outer[0]:.2f}, {w.waist_outer[1]:.2f})")
    print(f"  腰围内缝顶点:   ({w.waist_inner_final[0]:.2f}, {w.waist_inner_final[1]:.2f})")
    print(f"  腰围线控制点:   ({w.waist_control[0]:.2f}, {w.waist_control[1]:.2f})")

    # 腰头信息
    if hasattr(points, 'waistband'):
        wb = points.waistband
        print(f"\n【腰头】")
        print(f"  上腰外端点:     ({wb.waist_outer[0]:.2f}, {wb.waist_outer[1]:.2f})")
        print(f"  上腰内端点:     ({wb.waist_inner_final[0]:.2f}, {wb.waist_inner_final[1]:.2f})")
        print(f"  下腰外端点:     ({wb.lower_waist_outer[0]:.2f}, {wb.lower_waist_outer[1]:.2f})")
        print(f"  下腰内端点:     ({wb.lower_waist_inner[0]:.2f}, {wb.lower_waist_inner[1]:.2f})")
        print(f"  下腰控制点:     ({wb.lower_waist_control[0]:.2f}, {wb.lower_waist_control[1]:.2f})")

    # 前门襟信息
    if hasattr(points, 'front_fly'):
        ff = points.front_fly
        print(f"\n【前门襟】")
        print(f"  门襟起点:       ({ff.fly_start_point[0]:.2f}, {ff.fly_start_point[1]:.2f})")
        print(f"  门襟内端点:     ({ff.fly_inner_end[0]:.2f}, {ff.fly_inner_end[1]:.2f})")
        print(f"  门襟外端点:     ({ff.fly_outer_end[0]:.2f}, {ff.fly_outer_end[1]:.2f})")
        print(f"  门襟弧终点:     ({ff.fly_end_point[0]:.2f}, {ff.fly_end_point[1]:.2f})")
        if getattr(ff, 'fly_panel_outline', None):
            print(f"  门襟裁片轮廓:   {len(ff.fly_panel_outline)} 个采样点（单独绘制于前片下方）")

    # 月牙袋信息
    if hasattr(points, 'crescent_pocket'):
        cp = points.crescent_pocket
        wb = points.waistband
        print(f"\n【月牙袋】")
        print(f"  袋外顶点:       ({cp.pocket_outer[0]:.2f}, {cp.pocket_outer[1]:.2f})")
        print(f"  袋宽顶点:       ({cp.pocket_width[0]:.2f}, {cp.pocket_width[1]:.2f})")
        print(f"  袋省顶点:       ({cp.pocket_dart[0]:.2f}, {cp.pocket_dart[1]:.2f})")
        print(f"  袋省线宽点:   ({cp.pocket_dart_line_width[0]:.2f}, {cp.pocket_dart_line_width[1]:.2f})")
        print(f"  袋省线省点:   ({cp.pocket_dart_line_dart[0]:.2f}, {cp.pocket_dart_line_dart[1]:.2f})")
        print(f"  上腰外顶点:     ({wb.waist_outer[0]:.2f}, {wb.waist_outer[1]:.2f})")

    # 袋贴信息
    if hasattr(points, 'pocket_patch'):
        pp = points.pocket_patch
        print(f"\n【袋贴】")
        print(f"  贴腰顶点:       ({pp.patch_lower_waist[0]:.2f}, {pp.patch_lower_waist[1]:.2f})")
        print(f"  贴外顶点:       ({pp.patch_outer_seam[0]:.2f}, {pp.patch_outer_seam[1]:.2f})")

    # 袋布信息
    if hasattr(points, 'pocket_bag'):
        pb = points.pocket_bag
        print(f"\n【袋布】")
        print(f"  布腰顶点:       ({pb.bag_upper_waist[0]:.2f}, {pb.bag_upper_waist[1]:.2f})")
        print(f"  布内端点:       ({pb.bag_inner_end[0]:.2f}, {pb.bag_inner_end[1]:.2f})")
        print(f"  布拐点:         ({pb.bag_corner[0]:.2f}, {pb.bag_corner[1]:.2f})")
        print(f"  布外顶点:       ({pb.bag_outer_seam[0]:.2f}, {pb.bag_outer_seam[1]:.2f})")

    # 小表袋信息
    if hasattr(points, 'watch_pocket'):
        wp = points.watch_pocket
        print(f"\n【小表袋】")
        print(f"  表上外端点:     ({wp.outer_upper[0]:.2f}, {wp.outer_upper[1]:.2f})")
        print(f"  表下外端点:     ({wp.outer_lower[0]:.2f}, {wp.outer_lower[1]:.2f})")
        print(f"  表上内端点:     ({wp.inner_upper[0]:.2f}, {wp.inner_upper[1]:.2f})")
        print(f"  表下内端点:     ({wp.inner_lower[0]:.2f}, {wp.inner_lower[1]:.2f})")

    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(
        description='女性弯腰头牛仔裤前片打版程序',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                                      # 使用默认参数（同时输出DXF+SVG）
  %(prog)s --waist 72 --hip 94                  # 自定义腰围和臀围
  %(prog)s --waist 70 --hip 90 --knee 36 --hem 39 --front-rise 24 --length 100
  %(prog)s --output my_pattern                  # 指定输出文件名（不含扩展名）
  %(prog)s --dxf --svg                          # 同时输出DXF和SVG
  %(prog)s --svg-only                           # 只输出SVG
  %(prog)s --simple                             # 导出简化版DXF（仅轮廓）
        """
    )

    # 尺寸参数
    parser.add_argument('--waist', type=float, default=70.0,
                        help='腰围 (cm)，默认: 70.0')
    parser.add_argument('--hip', type=float, default=90.0,
                        help='臀围 (cm)，默认: 90.0')
    parser.add_argument('--knee', type=float, default=36.0,
                        help='膝围 (cm)，默认: 36.0')
    parser.add_argument('--hem', type=float, default=39.0,
                        help='裤口 (cm)，默认: 39.0')
    parser.add_argument('--front-rise', type=float, default=24.0,
                        help='前浪 (cm)，默认: 24.0')
    parser.add_argument('--length', type=float, default=100.0,
                        help='裤长 (cm)，默认: 100.0')

    # 微调参数
    parser.add_argument('--waist-ease', type=float, default=0.3,
                        help='腰围松量 (cm)，默认: 0.3')
    parser.add_argument('--hip-ease', type=float, default=0.2,
                        help='臀围松量 (cm)，默认: 0.2')
    parser.add_argument('--dart-width', type=float, default=0.6,
                        help='省道宽 (cm)，默认: 0.6')
    parser.add_argument('--front-rise-curve', type=float, default=1.5,
                        help='前浪曲线凹陷程度，越大越凹，默认: 1.5')

    # 输出选项
    parser.add_argument('--output', '-o', type=str, default='jeans_pattern',
                        help='输出文件名（不含扩展名），默认: jeans_pattern')
    parser.add_argument('--simple', action='store_true',
                        help='导出简化版DXF（仅闭合轮廓）')
    parser.add_argument('--units', type=str, choices=['mm', 'cm'], default='mm',
                        help='输出单位，默认: mm')

    # 格式选项
    parser.add_argument('--dxf', action='store_true', help='输出DXF格式')
    parser.add_argument('--svg', action='store_true', help='输出SVG格式')
    parser.add_argument('--dxf-only', action='store_true', help='只输出DXF')
    parser.add_argument('--svg-only', action='store_true', help='只输出SVG')

    # SVG选项
    parser.add_argument('--svg-scale', type=float, default=2.0,
                        help='SVG显示缩放比例，默认: 2.0')
    parser.add_argument('--no-ref', action='store_true',
                        help='SVG不包含参考线')
    parser.add_argument('--no-dim', action='store_true',
                        help='SVG不包含尺寸标注')

    # 其他选项
    parser.add_argument('--no-print', action='store_true',
                        help='不打印计算结果')

    args = parser.parse_args()

    # 确定输出格式
    output_dxf = args.dxf or args.dxf_only or not (args.svg or args.svg_only)
    output_svg = args.svg or args.svg_only or not (args.dxf or args.dxf_only)

    if args.dxf_only:
        output_svg = False
    if args.svg_only:
        output_dxf = False

    # 创建参数对象
    params = PatternParams(
        waist=args.waist,
        hip=args.hip,
        knee=args.knee,
        hem=args.hem,
        front_rise=args.front_rise,
        pants_length=args.length,
        waist_ease=args.waist_ease,
        hip_ease=args.hip_ease,
        dart_width=args.dart_width,
        front_rise_curve=args.front_rise_curve
    )

    # 打印输入参数
    print("="*60)
    print("女性弯腰头牛仔裤前片打版程序")
    print("="*60)
    print(f"\n输入参数:")
    print(f"  腰围:      {params.waist} cm")
    print(f"  臀围:      {params.hip} cm")
    print(f"  膝围:      {params.knee} cm")
    print(f"  裤口:      {params.hem} cm")
    print(f"  前浪:      {params.front_rise} cm")
    print(f"  裤长:      {params.pants_length} cm")
    print(f"  前浪凹陷:  {params.front_rise_curve}")

    # 创建计算器并计算
    calculator = JeansPatternCalculator(params)
    try:
        points = calculator.calculate()
        # 后片打版（步骤1基础参考线 + 步骤2后腰头 + 步骤3后立裆/落档）
        back_points = BackPanelCalculator(params).calculate()
    except Exception as e:
        print(f"\n错误: 计算失败 - {e}")
        return 1

    # 打印计算结果
    if not args.no_print:
        print_points_info(points)

    # 导出文件
    base_path = Path(args.output)
    output_files = []

    print(f"\n正在导出文件...")

    # 导出DXF
    if output_dxf:
        dxf_path = base_path.with_suffix('.dxf')
        if args.simple:
            exporter = SimpleDXFExporter(units=args.units)
            exporter.export(points, str(dxf_path))
        else:
            exporter = DXFExporter(units=args.units)
            exporter.export(points, str(dxf_path), back_points=back_points)
        output_files.append(('DXF', dxf_path))

    # 导出SVG
    if output_svg:
        svg_path = base_path.with_suffix('.svg')
        exporter = SVGExporter(units=args.units, scale=args.svg_scale)
        exporter.export(points, str(svg_path),
                        include_reference=not args.no_ref,
                        include_dimensions=not args.no_dim,
                        back_points=back_points)
        output_files.append(('SVG', svg_path))

    print(f"\n完成!")
    for fmt, path in output_files:
        print(f"  {fmt}: {path.absolute()}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
