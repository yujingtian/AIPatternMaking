"""
SVG文件导出模块
"""
import math
from typing import List, Tuple, Optional
from pathlib import Path
from src.types import PatternPoints, BoundingBox, BackPatternPoints


def point_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """计算两点之间的距离"""
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


class SVGExporter:
    """SVG导出器"""

    def __init__(self, units: str = 'mm', scale: float = 2.0):
        """
        初始化导出器

        Args:
            units: 单位，'mm' 或 'cm'
            scale: 显示缩放比例（用于SVG视图，不影响实际尺寸）
        """
        self.units = units
        self.unit_scale = 10.0 if units == 'mm' else 1.0  # cm转mm
        self.display_scale = scale

    def export(self, points: PatternPoints, filepath: str,
               include_reference: bool = True,
               include_dimensions: bool = True,
               back_points: Optional[BackPatternPoints] = None) -> None:
        """
        导出版型到SVG文件

        Args:
            points: 版型关键点
            filepath: 输出文件名
            include_reference: 是否包含参考线
            include_dimensions: 是否包含尺寸标注
        """
        output_path = Path(filepath)

        # 收集所有轮廓点（原始版型坐标）
        all_points = []
        all_points.extend(points.outer_seam_curve)
        all_points.extend(points.inner_seam_curve)
        all_points.extend(points.front_rise_curve)
        all_points.extend(points.waistline_curve)
        if hasattr(points, 'lower_waistline_curve'):
            all_points.extend(points.lower_waistline_curve)
        if hasattr(points, 'crescent_pocket'):
            all_points.extend(points.crescent_pocket.pocket_curve)
        if hasattr(points, 'pocket_patch'):
            all_points.extend(points.pocket_patch.patch_curve)
        if hasattr(points, 'pocket_bag'):
            all_points.extend(points.pocket_bag.bag_curve)
            all_points.extend(points.pocket_bag.bag_top_edge)
        if hasattr(points, 'watch_pocket'):
            all_points.extend(points.watch_pocket.outer_line)
            all_points.extend(points.watch_pocket.inner_line)
            all_points.extend(points.watch_pocket.bottom_curve)

        # 后片整体沿X正向偏移，放在前片右侧并留间隔
        back_offset_x = 0.0
        if back_points is not None:
            bbox = back_points.bounding_box
            front_max_x = max(p[0] for p in all_points)
            back_offset_x = front_max_x + 8.0  # 前后片间隔 8cm
            # 将后片大矩形四角（带偏移）纳入画布范围
            for (cx, cy) in bbox.get_corners():
                all_points.append((cx + back_offset_x, cy))
            # 纳入后片关键点与水平参考线延伸范围，避免被画布裁切
            all_points.append((back_points.crotch.back_crotch_point[0] + back_offset_x,
                               back_points.crotch.back_crotch_point[1]))
            all_points.append((back_offset_x - 5, bbox.hem_y))
            all_points.append((bbox.inner_seam_x + back_offset_x + 10, bbox.waist_y))
            # 纳入后浪曲线采样点
            for (rx, ry) in back_points.rise.rise_curve:
                all_points.append((rx + back_offset_x, ry))
            # 纳入内缝/外缝曲线采样点
            for curve in (back_points.seam.outer_seam_curve, back_points.seam.inner_seam_curve):
                for (sx, sy) in curve:
                    all_points.append((sx + back_offset_x, sy))
            # 纳入最终腰围线顶点（后翘，高于腰围参考线）
            for p in (back_points.waist_final.new_waist_inner, back_points.waist_final.new_waist_outer):
                all_points.append((p[0] + back_offset_x, p[1]))
            # 纳入折叠腰头曲线
            if back_points.folded_waistband is not None:
                for curve in (back_points.folded_waistband.top_curve,
                              back_points.folded_waistband.bottom_curve):
                    for (sx, sy) in curve:
                        all_points.append((sx + back_offset_x, sy))

        # 计算原始版型坐标的边界
        xs = [p[0] for p in all_points]
        ys = [p[1] for p in all_points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        # 版型尺寸
        pattern_width = max_x - min_x
        pattern_height = max_y - min_y

        # 边距
        padding = 30  # 显示边距

        # SVG画布尺寸（按缩放后计算）
        svg_width = (pattern_width * self.unit_scale * self.display_scale + padding * 2)
        svg_height = (pattern_height * self.unit_scale * self.display_scale + padding * 2)

        # 计算坐标变换函数
        def to_svg(x: float, y: float) -> Tuple[float, float]:
            """将版型坐标转换为SVG坐标"""
            # 版型坐标 -> 标准化坐标 (0-1)
            nx = (x - min_x) / pattern_width
            ny = (y - min_y) / pattern_height

            # 标准化坐标 -> SVG坐标
            # SVG Y轴向下，所以ny需要翻转
            sx = padding + nx * pattern_width * self.unit_scale * self.display_scale
            sy = svg_height - padding - ny * pattern_height * self.unit_scale * self.display_scale
            return (sx, sy)

        # 构建SVG内容
        svg_content = []
        svg_content.append(f'<?xml version="1.0" encoding="UTF-8"?>')
        svg_content.append(f'<svg xmlns="http://www.w3.org/2000/svg" ')
        svg_content.append(f'     width="{svg_width:.2f}" ')
        svg_content.append(f'     height="{svg_height:.2f}" ')
        svg_content.append(f'     viewBox="0 0 {svg_width:.2f} {svg_height:.2f}">')

        # 背景
        svg_content.append(f'  <rect x="0" y="0" width="{svg_width:.2f}" height="{svg_height:.2f}" fill="#f8f9fa"/>')

        # 定义箭头标记
        svg_content.append(f'  <defs>')
        svg_content.append(f'    <marker id="arrow-end" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">')
        svg_content.append(f'      <polygon points="0 0, 10 3.5, 0 7" fill="#666"/>')
        svg_content.append(f'    </marker>')
        svg_content.append(f'    <marker id="arrow-start" markerWidth="10" markerHeight="7" refX="1" refY="3.5" orient="auto">')
        svg_content.append(f'      <polygon points="10 0, 0 3.5, 10 7" fill="#666"/>')
        svg_content.append(f'    </marker>')
        svg_content.append(f'  </defs>')

        # 绘制参考线
        if include_reference:
            svg_content.extend(self._draw_reference_lines(points, to_svg))

        # 绘制后片（步骤1参考线/大矩形 + 步骤2后腰头 + 步骤3后立裆/落档）
        if back_points is not None:
            svg_content.extend(self._draw_back_panel(back_points, back_offset_x, to_svg))

        # 绘制轮廓线
        svg_content.extend(self._draw_outline(points, to_svg))

        # 绘制关键点
        svg_content.extend(self._draw_points(points, to_svg))

        # 绘制尺寸标注
        if include_dimensions:
            svg_content.extend(self._draw_dimensions(points, to_svg, min_x, max_x, min_y, max_y))

        # 添加图例
        svg_content.extend(self._draw_legend(20, svg_height - 100))

        svg_content.append(f'</svg>')

        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(svg_content))

        print(f"SVG文件已保存至: {output_path}")

    def _draw_reference_lines(self, points: PatternPoints, to_svg) -> List[str]:
        """绘制参考线"""
        lines = []
        bbox = points.bounding_box

        lines.append(f'  <!-- 参考线 -->')
        lines.append(f'  <g stroke="#4a90d9" stroke-width="1" stroke-dasharray="8,4">')

        # 外侧缝参考线 (X=0)
        start = to_svg(bbox.outer_seam_x, bbox.hem_y - 10)
        end = to_svg(bbox.outer_seam_x, bbox.waist_y + 10)
        lines.append(f'    <line x1="{start[0]:.2f}" y1="{start[1]:.2f}" x2="{end[0]:.2f}" y2="{end[1]:.2f}"/>')

        # 内侧缝参考线
        start = to_svg(bbox.inner_seam_x, bbox.hem_y - 10)
        end = to_svg(bbox.inner_seam_x, bbox.waist_y + 10)
        lines.append(f'    <line x1="{start[0]:.2f}" y1="{start[1]:.2f}" x2="{end[0]:.2f}" y2="{end[1]:.2f}"/>')

        # 裤中线
        start = to_svg(points.center_crease_x, bbox.hem_y - 10)
        end = to_svg(points.center_crease_x, bbox.waist_y + 10)
        lines.append(f'    <line x1="{start[0]:.2f}" y1="{start[1]:.2f}" x2="{end[0]:.2f}" y2="{end[1]:.2f}"/>')

        # 水平参考线
        y_positions = [
            bbox.hem_y,
            bbox.knee_y,
            bbox.crotch_y,
            bbox.hip_y,
            bbox.waist_y
        ]

        for y in y_positions:
            start = to_svg(-5, y)
            end = to_svg(bbox.inner_seam_x + 10, y)
            lines.append(f'    <line x1="{start[0]:.2f}" y1="{start[1]:.2f}" x2="{end[0]:.2f}" y2="{end[1]:.2f}"/>')

        lines.append(f'  </g>')
        return lines

    def _draw_back_panel(self, back_points: BackPatternPoints, offset_x: float, to_svg) -> List[str]:
        """绘制后片（步骤1参考线/大矩形 + 步骤2后腰头线 + 步骤3后立裆/落档）

        后片整体沿X轴正向偏移 offset_x，放在前片右侧。
        """
        bbox = back_points.bounding_box
        lines = []
        lines.append(f'  <!-- 后片参考线与大矩形 -->')
        lines.append(f'  <g stroke="#9b59b6" stroke-width="1" stroke-dasharray="8,4">')

        # 外侧缝 / 内侧缝 / 裤中线 垂直参考线
        for vx in (bbox.outer_seam_x, bbox.inner_seam_x, back_points.center_crease_x):
            start = to_svg(vx + offset_x, bbox.hem_y - 10)
            end = to_svg(vx + offset_x, bbox.waist_y + 10)
            lines.append(f'    <line x1="{start[0]:.2f}" y1="{start[1]:.2f}" x2="{end[0]:.2f}" y2="{end[1]:.2f}"/>')

        # 五条水平参考线：脚口 / 膝围 / 立裆 / 臀围 / 腰围
        for y in (bbox.hem_y, bbox.knee_y, bbox.crotch_y, bbox.hip_y, bbox.waist_y):
            start = to_svg(-5 + offset_x, y)
            end = to_svg(bbox.inner_seam_x + 10 + offset_x, y)
            lines.append(f'    <line x1="{start[0]:.2f}" y1="{start[1]:.2f}" x2="{end[0]:.2f}" y2="{end[1]:.2f}"/>')

        lines.append(f'  </g>')

        # 大矩形框架（实体描边，标示后片当前范围）
        corners = [to_svg(cx + offset_x, cy) for (cx, cy) in bbox.get_corners()]
        pts = ' '.join(f'{x:.2f},{y:.2f}' for x, y in corners)
        lines.append(f'  <polygon points="{pts}" fill="none" stroke="#8e44ad" stroke-width="2"/>')

        # ===== 步骤2: 后腰头线（后腰围外缝顶点 → 后腰围内缝顶点）=====
        w = back_points.waist
        wo = to_svg(w.back_waist_outer[0] + offset_x, w.back_waist_outer[1])
        wi = to_svg(w.back_waist_inner[0] + offset_x, w.back_waist_inner[1])
        lines.append(f'  <line x1="{wo[0]:.2f}" y1="{wo[1]:.2f}" x2="{wi[0]:.2f}" y2="{wi[1]:.2f}" '
                     f'stroke="#c0392b" stroke-width="2.5"/>')

        # ===== 步骤3: 落档线 + 后立裆宽顶点 =====
        c = back_points.crotch
        d0 = to_svg(c.drop_crotch_line[0][0] + offset_x, c.drop_crotch_line[0][1])
        d1 = to_svg(c.drop_crotch_line[1][0] + offset_x, c.drop_crotch_line[1][1])
        lines.append(f'  <line x1="{d0[0]:.2f}" y1="{d0[1]:.2f}" x2="{d1[0]:.2f}" y2="{d1[1]:.2f}" '
                     f'stroke="#16a085" stroke-width="2.5"/>')

        # ===== 步骤4: 后浪曲线（后腰围内缝顶点 → 臀围内缝顶点 → 后立裆宽顶点）=====
        rise = back_points.rise
        rise_pts = [to_svg(rx + offset_x, ry) for (rx, ry) in rise.rise_curve]
        rise_str = ' '.join(f'{x:.2f},{y:.2f}' for x, y in rise_pts)
        lines.append(f'  <polyline points="{rise_str}" fill="none" '
                     f'stroke="#2980b9" stroke-width="2.5"/>')

        # 困势线（构造辅助线：臀围内缝顶点 → 困势顶点，虚线）
        kb0 = to_svg(rise.hip_inner_point[0] + offset_x, rise.hip_inner_point[1])
        kb1 = to_svg(rise.kunshi_point[0] + offset_x, rise.kunshi_point[1])
        lines.append(f'  <line x1="{kb0[0]:.2f}" y1="{kb0[1]:.2f}" x2="{kb1[0]:.2f}" y2="{kb1[1]:.2f}" '
                     f'stroke="#2980b9" stroke-width="1" stroke-dasharray="4,3" opacity="0.6"/>')

        # 关键点标记
        def mark(p, color):
            mp = to_svg(p[0] + offset_x, p[1])
            lines.append(f'  <circle cx="{mp[0]:.2f}" cy="{mp[1]:.2f}" r="3" fill="{color}"/>')

        # ===== 步骤6: 实际膝围与脚口顶点（宽度线 + 标记）=====
        kh = back_points.knee_hem
        for (pa, pb) in ((kh.knee_outer, kh.knee_inner), (kh.hem_outer, kh.hem_inner)):
            a = to_svg(pa[0] + offset_x, pa[1])
            b = to_svg(pb[0] + offset_x, pb[1])
            lines.append(f'  <line x1="{a[0]:.2f}" y1="{a[1]:.2f}" x2="{b[0]:.2f}" y2="{b[1]:.2f}" '
                         f'stroke="#e67e22" stroke-width="2"/>')

        # ===== 步骤7: 内缝与外缝曲线（主轮廓）=====
        for curve in (back_points.seam.outer_seam_curve, back_points.seam.inner_seam_curve):
            pts = [to_svg(sx + offset_x, sy) for (sx, sy) in curve]
            pts_str = ' '.join(f'{x:.2f},{y:.2f}' for x, y in pts)
            lines.append(f'  <polyline points="{pts_str}" fill="none" '
                         f'stroke="#2c3e50" stroke-width="2.5"/>')

        # ===== 步骤8: 最终腰围线（后翘，垂直于后浪）=====
        wf = back_points.waist_final
        wl = [to_svg(p[0] + offset_x, p[1]) for p in wf.waistline]
        wl_str = ' '.join(f'{x:.2f},{y:.2f}' for x, y in wl)
        lines.append(f'  <polyline points="{wl_str}" fill="none" '
                     f'stroke="#e84393" stroke-width="2.5"/>')
        # 后浪切线延长段（虚线）
        re0 = to_svg(wf.rise_extension[0][0] + offset_x, wf.rise_extension[0][1])
        re1 = to_svg(wf.rise_extension[1][0] + offset_x, wf.rise_extension[1][1])
        lines.append(f'  <line x1="{re0[0]:.2f}" y1="{re0[1]:.2f}" x2="{re1[0]:.2f}" y2="{re1[1]:.2f}" '
                     f'stroke="#3498db" stroke-width="2.5" stroke-dasharray="6,3"/>')
        # 外缝切线延长段（虚线）
        oe0 = to_svg(wf.outer_extension[0][0] + offset_x, wf.outer_extension[0][1])
        oe1 = to_svg(wf.outer_extension[1][0] + offset_x, wf.outer_extension[1][1])
        lines.append(f'  <line x1="{oe0[0]:.2f}" y1="{oe0[1]:.2f}" x2="{oe1[0]:.2f}" y2="{oe1[1]:.2f}" '
                     f'stroke="#e67e22" stroke-width="2.5" stroke-dasharray="6,3"/>')

        # ===== 步骤9: 腰省（V 形）=====
        d = back_points.dart
        for (pa, pb) in ((d.dart_outer, d.dart_tip), (d.dart_inner, d.dart_tip)):
            a = to_svg(pa[0] + offset_x, pa[1])
            b = to_svg(pb[0] + offset_x, pb[1])
            lines.append(f'  <line x1="{a[0]:.2f}" y1="{a[1]:.2f}" x2="{b[0]:.2f}" y2="{b[1]:.2f}" '
                         f'stroke="#9b59b6" stroke-width="2"/>')

        # ===== 步骤10: 折叠腰头（模拟折叠腰省后画顺的 4cm 腰头）=====
        fw = back_points.folded_waistband
        if fw is not None:
            top = [to_svg(p[0] + offset_x, p[1]) for p in fw.top_curve]
            bot = [to_svg(p[0] + offset_x, p[1]) for p in fw.bottom_curve]
            # 腰头填充区域：上曲线 + 下曲线反向闭合
            region = top + list(reversed(bot))
            reg_str = ' '.join(f'{x:.2f},{y:.2f}' for x, y in region)
            lines.append(f'  <polygon points="{reg_str}" fill="#1abc9c" fill-opacity="0.18" stroke="none"/>')
            # 上腰头曲线（折叠后的最终腰口）
            lines.append(f'  <polyline points="{(" ".join(f"{x:.2f},{y:.2f}" for x, y in top))}" '
                         f'fill="none" stroke="#1abc9c" stroke-width="2.5"/>')
            # 下腰头曲线
            lines.append(f'  <polyline points="{(" ".join(f"{x:.2f},{y:.2f}" for x, y in bot))}" '
                         f'fill="none" stroke="#1abc9c" stroke-width="2"/>')

        mark(w.back_waist_outer, '#c0392b')   # 后腰围外缝顶点
        mark(w.back_waist_inner, '#c0392b')   # 后腰围内缝顶点
        mark(back_points.waist_final.new_waist_outer, '#e84393')  # 新腰围外缝顶点
        mark(back_points.waist_final.new_waist_inner, '#e84393')  # 新腰围内缝顶点（后翘）
        mark(back_points.dart.dart_tip, '#9b59b6')  # 省尖
        mark(back_points.seam.hip_outer_point, '#2c3e50')  # 后臀围外缝顶点
        mark(back_points.rise.hip_inner_point, '#2980b9')  # 臀围内缝顶点（后浪中点）
        mark(back_points.rise.kunshi_point, '#2980b9')     # 困势顶点 K
        mark(back_points.rise.helper_point, '#8e44ad')     # 后浪辅助点 H
        mark(kh.knee_outer, '#e67e22')  # 实际膝围外缝顶点
        mark(kh.knee_inner, '#e67e22')  # 实际膝围内缝顶点
        mark(kh.hem_outer, '#e67e22')   # 实际脚口外缝顶点
        mark(kh.hem_inner, '#e67e22')   # 实际脚口内缝顶点
        mark(c.crotch_extend_point, '#16a085')  # 立裆延伸点（未落档）
        mark(c.back_crotch_point, '#16a085')    # 后立裆宽顶点（落档后）

        # 后片标注（放在大矩形内部上方，避免超出画布顶端被裁切）
        label = to_svg(offset_x + bbox.inner_seam_x / 2, bbox.waist_y - 5)
        lines.append(f'  <text x="{label[0]:.2f}" y="{label[1]:.2f}" font-size="14" '
                     f'text-anchor="middle" fill="#8e44ad" font-weight="bold">后片</text>')
        return lines

    def _draw_outline(self, points: PatternPoints, to_svg) -> List[str]:
        """绘制轮廓线"""
        elements = []
        elements.append(f'  <!-- 轮廓线 -->')

        # 构建完整闭合轮廓（裤身）
        outline = []

        # 1. 腰围外 -> 外侧缝 -> 脚口外
        outline.extend(reversed(points.outer_seam_curve))

        # 2. 脚口外 -> 脚口内
        outline.append(points.knee_hem.hem_inner)

        # 3. 脚口内 -> 内侧缝 -> 立裆宽顶点
        outline.extend(points.inner_seam_curve[1:])

        # 4. 立裆宽顶点 -> 前浪曲线 -> 腰围内缝参考
        # 前浪曲线是: [腰围内缝参考, ..., 立裆宽顶点]
        # reversed后是: [立裆宽顶点, ..., 腰围内缝参考]
        # 我们需要去掉最后那个腰围内缝参考点，直接连到腰围内缝顶点
        front_reversed = list(reversed(points.front_rise_curve))
        outline.extend(front_reversed[:-1])  # 去掉最后一个点（腰围内缝参考）

        # 5. 直接添加腰围内缝顶点
        outline.append(points.waist.waist_inner_final)

        # 6. 腰围内缝顶点 -> 腰围线 -> 腰围外
        # 腰围线是: [腰围外, ..., 腰围内缝顶点]
        # reversed后是: [腰围内缝顶点, ..., 腰围外]
        waist_reversed = list(reversed(points.waistline_curve))
        outline.extend(waist_reversed[1:])  # 去掉第一个点（腰围内缝顶点，避免重复）

        # 转换点
        svg_points = [to_svg(x, y) for x, y in outline]
        points_str = ' '.join([f'{x:.2f},{y:.2f}' for x, y in svg_points])

        # 描边
        elements.append(f'  <polygon points="{points_str}" fill="none" stroke="#2c3e50" stroke-width="2.5"/>')

        # 如果有下腰头，绘制腰头区域
        if hasattr(points, 'waistband') and hasattr(points, 'lower_waistline_curve'):
            elements.extend(self._draw_waistband(points, to_svg))

        # 如果有前门襟，绘制前门襟
        if hasattr(points, 'front_fly'):
            elements.extend(self._draw_front_fly(points, to_svg))

        # 如果有月牙袋，绘制月牙袋
        if hasattr(points, 'crescent_pocket'):
            elements.extend(self._draw_crescent_pocket(points, to_svg))

        # 如果有袋贴，绘制袋贴
        if hasattr(points, 'pocket_patch'):
            elements.extend(self._draw_pocket_patch(points, to_svg))

        # 如果有袋布，绘制袋布
        if hasattr(points, 'pocket_bag'):
            elements.extend(self._draw_pocket_bag(points, to_svg))

        # 如果有小表袋，绘制小表袋
        if hasattr(points, 'watch_pocket'):
            elements.extend(self._draw_watch_pocket(points, to_svg))

        return elements

    def _draw_waistband(self, points: PatternPoints, to_svg) -> List[str]:
        """绘制腰头区域"""
        elements = []
        elements.append(f'  <!-- 腰头 -->')

        wb = points.waistband

        # 构建腰头闭合区域：
        # 上腰头外 -> 上腰头内 -> 下腰头内 -> 下腰头外 -> 上腰头外
        waistband_outline = []

        # 1. 上腰头曲线（从外到内）
        waistband_outline.extend(points.waistline_curve)

        # 2. 下腰头曲线（从内到外，需要反转）
        waistband_outline.extend(reversed(points.lower_waistline_curve))

        # 转换点
        svg_points = [to_svg(x, y) for x, y in waistband_outline]
        points_str = ' '.join([f'{x:.2f},{y:.2f}' for x, y in svg_points])

        # 腰头描边
        elements.append(f'  <polygon points="{points_str}" fill="none" stroke="#e67e22" stroke-width="2"/>')

        # 单独绘制下腰头曲线（突出显示）
        lower_svg_points = [to_svg(x, y) for x, y in points.lower_waistline_curve]
        lower_points_str = ' '.join([f'{x:.2f},{y:.2f}' for x, y in lower_svg_points])
        elements.append(f'  <polyline points="{lower_points_str}" fill="none" stroke="#e67e22" stroke-width="3"/>')

        return elements

    def _draw_front_fly(self, points: PatternPoints, to_svg) -> List[str]:
        """绘制前门襟"""
        elements = []
        elements.append(f'  <!-- 前门襟 -->')

        fly = points.front_fly

        # 绘制门襟线（从起点到弧起点）- 实线（实际轮廓）
        start_svg = to_svg(fly.fly_start_point[0], fly.fly_start_point[1])
        arc_start_svg = to_svg(fly.fly_end_point[0], fly.fly_end_point[1])
        elements.append(f'    <line x1="{start_svg[0]:.2f}" y1="{start_svg[1]:.2f}" x2="{arc_start_svg[0]:.2f}" y2="{arc_start_svg[1]:.2f}" stroke="#27ae60" stroke-width="3"/>')

        # 绘制门襟线（从弧起点到内端点）- 虚线（辅助线）
        inner_end_svg = to_svg(fly.fly_inner_end[0], fly.fly_inner_end[1])
        elements.append(f'    <line x1="{arc_start_svg[0]:.2f}" y1="{arc_start_svg[1]:.2f}" x2="{inner_end_svg[0]:.2f}" y2="{inner_end_svg[1]:.2f}" stroke="#27ae60" stroke-width="2" stroke-dasharray="5,3"/>')

        # 绘制垂直线（从内端点到外端点）- 虚线（辅助线）
        outer_end_svg = to_svg(fly.fly_outer_end[0], fly.fly_outer_end[1])
        elements.append(f'    <line x1="{inner_end_svg[0]:.2f}" y1="{inner_end_svg[1]:.2f}" x2="{outer_end_svg[0]:.2f}" y2="{outer_end_svg[1]:.2f}" stroke="#27ae60" stroke-width="2" stroke-dasharray="5,3"/>')

        # 绘制门襟弧线
        fly_svg_points = [to_svg(x, y) for x, y in fly.fly_curve]
        fly_points_str = ' '.join([f'{x:.2f},{y:.2f}' for x, y in fly_svg_points])
        elements.append(f'    <polyline points="{fly_points_str}" fill="none" stroke="#27ae60" stroke-width="3"/>')

        # 绘制门襟闭合区域（填充）
        # 从下腰头门襟点 -> 门襟线 -> 弧起点 -> 弧线 -> 门襟外端点 -> 前浪 -> 下腰头内缝顶点 -> 下腰头 -> 门襟起点
        fly_outline = []
        fly_outline.append(fly.fly_start_point)  # 下腰头门襟点
        fly_outline.append(fly.fly_end_point)    # 沿着门襟线到弧起点
        fly_outline.extend(fly.fly_curve)        # 沿着弧线到门襟外端点
        # 从门襟外端点沿着前浪到下腰头内缝顶点
        found_outer = False
        for p in points.front_rise_curve:
            if not found_outer and abs(p[0] - fly.fly_outer_end[0]) < 0.2 and abs(p[1] - fly.fly_outer_end[1]) < 0.2:
                found_outer = True
            if found_outer:
                fly_outline.append(p)
            if hasattr(points, 'waistband') and found_outer:
                dist = point_distance(p, points.waistband.lower_waist_inner)
                if dist < 0.3:
                    break
        # 添加下腰头内缝顶点
        if hasattr(points, 'waistband'):
            fly_outline.append(points.waistband.lower_waist_inner)
            # 沿着下腰头曲线从内到外，直到门襟起点
            found_lower_inner = False
            for p in reversed(points.lower_waistline_curve):
                if not found_lower_inner:
                    dist = point_distance(p, points.waistband.lower_waist_inner)
                    if dist < 0.2:
                        found_lower_inner = True
                if found_lower_inner:
                    fly_outline.append(p)
                    dist = point_distance(p, fly.fly_start_point)
                    if dist < 0.3:
                        break
        # 确保闭合
        fly_outline.append(fly.fly_start_point)

        return elements

    def _draw_crescent_pocket(self, points: PatternPoints, to_svg) -> List[str]:
        """绘制月牙袋"""
        elements = []
        elements.append(f'  <!-- 月牙袋 -->')

        pocket = points.crescent_pocket
        waistband = points.waistband

        # 绘制月牙袋弧线（口袋开口）
        pocket_svg_points = [to_svg(x, y) for x, y in pocket.pocket_curve]
        pocket_points_str = ' '.join([f'{x:.2f},{y:.2f}' for x, y in pocket_svg_points])
        elements.append(f'    <polyline points="{pocket_points_str}" fill="none" stroke="#9b59b6" stroke-width="3"/>')

        # 绘制月牙袋省道弧线
        dart_curve_svg = [to_svg(x, y) for x, y in pocket.pocket_dart_curve]
        dart_curve_str = ' '.join([f'{x:.2f},{y:.2f}' for x, y in dart_curve_svg])
        elements.append(f'    <polyline points="{dart_curve_str}" fill="none" stroke="#9b59b6" stroke-width="2"/>')

        # 绘制月牙袋省道的两条垂直线
        width_start = to_svg(pocket.pocket_width[0], pocket.pocket_width[1])
        width_end = to_svg(pocket.pocket_dart_line_width[0], pocket.pocket_dart_line_width[1])
        elements.append(f'    <line x1="{width_start[0]:.2f}" y1="{width_start[1]:.2f}" x2="{width_end[0]:.2f}" y2="{width_end[1]:.2f}" stroke="#9b59b6" stroke-width="2"/>')

        dart_start = to_svg(pocket.pocket_dart[0], pocket.pocket_dart[1])
        dart_end = to_svg(pocket.pocket_dart_line_dart[0], pocket.pocket_dart_line_dart[1])
        elements.append(f'    <line x1="{dart_start[0]:.2f}" y1="{dart_start[1]:.2f}" x2="{dart_end[0]:.2f}" y2="{dart_end[1]:.2f}" stroke="#9b59b6" stroke-width="2"/>')

        return elements

    def _draw_pocket_patch(self, points: PatternPoints, to_svg) -> List[str]:
        """绘制袋贴"""
        elements = []
        elements.append(f'  <!-- 袋贴 -->')

        patch = points.pocket_patch
        pocket = points.crescent_pocket
        waistband = points.waistband

        # 绘制袋贴弧线
        patch_svg_points = [to_svg(x, y) for x, y in patch.patch_curve]
        patch_points_str = ' '.join([f'{x:.2f},{y:.2f}' for x, y in patch_svg_points])
        elements.append(f'    <polyline points="{patch_points_str}" fill="none" stroke="#1abc9c" stroke-width="3"/>')

        # 构建袋贴闭合区域（袋贴贴片）：
        # 袋贴下腰头顶点 -> 袋贴弧线 -> 袋贴外缝顶点 -> 外侧缝(向上) -> 月牙袋外缝顶点
        # -> 月牙袋省道弧线(反向) -> 月牙袋省道点 -> 下腰头(向内) -> 袋贴下腰头顶点
        patch_outline = []
        # 1. 袋贴弧线
        patch_outline.extend(patch.patch_curve)

        # 2. 沿外侧缝从袋贴外缝顶点向上到月牙袋外缝顶点
        found_patch_outer = False
        for p in points.outer_seam_curve:
            if not found_patch_outer and point_distance(p, patch.patch_outer_seam) < 0.3:
                found_patch_outer = True
            if found_patch_outer:
                patch_outline.append(p)
            if found_patch_outer and point_distance(p, pocket.pocket_outer) < 0.3:
                break

        # 3. 沿月牙袋省道弧线反向（外缝顶点 -> 省道点）
        patch_outline.extend(reversed(pocket.pocket_dart_curve))

        # 4. 沿下腰头从月牙袋省道点向内到袋贴下腰头顶点
        found_dart = False
        for p in points.lower_waistline_curve:
            if not found_dart and point_distance(p, pocket.pocket_dart) < 0.3:
                found_dart = True
            if found_dart:
                patch_outline.append(p)
            if found_dart and point_distance(p, patch.patch_lower_waist) < 0.3:
                break

        # 转换并绘制闭合区域
        svg_outline = [to_svg(x, y) for x, y in patch_outline]
        outline_str = ' '.join([f'{x:.2f},{y:.2f}' for x, y in svg_outline])
        elements.append(f'    <polygon points="{outline_str}" fill="none" stroke="#1abc9c" stroke-width="2"/>')

        return elements

    def _draw_pocket_bag(self, points: PatternPoints, to_svg) -> List[str]:
        """绘制袋布"""
        elements = []
        elements.append(f'  <!-- 袋布 -->')

        bag = points.pocket_bag
        color = '#e84393'

        def to_pts(curve):
            sp = [to_svg(x, y) for x, y in curve]
            return ' '.join([f'{x:.2f},{y:.2f}' for x, y in sp])

        # 袋布线（上腰头顶点 → 内端点）
        elements.append(f'    <polyline points="{to_pts(bag.bag_line)}" fill="none" stroke="{color}" stroke-width="3"/>')
        # 底边（内端点 → 拐点）
        elements.append(f'    <polyline points="{to_pts(bag.bag_bottom_edge)}" fill="none" stroke="{color}" stroke-width="3"/>')
        # 袋布弧线（拐点 → 外缝顶点）
        elements.append(f'    <polyline points="{to_pts(bag.bag_curve)}" fill="none" stroke="{color}" stroke-width="3"/>')

        # 袋布闭合区域：袋布线 + 底边 + 袋布弧线 + 顶边
        bag_outline = []
        bag_outline.extend(bag.bag_line)
        bag_outline.extend(bag.bag_bottom_edge[1:])
        bag_outline.extend(bag.bag_curve[1:])
        bag_outline.extend(bag.bag_top_edge[1:])
        elements.append(f'    <polygon points="{to_pts(bag_outline)}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="5,3"/>')

        return elements

    def _draw_watch_pocket(self, points: PatternPoints, to_svg) -> List[str]:
        """绘制小表袋"""
        elements = []
        elements.append(f'  <!-- 小表袋 -->')

        wp = points.watch_pocket
        color = '#f1c40f'

        def to_pts(curve):
            sp = [to_svg(x, y) for x, y in curve]
            return ' '.join([f'{x:.2f},{y:.2f}' for x, y in sp])

        # 顶边（上外 → 上内）
        elements.append(f'    <polyline points="{to_pts([wp.outer_upper, wp.inner_upper])}" fill="none" stroke="{color}" stroke-width="3"/>')
        # 外线（上外 → 下外）
        elements.append(f'    <polyline points="{to_pts(wp.outer_line)}" fill="none" stroke="{color}" stroke-width="3"/>')
        # 内线（上内 → 下内）
        elements.append(f'    <polyline points="{to_pts(wp.inner_line)}" fill="none" stroke="{color}" stroke-width="3"/>')
        # 底边（沿袋贴弧线 下内 → 下外）
        elements.append(f'    <polyline points="{to_pts(wp.bottom_curve)}" fill="none" stroke="{color}" stroke-width="3"/>')

        # 小表袋闭合区域
        wp_outline = []
        wp_outline.extend([wp.outer_upper, wp.inner_upper])
        wp_outline.extend(wp.inner_line[1:])        # 上内 → 下内
        wp_outline.extend(wp.bottom_curve[1:])       # 下内 → 下外
        wp_outline.extend(list(reversed(wp.outer_line))[1:])  # 下外 → 上外
        elements.append(f'    <polygon points="{to_pts(wp_outline)}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="5,3"/>')

        return elements

    def _draw_points(self, points: PatternPoints, to_svg) -> List[str]:
        """绘制关键点"""
        elements = []
        elements.append(f'  <!-- 关键点 -->')

        # 关键点列表
        key_points = [
            ('腰围外', points.waist.waist_outer),
            ('腰围内', points.waist.waist_inner_final),
            ('臀围外', (points.bounding_box.outer_seam_x, points.bounding_box.hip_y)),
            ('臀围内', points.front_rise.hip_inner_point),
            ('膝围外', points.knee_hem.knee_outer),
            ('膝围内', points.knee_hem.knee_inner),
            ('脚口外', points.knee_hem.hem_outer),
            ('脚口内', points.knee_hem.hem_inner),
            ('立裆点', points.front_rise.crotch_extension_point),
        ]

        # 添加腰头关键点
        if hasattr(points, 'waistband'):
            key_points.append(('下腰外', points.waistband.lower_waist_outer))
            key_points.append(('下腰内', points.waistband.lower_waist_inner))

        # 添加前门襟关键点
        if hasattr(points, 'front_fly'):
            key_points.append(('门襟起', points.front_fly.fly_start_point))
            key_points.append(('门襟内', points.front_fly.fly_inner_end))
            key_points.append(('门襟外', points.front_fly.fly_outer_end))
            key_points.append(('门襟终', points.front_fly.fly_end_point))

        # 添加月牙袋关键点
        if hasattr(points, 'crescent_pocket'):
            key_points.append(('袋外点', points.crescent_pocket.pocket_outer))
            key_points.append(('袋宽点', points.crescent_pocket.pocket_width))
            key_points.append(('袋省点', points.crescent_pocket.pocket_dart))
            key_points.append(('袋省线宽', points.crescent_pocket.pocket_dart_line_width))
            key_points.append(('袋省线省', points.crescent_pocket.pocket_dart_line_dart))

        # 添加袋贴关键点
        if hasattr(points, 'pocket_patch'):
            key_points.append(('贴腰点', points.pocket_patch.patch_lower_waist))
            key_points.append(('贴外点', points.pocket_patch.patch_outer_seam))

        # 添加袋布关键点
        if hasattr(points, 'pocket_bag'):
            key_points.append(('布腰点', points.pocket_bag.bag_upper_waist))
            key_points.append(('布内点', points.pocket_bag.bag_inner_end))
            key_points.append(('布拐点', points.pocket_bag.bag_corner))
            key_points.append(('布外点', points.pocket_bag.bag_outer_seam))

        # 添加小表袋关键点
        if hasattr(points, 'watch_pocket'):
            key_points.append(('表上外', points.watch_pocket.outer_upper))
            key_points.append(('表下外', points.watch_pocket.outer_lower))
            key_points.append(('表上内', points.watch_pocket.inner_upper))
            key_points.append(('表下内', points.watch_pocket.inner_lower))

        for name, (x, y) in key_points:
            sx, sy = to_svg(x, y)
            r = 5

            # 十字线
            elements.append(f'  <line x1="{sx - r*2:.2f}" y1="{sy:.2f}" x2="{sx + r*2:.2f}" y2="{sy:.2f}" stroke="#e74c3c" stroke-width="1.5"/>')
            elements.append(f'  <line x1="{sx:.2f}" y1="{sy - r*2:.2f}" x2="{sx:.2f}" y2="{sy + r*2:.2f}" stroke="#e74c3c" stroke-width="1.5"/>')

            # 圆点
            elements.append(f'  <circle cx="{sx:.2f}" cy="{sy:.2f}" r="{r:.2f}" fill="none" stroke="#e74c3c" stroke-width="2"/>')

        return elements

    def _draw_dimensions(self, points: PatternPoints, to_svg, min_x: float, max_x: float, min_y: float, max_y: float) -> List[str]:
        """绘制尺寸标注"""
        elements = []
        elements.append(f'  <!-- 尺寸标注 -->')
        elements.append(f'  <g font-family="Arial, sans-serif" font-size="12" fill="#555">')

        bbox = points.bounding_box

        # 裤长标注（左侧）
        dim_x = min_x - 1.5
        start = to_svg(dim_x, bbox.hem_y)
        end = to_svg(dim_x, bbox.waist_y)
        elements.append(f'    <line x1="{start[0]:.2f}" y1="{start[1]:.2f}" x2="{end[0]:.2f}" y2="{end[1]:.2f}" stroke="#666" stroke-width="1" marker-start="url(#arrow-start)" marker-end="url(#arrow-end)"/>')

        # 裤长文字
        mid_y = (start[1] + end[1]) / 2
        elements.append(f'    <text x="{start[0] - 8:.2f}" y="{mid_y:.2f}" text-anchor="end" dominant-baseline="middle">{bbox.waist_y:.0f}</text>')

        # 臀围宽标注（顶部）
        dim_y = max_y + 1.5
        start = to_svg(bbox.outer_seam_x, dim_y)
        end = to_svg(bbox.inner_seam_x, dim_y)
        elements.append(f'    <line x1="{start[0]:.2f}" y1="{start[1]:.2f}" x2="{end[0]:.2f}" y2="{end[1]:.2f}" stroke="#666" stroke-width="1" marker-start="url(#arrow-start)" marker-end="url(#arrow-end)"/>')

        # 臀围宽文字
        mid_x = (start[0] + end[0]) / 2
        elements.append(f'    <text x="{mid_x:.2f}" y="{start[1] - 8:.2f}" text-anchor="middle">{bbox.inner_seam_x:.1f}</text>')

        # 膝围宽标注
        dim_y_knee = bbox.knee_y + 2
        start = to_svg(points.knee_hem.knee_outer[0], dim_y_knee)
        end = to_svg(points.knee_hem.knee_inner[0], dim_y_knee)
        elements.append(f'    <line x1="{start[0]:.2f}" y1="{start[1]:.2f}" x2="{end[0]:.2f}" y2="{end[1]:.2f}" stroke="#666" stroke-width="1" marker-start="url(#arrow-start)" marker-end="url(#arrow-end)"/>')

        knee_width = points.knee_hem.knee_inner[0] - points.knee_hem.knee_outer[0]
        mid_x_knee = (start[0] + end[0]) / 2
        elements.append(f'    <text x="{mid_x_knee:.2f}" y="{start[1] - 8:.2f}" text-anchor="middle">{knee_width:.1f}</text>')

        # 脚口宽标注
        dim_y_hem = bbox.hem_y - 1.5
        start = to_svg(points.knee_hem.hem_outer[0], dim_y_hem)
        end = to_svg(points.knee_hem.hem_inner[0], dim_y_hem)
        elements.append(f'    <line x1="{start[0]:.2f}" y1="{start[1]:.2f}" x2="{end[0]:.2f}" y2="{end[1]:.2f}" stroke="#666" stroke-width="1" marker-start="url(#arrow-start)" marker-end="url(#arrow-end)"/>')

        hem_width = points.knee_hem.hem_inner[0] - points.knee_hem.hem_outer[0]
        mid_x_hem = (start[0] + end[0]) / 2
        elements.append(f'    <text x="{mid_x_hem:.2f}" y="{start[1] + 16:.2f}" text-anchor="middle">{hem_width:.1f}</text>')

        elements.append(f'  </g>')
        return elements

    def _draw_legend(self, x: float, y: float) -> List[str]:
        """绘制图例"""
        elements = []
        elements.append(f'  <!-- 图例 -->')
        elements.append(f'  <g font-family="Arial, sans-serif" font-size="12">')

        # 图例项
        legend_items = [
            ('轮廓线', '#2c3e50', 'line'),
            ('腰头', '#e67e22', 'line'),
            ('前门襟', '#27ae60', 'line'),
            ('月牙袋', '#9b59b6', 'line'),
            ('袋贴', '#1abc9c', 'line'),
            ('袋布', '#e84393', 'line'),
            ('小表袋', '#f1c40f', 'line'),
            ('参考线', '#4a90d9', 'dashed'),
            ('关键点', '#e74c3c', 'circle'),
        ]

        for i, (name, color, style) in enumerate(legend_items):
            ly = y + i * 22

            if style == 'line':
                elements.append(f'    <line x1="{x:.2f}" y1="{ly:.2f}" x2="{x + 30:.2f}" y2="{ly:.2f}" stroke="{color}" stroke-width="2.5"/>')
            elif style == 'dashed':
                elements.append(f'    <line x1="{x:.2f}" y1="{ly:.2f}" x2="{x + 30:.2f}" y2="{ly:.2f}" stroke="{color}" stroke-width="2" stroke-dasharray="8,4"/>')
            elif style == 'circle':
                elements.append(f'    <circle cx="{x + 15:.2f}" cy="{ly:.2f}" r="6" fill="none" stroke="{color}" stroke-width="2"/>')

            elements.append(f'    <text x="{x + 42:.2f}" y="{ly + 4:.2f}" fill="#333">{name}</text>')

        # 标题
        elements.append(f'    <text x="{x:.2f}" y="{y - 15:.2f}" fill="#333" font-size="14" font-weight="bold">版型图例</text>')

        elements.append(f'  </g>')
        return elements
