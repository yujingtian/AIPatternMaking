#!/usr/bin/env python3
"""
女性弯腰头牛仔裤打版程序 - 启动脚本（含前后片）
"""
import sys
from pathlib import Path

# 确保能找到src模块
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.types import PatternParams, PatternPoints, BackPatternPoints
from src.pattern_calculator import JeansPatternCalculator
from src.back_pattern_calculator import BackPanelCalculator
from src.dxf_exporter import DXFExporter, SimpleDXFExporter
from src.svg_exporter import SVGExporter


def print_points_info(points: PatternPoints) -> None:
    """打印前片关键点信息"""
    print("\n" + "="*60)
    print("前片版型计算结果")
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

    print("\n" + "="*60)


def print_back_points_info(points: BackPatternPoints) -> None:
    """打印后片关键点信息 (包含折叠腰头)"""
    print("\n" + "="*60)
    print("后片版型计算结果")
    print("="*60)

    bbox = points.bounding_box
    print(f"\n【后片基础框架】")
    print(f"  外侧缝参考线: X = {bbox.outer_seam_x:.2f}")
    print(f"  内侧缝参考线: X = {bbox.inner_seam_x:.2f} (比前片宽)")
    print(f"  臀围参考线:   Y = {bbox.hip_y:.2f}")

    print(f"\n【后裤中线】")
    print(f"  裤中线位置:   X = {points.center_crease_x:.2f}")

    print(f"\n【后浪与立裆】")
    crotch = points.crotch
    print(f"  立裆宽顶点(落档前): ({crotch.crotch_extend_point[0]:.2f}, {crotch.crotch_extend_point[1]:.2f})")
    print(f"  落档后顶点:         ({crotch.back_crotch_point[0]:.2f}, {crotch.back_crotch_point[1]:.2f})")

    print(f"\n【最终腰围线与省道】")
    wf = points.waist_final
    dart = points.dart
    print(f"  最终腰围外缝: ({wf.new_waist_outer[0]:.2f}, {wf.new_waist_outer[1]:.2f})")
    print(f"  最终腰围内缝: ({wf.new_waist_inner[0]:.2f}, {wf.new_waist_inner[1]:.2f}) (含后翘)")
    print(f"  省道中点:     ({dart.dart_mid[0]:.2f}, {dart.dart_mid[1]:.2f})")
    print(f"  省尖:         ({dart.dart_tip[0]:.2f}, {dart.dart_tip[1]:.2f})")

    print(f"\n【折叠画顺后腰头 (4cm)】")
    fw = points.folded_waistband
    print(f"  上腰头曲线采样点数: {len(fw.top_curve)}")
    print(f"  下腰头曲线采样点数: {len(fw.bottom_curve)}")
    print(f"  上腰头起点(外):     ({fw.top_curve[0][0]:.2f}, {fw.top_curve[0][1]:.2f})")
    print(f"  上腰头终点(内):     ({fw.top_curve[-1][0]:.2f}, {fw.top_curve[-1][1]:.2f})")

    print("\n" + "="*60)


def main():
    print("="*60)
    print("女性弯腰头牛仔裤打版程序 (前片 + 后片)")
    print("="*60)

    # 使用文档中的示例参数，增加凹陷程度
    params = PatternParams(
        waist=70.0,
        hip=90.0,
        knee=36.0,
        hem=39.0,
        front_rise=24.0,
        back_rise=35.0,     # 后浪参数
        pants_length=100.0,
        front_rise_curve=2.5  # 增加凹陷程度
    )

    print(f"\n输入参数:")
    print(f"  腰围:      {params.waist} cm")
    print(f"  臀围:      {params.hip} cm")
    print(f"  膝围:      {params.knee} cm")
    print(f"  裤口:      {params.hem} cm")
    print(f"  前浪:      {params.front_rise} cm")
    print(f"  后浪:      {params.back_rise} cm")
    print(f"  裤长:      {params.pants_length} cm")
    print(f"  前浪凹陷:  {params.front_rise_curve}")

    # ================= 1. 计算前片 =================
    print(f"\n正在计算前片...")
    calculator = JeansPatternCalculator(params)
    try:
        points = calculator.calculate()
        print_points_info(points)
    except Exception as e:
        print(f"\n错误: 前片计算失败 - {e}")
        import traceback
        traceback.print_exc()
        return 1

    # ================= 2. 计算后片 =================
    print(f"\n正在计算后片...")
    back_calculator = BackPanelCalculator(params)
    try:
        back_points = back_calculator.calculate()
        print_back_points_info(back_points)
    except Exception as e:
        print(f"\n错误: 后片计算失败 - {e}")
        import traceback
        traceback.print_exc()
        return 1

    # ================= 3. 导出文件 =================
    output_dxf = project_root / 'jeans_pattern.dxf'
    output_simple = project_root / 'jeans_pattern_simple.dxf'
    output_svg = project_root / 'jeans_pattern.svg'

    print(f"\n正在导出文件...")

    # 完整版DXF（同时渲染前片 + 后片）
    exporter = DXFExporter(units='mm')
    exporter.export(points, str(output_dxf), back_points=back_points)

    # 简化版DXF
    simple_exporter = SimpleDXFExporter(units='mm')
    simple_exporter.export(points, str(output_simple))

    # SVG文件
    svg_exporter = SVGExporter(units='mm', scale=2.0)
    svg_exporter.export(points, str(output_svg), back_points=back_points)

    print(f"\n完成!")
    print(f"  DXF完整版: {output_dxf}")
    print(f"  DXF简化版: {output_simple}")
    print(f"  SVG预览:  {output_svg}")

    return 0


if __name__ == '__main__':
    sys.exit(main())