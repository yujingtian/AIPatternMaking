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
            
            for (cx, cy) in bbox.get_corners():
                all_points.append((cx + back_offset_x, cy))
            all_points.append((back_points.crotch.back_crotch_point[0] + back_offset_x,
                               back_points.crotch.back_crotch_point[1]))
            all_points.append((back_offset_x - 5, bbox.hem_y))
            all_points.append((bbox.inner_seam_x + back_offset_x + 10, bbox.waist_y))
            for (rx, ry) in back_points.rise.rise_curve:
                all_points.append((rx + back_offset_x, ry))
            for curve in (back_points.seam.outer_seam_curve, back_points.seam.inner_seam_curve):
                for (sx, sy) in curve:
                    all_points.append((sx + back_offset_x, sy))
            for p in (back_points.waist_final.new_waist_inner, back_points.waist_final.new_waist_outer):
                all_points.append((p[0] + back_offset_x, p[1]))
            if back_points.waistband is not None:
                for (sx, sy) in back_points.waistband.lower_waist_curve:
                    all_points.append((sx + back_offset_x, sy))
            if back_points.jitou is not None:
                all_points.append((back_points.jitou.jitou_outer[0] + back_offset_x, back_points.jitou.jitou_outer[1]))
                all_points.append((back_points.jitou.jitou_inner[0] + back_offset_x, back_points.jitou.jitou_inner[1]))
            if back_points.back_pocket is not None:
                for (x, y) in back_points.back_pocket.pocket_outline:
                    all_points.append((x + back_offset_x, y))

        # 门襟裁片整体沿Y负向偏移，放在前片下方单独展示
        fly_panel_offset_y = 0.0
        if (hasattr(points, 'front_fly') and
                getattr(points.front_fly, 'fly_panel_outline', None)):
            panel_max_y = max(p[1] for p in points.front_fly.fly_panel_outline)
            fly_panel_offset_y = -(panel_max_y + 5.0)  # 裁片最高点位于脚口线下方5cm
            for (fx, fy) in points.front_fly.fly_panel_outline:
                all_points.append((fx, fy + fly_panel_offset_y))

        # 计算原始版型坐标的边界
        xs = [p[0] for p in all_points]
        ys = [p[1] for p in all_points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        pattern_width = max_x - min_x
        pattern_height = max_y - min_y
        padding = 30  

        svg_width = (pattern_width * self.unit_scale * self.display_scale + padding * 2)
        svg_height = (pattern_height * self.unit_scale * self.display_scale + padding * 2)

        def to_svg(x: float, y: float) -> Tuple[float, float]:
            nx = (x - min_x) / pattern_width
            ny = (y - min_y) / pattern_height
            sx = padding + nx * pattern_width * self.unit_scale * self.display_scale
            sy = svg_height - padding - ny * pattern_height * self.unit_scale * self.display_scale
            return (sx, sy)

        svg_content = []
        svg_content.append(f'<?xml version="1.0" encoding="UTF-8"?>')
        svg_content.append(f'<svg xmlns="http://www.w3.org/2000/svg" ')
        svg_content.append(f'     width="{svg_width:.2f}" ')
        svg_content.append(f'     height="{svg_height:.2f}" ')
        svg_content.append(f'     viewBox="0 0 {svg_width:.2f} {svg_height:.2f}">')
        svg_content.append(f'  <rect x="0" y="0" width="{svg_width:.2f}" height="{svg_height:.2f}" fill="#f8f9fa"/>')
        svg_content.append(f'  <defs>')
        svg_content.append(f'    <marker id="arrow-end" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">')
        svg_content.append(f'      <polygon points="0 0, 10 3.5, 0 7" fill="#666"/>')
        svg_content.append(f'    </marker>')
        svg_content.append(f'    <marker id="arrow-start" markerWidth="10" markerHeight="7" refX="1" refY="3.5" orient="auto">')
        svg_content.append(f'      <polygon points="10 0, 0 3.5, 10 7" fill="#666"/>')
        svg_content.append(f'    </marker>')
        svg_content.append(f'  </defs>')

        if include_reference:
            svg_content.extend(self._draw_reference_lines(points, to_svg))
        if back_points is not None:
            svg_content.extend(self._draw_back_panel(back_points, back_offset_x, to_svg))
        svg_content.extend(self._draw_outline(points, to_svg))
        svg_content.extend(self._draw_fly_panel(points, to_svg, fly_panel_offset_y))
        svg_content.extend(self._draw_points(points, to_svg))
        if include_dimensions:
            svg_content.extend(self._draw_dimensions(points, to_svg, min_x, max_x, min_y, max_y))
        
        svg_content.extend(self._draw_legend(20, svg_height - 100))
        svg_content.append(f'</svg>')

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(svg_content))
        print(f"SVG文件已保存至: {output_path}")

    def _draw_reference_lines(self, points: PatternPoints, to_svg) -> List[str]:
        lines = []
        bbox = points.bounding_box
        lines.append(f'  <!-- 参考线 -->')
        lines.append(f'  <g stroke="#4a90d9" stroke-width="1" stroke-dasharray="8,4">')
        start = to_svg(bbox.outer_seam_x, bbox.hem_y - 10)
        end = to_svg(bbox.outer_seam_x, bbox.waist_y + 10)
        lines.append(f'    <line x1="{start[0]:.2f}" y1="{start[1]:.2f}" x2="{end[0]:.2f}" y2="{end[1]:.2f}"/>')
        start = to_svg(bbox.inner_seam_x, bbox.hem_y - 10)
        end = to_svg(bbox.inner_seam_x, bbox.waist_y + 10)
        lines.append(f'    <line x1="{start[0]:.2f}" y1="{start[1]:.2f}" x2="{end[0]:.2f}" y2="{end[1]:.2f}"/>')
        start = to_svg(points.center_crease_x, bbox.hem_y - 10)
        end = to_svg(points.center_crease_x, bbox.waist_y + 10)
        lines.append(f'    <line x1="{start[0]:.2f}" y1="{start[1]:.2f}" x2="{end[0]:.2f}" y2="{end[1]:.2f}"/>')
        y_positions = [bbox.hem_y, bbox.knee_y, bbox.crotch_y, bbox.hip_y, bbox.waist_y]
        for y in y_positions:
            start = to_svg(-5, y)
            end = to_svg(bbox.inner_seam_x + 10, y)
            lines.append(f'    <line x1="{start[0]:.2f}" y1="{start[1]:.2f}" x2="{end[0]:.2f}" y2="{end[1]:.2f}"/>')
        lines.append(f'  </g>')
        return lines

    def _draw_back_panel(self, back_points: BackPatternPoints, offset_x: float, to_svg) -> List[str]:
        bbox = back_points.bounding_box
        lines = []
        lines.append(f'  <!-- 后片参考线与大矩形 -->')
        lines.append(f'  <g stroke="#9b59b6" stroke-width="1" stroke-dasharray="8,4">')
        for vx in (bbox.outer_seam_x, bbox.inner_seam_x, back_points.center_crease_x):
            start = to_svg(vx + offset_x, bbox.hem_y - 10)
            end = to_svg(vx + offset_x, bbox.waist_y + 10)
            lines.append(f'    <line x1="{start[0]:.2f}" y1="{start[1]:.2f}" x2="{end[0]:.2f}" y2="{end[1]:.2f}"/>')
        for y in (bbox.hem_y, bbox.knee_y, bbox.crotch_y, bbox.hip_y, bbox.waist_y):
            start = to_svg(-5 + offset_x, y)
            end = to_svg(bbox.inner_seam_x + 10 + offset_x, y)
            lines.append(f'    <line x1="{start[0]:.2f}" y1="{start[1]:.2f}" x2="{end[0]:.2f}" y2="{end[1]:.2f}"/>')
        lines.append(f'  </g>')

        corners = [to_svg(cx + offset_x, cy) for (cx, cy) in bbox.get_corners()]
        pts = ' '.join(f'{x:.2f},{y:.2f}' for x, y in corners)
        lines.append(f'  <polygon points="{pts}" fill="none" stroke="#8e44ad" stroke-width="2"/>')

        w = back_points.waist
        wo = to_svg(w.back_waist_outer[0] + offset_x, w.back_waist_outer[1])
        wi = to_svg(w.back_waist_inner[0] + offset_x, w.back_waist_inner[1])
        lines.append(f'  <line x1="{wo[0]:.2f}" y1="{wo[1]:.2f}" x2="{wi[0]:.2f}" y2="{wi[1]:.2f}" stroke="#c0392b" stroke-width="2.5"/>')

        c = back_points.crotch
        d0 = to_svg(c.drop_crotch_line[0][0] + offset_x, c.drop_crotch_line[0][1])
        d1 = to_svg(c.drop_crotch_line[1][0] + offset_x, c.drop_crotch_line[1][1])
        lines.append(f'  <line x1="{d0[0]:.2f}" y1="{d0[1]:.2f}" x2="{d1[0]:.2f}" y2="{d1[1]:.2f}" stroke="#16a085" stroke-width="2.5"/>')

        rise = back_points.rise
        rise_pts = [to_svg(rx + offset_x, ry) for (rx, ry) in rise.rise_curve]
        rise_str = ' '.join(f'{x:.2f},{y:.2f}' for x, y in rise_pts)
        lines.append(f'  <polyline points="{rise_str}" fill="none" stroke="#2980b9" stroke-width="2.5"/>')
        kb0 = to_svg(rise.hip_inner_point[0] + offset_x, rise.hip_inner_point[1])
        kb1 = to_svg(rise.kunshi_point[0] + offset_x, rise.kunshi_point[1])
        lines.append(f'  <line x1="{kb0[0]:.2f}" y1="{kb0[1]:.2f}" x2="{kb1[0]:.2f}" y2="{kb1[1]:.2f}" stroke="#2980b9" stroke-width="1" stroke-dasharray="4,3" opacity="0.6"/>')

        kh = back_points.knee_hem
        for (pa, pb) in ((kh.knee_outer, kh.knee_inner), (kh.hem_outer, kh.hem_inner)):
            a = to_svg(pa[0] + offset_x, pa[1])
            b = to_svg(pb[0] + offset_x, pb[1])
            lines.append(f'  <line x1="{a[0]:.2f}" y1="{a[1]:.2f}" x2="{b[0]:.2f}" y2="{b[1]:.2f}" stroke="#e67e22" stroke-width="2"/>')

        for curve in (back_points.seam.outer_seam_curve, back_points.seam.inner_seam_curve):
            pts = [to_svg(sx + offset_x, sy) for (sx, sy) in curve]
            pts_str = ' '.join(f'{x:.2f},{y:.2f}' for x, y in pts)
            lines.append(f'  <polyline points="{pts_str}" fill="none" stroke="#2c3e50" stroke-width="2.5"/>')

        wf = back_points.waist_final
        wl = [to_svg(p[0] + offset_x, p[1]) for p in wf.waistline]
        wl_str = ' '.join(f'{x:.2f},{y:.2f}' for x, y in wl)
        lines.append(f'  <polyline points="{wl_str}" fill="none" stroke="#e84393" stroke-width="2.5"/>')
        
        re0 = to_svg(wf.rise_extension[0][0] + offset_x, wf.rise_extension[0][1])
        re1 = to_svg(wf.rise_extension[1][0] + offset_x, wf.rise_extension[1][1])
        lines.append(f'  <line x1="{re0[0]:.2f}" y1="{re0[1]:.2f}" x2="{re1[0]:.2f}" y2="{re1[1]:.2f}" stroke="#3498db" stroke-width="2.5" stroke-dasharray="6,3"/>')
        
        oe0 = to_svg(wf.outer_extension[0][0] + offset_x, wf.outer_extension[0][1])
        oe1 = to_svg(wf.outer_extension[1][0] + offset_x, wf.outer_extension[1][1])
        lines.append(f'  <line x1="{oe0[0]:.2f}" y1="{oe0[1]:.2f}" x2="{oe1[0]:.2f}" y2="{oe1[1]:.2f}" stroke="#e67e22" stroke-width="2.5" stroke-dasharray="6,3"/>')

        d = back_points.dart
        for (pa, pb) in ((d.dart_outer, d.dart_tip), (d.dart_inner, d.dart_tip)):
            a = to_svg(pa[0] + offset_x, pa[1])
            b = to_svg(pb[0] + offset_x, pb[1])
            lines.append(f'  <line x1="{a[0]:.2f}" y1="{a[1]:.2f}" x2="{b[0]:.2f}" y2="{b[1]:.2f}" stroke="#9b59b6" stroke-width="2"/>')

        # ===== 步骤10: 绘制腰头 =====
        wb = back_points.waistband
        if wb is not None:
            # 绘制腰头闭合区域（上腰头 + 下腰头）
            waistband_region = [wb.waist_outer, wb.waist_inner] + list(reversed(wb.lower_waist_curve))
            waistband_pts = ' '.join(f'{to_svg(x + offset_x, y)[0]:.2f},{to_svg(x + offset_x, y)[1]:.2f}' for x, y in waistband_region)
            lines.append(f'  <!-- 后片腰头区域 -->')
            lines.append(f'  <polygon points="{waistband_pts}" fill="#1abc9c" fill-opacity="0.2" stroke="none"/>')

            # 绘制下腰头曲线
            lower_curve_pts = ' '.join(f'{to_svg(x + offset_x, y)[0]:.2f},{to_svg(x + offset_x, y)[1]:.2f}' for x, y in wb.lower_waist_curve)
            lines.append(f'  <polyline points="{lower_curve_pts}" fill="none" stroke="#16a085" stroke-width="3"/>')

            # 标注腰头的关键端点
            for pt, label_text in [(wb.lower_waist_outer, "下腰外"), (wb.lower_waist_inner, "下腰内")]:
                mp = to_svg(pt[0] + offset_x, pt[1])
                lines.append(f'  <circle cx="{mp[0]:.2f}" cy="{mp[1]:.2f}" r="4" fill="#16a085"/>')
                label_pos = to_svg(pt[0] + offset_x + 1.5, pt[1] - 1.5)
                lines.append(f'  <text x="{label_pos[0]:.2f}" y="{label_pos[1]:.2f}" font-size="10" fill="#16a085">{label_text}</text>')

        # ===== 步骤11: 绘制机头 =====
        jt = back_points.jitou
        if jt is not None:
            # 绘制机头连接线
            jt_line = [jt.jitou_outer, jt.jitou_inner]
            jt_pts = ' '.join(f'{to_svg(x + offset_x, y)[0]:.2f},{to_svg(x + offset_x, y)[1]:.2f}' for x, y in jt_line)
            lines.append(f'  <!-- 后片机头线 -->')
            lines.append(f'  <polyline points="{jt_pts}" fill="none" stroke="#e67e22" stroke-width="3"/>')

            # 标注机头的关键端点
            for pt, label_text in [(jt.jitou_outer, "机头外"), (jt.jitou_inner, "机头内")]:
                mp = to_svg(pt[0] + offset_x, pt[1])
                lines.append(f'  <circle cx="{mp[0]:.2f}" cy="{mp[1]:.2f}" r="4" fill="#e67e22"/>')
                label_pos = to_svg(pt[0] + offset_x + 1.5, pt[1] - 1.5)
                lines.append(f'  <text x="{label_pos[0]:.2f}" y="{label_pos[1]:.2f}" font-size="10" fill="#e67e22">{label_text}</text>')

        # ===== 步骤12: 绘制后口袋 =====
        bp = back_points.back_pocket
        if bp is not None:
            # 绘制后口袋轮廓
            pocket_pts = ' '.join(f'{to_svg(x + offset_x, y)[0]:.2f},{to_svg(x + offset_x, y)[1]:.2f}' for x, y in bp.pocket_outline)
            lines.append(f'  <!-- 后片后口袋 -->')
            lines.append(f'  <polygon points="{pocket_pts}" fill="#f1c40f" fill-opacity="0.2" stroke="none"/>')
            lines.append(f'  <polyline points="{pocket_pts}" fill="none" stroke="#f39c12" stroke-width="3"/>')

            # 标注后口袋的关键端点
            for pt, label_text in [(bp.pocket_up_inner, "袋上内"), (bp.pocket_up_outer, "袋上外"),
                                   (bp.pocket_down_inner, "袋下内"), (bp.pocket_down_outer, "袋下外")]:
                mp = to_svg(pt[0] + offset_x, pt[1])
                lines.append(f'  <circle cx="{mp[0]:.2f}" cy="{mp[1]:.2f}" r="3" fill="#f39c12"/>')
                label_pos = to_svg(pt[0] + offset_x + 1.5, pt[1] - 1.5)
                lines.append(f'  <text x="{label_pos[0]:.2f}" y="{label_pos[1]:.2f}" font-size="9" fill="#f39c12">{label_text}</text>')

        def mark(p, color):
            mp = to_svg(p[0] + offset_x, p[1])
            lines.append(f'  <circle cx="{mp[0]:.2f}" cy="{mp[1]:.2f}" r="3" fill="{color}"/>')

        mark(w.back_waist_outer, '#c0392b')
        mark(w.back_waist_inner, '#c0392b')
        mark(back_points.waist_final.new_waist_outer, '#e84393')
        mark(back_points.waist_final.new_waist_inner, '#e84393')
        mark(back_points.dart.dart_tip, '#9b59b6')
        mark(back_points.seam.hip_outer_point, '#2c3e50')
        mark(back_points.rise.hip_inner_point, '#2980b9')
        mark(back_points.rise.kunshi_point, '#2980b9')
        mark(back_points.rise.helper_point, '#8e44ad')
        mark(kh.knee_outer, '#e67e22')
        mark(kh.knee_inner, '#e67e22')
        mark(kh.hem_outer, '#e67e22')
        mark(kh.hem_inner, '#e67e22')
        mark(c.crotch_extend_point, '#16a085')
        mark(c.back_crotch_point, '#16a085')

        label = to_svg(offset_x + bbox.inner_seam_x / 2, bbox.waist_y - 5)
        lines.append(f'  <text x="{label[0]:.2f}" y="{label[1]:.2f}" font-size="14" text-anchor="middle" fill="#8e44ad" font-weight="bold">后片</text>')
        return lines

    def _draw_outline(self, points: PatternPoints, to_svg) -> List[str]:
        elements = []
        elements.append(f'  <!-- 轮廓线 -->')
        outline = []
        outline.extend(reversed(points.outer_seam_curve))
        outline.append(points.knee_hem.hem_inner)
        outline.extend(points.inner_seam_curve[1:])
        front_reversed = list(reversed(points.front_rise_curve))
        outline.extend(front_reversed[:-1])
        outline.append(points.waist.waist_inner_final)
        waist_reversed = list(reversed(points.waistline_curve))
        outline.extend(waist_reversed[1:])
        
        svg_points = [to_svg(x, y) for x, y in outline]
        points_str = ' '.join([f'{x:.2f},{y:.2f}' for x, y in svg_points])
        elements.append(f'  <polygon points="{points_str}" fill="none" stroke="#2c3e50" stroke-width="2.5"/>')

        if hasattr(points, 'waistband') and hasattr(points, 'lower_waistline_curve'):
            elements.extend(self._draw_waistband(points, to_svg))
        if hasattr(points, 'front_fly'):
            elements.extend(self._draw_front_fly(points, to_svg))
        if hasattr(points, 'crescent_pocket'):
            elements.extend(self._draw_crescent_pocket(points, to_svg))
        if hasattr(points, 'pocket_patch'):
            elements.extend(self._draw_pocket_patch(points, to_svg))
        if hasattr(points, 'pocket_bag'):
            elements.extend(self._draw_pocket_bag(points, to_svg))
        if hasattr(points, 'watch_pocket'):
            elements.extend(self._draw_watch_pocket(points, to_svg))
        return elements

    def _draw_waistband(self, points: PatternPoints, to_svg) -> List[str]:
        elements = []
        elements.append(f'  <!-- 前片腰头 -->')
        waistband_outline = []
        waistband_outline.extend(points.waistline_curve)
        waistband_outline.extend(reversed(points.lower_waistline_curve))
        svg_points = [to_svg(x, y) for x, y in waistband_outline]
        points_str = ' '.join([f'{x:.2f},{y:.2f}' for x, y in svg_points])
        elements.append(f'  <polygon points="{points_str}" fill="none" stroke="#e67e22" stroke-width="2"/>')
        lower_svg_points = [to_svg(x, y) for x, y in points.lower_waistline_curve]
        lower_points_str = ' '.join([f'{x:.2f},{y:.2f}' for x, y in lower_svg_points])
        elements.append(f'  <polyline points="{lower_points_str}" fill="none" stroke="#e67e22" stroke-width="3"/>')
        return elements

    def _draw_front_fly(self, points: PatternPoints, to_svg) -> List[str]:
        elements = []
        elements.append(f'  <!-- 前门襟 -->')
        fly = points.front_fly
        start_svg = to_svg(fly.fly_start_point[0], fly.fly_start_point[1])
        arc_start_svg = to_svg(fly.fly_end_point[0], fly.fly_end_point[1])
        elements.append(f'    <line x1="{start_svg[0]:.2f}" y1="{start_svg[1]:.2f}" x2="{arc_start_svg[0]:.2f}" y2="{arc_start_svg[1]:.2f}" stroke="#27ae60" stroke-width="3"/>')
        inner_end_svg = to_svg(fly.fly_inner_end[0], fly.fly_inner_end[1])
        elements.append(f'    <line x1="{arc_start_svg[0]:.2f}" y1="{arc_start_svg[1]:.2f}" x2="{inner_end_svg[0]:.2f}" y2="{inner_end_svg[1]:.2f}" stroke="#27ae60" stroke-width="2" stroke-dasharray="5,3"/>')
        outer_end_svg = to_svg(fly.fly_outer_end[0], fly.fly_outer_end[1])
        elements.append(f'    <line x1="{inner_end_svg[0]:.2f}" y1="{inner_end_svg[1]:.2f}" x2="{outer_end_svg[0]:.2f}" y2="{outer_end_svg[1]:.2f}" stroke="#27ae60" stroke-width="2" stroke-dasharray="5,3"/>')
        fly_svg_points = [to_svg(x, y) for x, y in fly.fly_curve]
        fly_points_str = ' '.join([f'{x:.2f},{y:.2f}' for x, y in fly_svg_points])
        elements.append(f'    <polyline points="{fly_points_str}" fill="none" stroke="#27ae60" stroke-width="3"/>')
        return elements

    def _draw_fly_panel(self, points: PatternPoints, to_svg,
                        offset_y: float) -> List[str]:
        """单独绘制门襟裁片（闭合轮廓，平移到前片下方）"""
        elements = []
        fly = getattr(points, 'front_fly', None)
        outline = getattr(fly, 'fly_panel_outline', None) if fly else None
        if not outline:
            return elements
        elements.append(f'  <!-- 门襟裁片（单独裁片） -->')
        panel_svg_points = [to_svg(x, y + offset_y) for x, y in outline]
        points_str = ' '.join([f'{x:.2f},{y:.2f}' for x, y in panel_svg_points])
        elements.append(f'    <polygon points="{points_str}" fill="none" stroke="#27ae60" stroke-width="3"/>')
        # 裁片标注
        min_px = min(p[0] for p in outline)
        max_px = max(p[0] for p in outline)
        max_py = max(p[1] for p in outline) + offset_y
        label_pos = to_svg((min_px + max_px) / 2, max_py + 1.5)
        elements.append(f'    <text x="{label_pos[0]:.2f}" y="{label_pos[1]:.2f}" font-size="12" text-anchor="middle" fill="#27ae60" font-weight="bold">门襟裁片</text>')
        return elements

    def _draw_crescent_pocket(self, points: PatternPoints, to_svg) -> List[str]:
        elements = []
        elements.append(f'  <!-- 月牙袋 -->')
        pocket = points.crescent_pocket
        pocket_svg_points = [to_svg(x, y) for x, y in pocket.pocket_curve]
        pocket_points_str = ' '.join([f'{x:.2f},{y:.2f}' for x, y in pocket_svg_points])
        elements.append(f'    <polyline points="{pocket_points_str}" fill="none" stroke="#9b59b6" stroke-width="3"/>')
        dart_curve_svg = [to_svg(x, y) for x, y in pocket.pocket_dart_curve]
        dart_curve_str = ' '.join([f'{x:.2f},{y:.2f}' for x, y in dart_curve_svg])
        elements.append(f'    <polyline points="{dart_curve_str}" fill="none" stroke="#9b59b6" stroke-width="2"/>')
        width_start = to_svg(pocket.pocket_width[0], pocket.pocket_width[1])
        width_end = to_svg(pocket.pocket_dart_line_width[0], pocket.pocket_dart_line_width[1])
        elements.append(f'    <line x1="{width_start[0]:.2f}" y1="{width_start[1]:.2f}" x2="{width_end[0]:.2f}" y2="{width_end[1]:.2f}" stroke="#9b59b6" stroke-width="2"/>')
        dart_start = to_svg(pocket.pocket_dart[0], pocket.pocket_dart[1])
        dart_end = to_svg(pocket.pocket_dart_line_dart[0], pocket.pocket_dart_line_dart[1])
        elements.append(f'    <line x1="{dart_start[0]:.2f}" y1="{dart_start[1]:.2f}" x2="{dart_end[0]:.2f}" y2="{dart_end[1]:.2f}" stroke="#9b59b6" stroke-width="2"/>')
        return elements

    def _draw_pocket_patch(self, points: PatternPoints, to_svg) -> List[str]:
        elements = []
        elements.append(f'  <!-- 袋贴 -->')
        patch = points.pocket_patch
        pocket = points.crescent_pocket
        patch_svg_points = [to_svg(x, y) for x, y in patch.patch_curve]
        patch_points_str = ' '.join([f'{x:.2f},{y:.2f}' for x, y in patch_svg_points])
        elements.append(f'    <polyline points="{patch_points_str}" fill="none" stroke="#1abc9c" stroke-width="3"/>')
        patch_outline = []
        patch_outline.extend(patch.patch_curve)
        found_patch_outer = False
        for p in points.outer_seam_curve:
            if not found_patch_outer and point_distance(p, patch.patch_outer_seam) < 0.3:
                found_patch_outer = True
            if found_patch_outer:
                patch_outline.append(p)
            if found_patch_outer and point_distance(p, pocket.pocket_outer) < 0.3:
                break
        patch_outline.extend(reversed(pocket.pocket_dart_curve))
        found_dart = False
        for p in points.lower_waistline_curve:
            if not found_dart and point_distance(p, pocket.pocket_dart) < 0.3:
                found_dart = True
            if found_dart:
                patch_outline.append(p)
            if found_dart and point_distance(p, patch.patch_lower_waist) < 0.3:
                break
        svg_outline = [to_svg(x, y) for x, y in patch_outline]
        outline_str = ' '.join([f'{x:.2f},{y:.2f}' for x, y in svg_outline])
        elements.append(f'    <polygon points="{outline_str}" fill="none" stroke="#1abc9c" stroke-width="2"/>')
        return elements

    def _draw_pocket_bag(self, points: PatternPoints, to_svg) -> List[str]:
        elements = []
        elements.append(f'  <!-- 袋布 -->')
        bag = points.pocket_bag
        color = '#e84393'
        def to_pts(curve):
            return ' '.join([f'{to_svg(x, y)[0]:.2f},{to_svg(x, y)[1]:.2f}' for x, y in curve])
        elements.append(f'    <polyline points="{to_pts(bag.bag_line)}" fill="none" stroke="{color}" stroke-width="3"/>')
        elements.append(f'    <polyline points="{to_pts(bag.bag_bottom_edge)}" fill="none" stroke="{color}" stroke-width="3"/>')
        elements.append(f'    <polyline points="{to_pts(bag.bag_curve)}" fill="none" stroke="{color}" stroke-width="3"/>')
        bag_outline = []
        bag_outline.extend(bag.bag_line)
        bag_outline.extend(bag.bag_bottom_edge[1:])
        bag_outline.extend(bag.bag_curve[1:])
        bag_outline.extend(bag.bag_top_edge[1:])
        elements.append(f'    <polygon points="{to_pts(bag_outline)}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="5,3"/>')
        return elements

    def _draw_watch_pocket(self, points: PatternPoints, to_svg) -> List[str]:
        elements = []
        elements.append(f'  <!-- 小表袋 -->')
        wp = points.watch_pocket
        color = '#f1c40f'
        def to_pts(curve):
            return ' '.join([f'{to_svg(x, y)[0]:.2f},{to_svg(x, y)[1]:.2f}' for x, y in curve])
        elements.append(f'    <polyline points="{to_pts([wp.outer_upper, wp.inner_upper])}" fill="none" stroke="{color}" stroke-width="3"/>')
        elements.append(f'    <polyline points="{to_pts(wp.outer_line)}" fill="none" stroke="{color}" stroke-width="3"/>')
        elements.append(f'    <polyline points="{to_pts(wp.inner_line)}" fill="none" stroke="{color}" stroke-width="3"/>')
        elements.append(f'    <polyline points="{to_pts(wp.bottom_curve)}" fill="none" stroke="{color}" stroke-width="3"/>')
        wp_outline = []
        wp_outline.extend([wp.outer_upper, wp.inner_upper])
        wp_outline.extend(wp.inner_line[1:])
        wp_outline.extend(wp.bottom_curve[1:])
        wp_outline.extend(list(reversed(wp.outer_line))[1:])
        elements.append(f'    <polygon points="{to_pts(wp_outline)}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="5,3"/>')
        return elements

    def _draw_points(self, points: PatternPoints, to_svg) -> List[str]:
        elements = []
        elements.append(f'  <!-- 前片关键点 -->')
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
        if hasattr(points, 'waistband'):
            key_points.append(('下腰外', points.waistband.lower_waist_outer))
            key_points.append(('下腰内', points.waistband.lower_waist_inner))

        for name, (x, y) in key_points:
            sx, sy = to_svg(x, y)
            r = 5
            elements.append(f'  <line x1="{sx - r*2:.2f}" y1="{sy:.2f}" x2="{sx + r*2:.2f}" y2="{sy:.2f}" stroke="#e74c3c" stroke-width="1.5"/>')
            elements.append(f'  <line x1="{sx:.2f}" y1="{sy - r*2:.2f}" x2="{sx:.2f}" y2="{sy + r*2:.2f}" stroke="#e74c3c" stroke-width="1.5"/>')
            elements.append(f'  <circle cx="{sx:.2f}" cy="{sy:.2f}" r="{r:.2f}" fill="none" stroke="#e74c3c" stroke-width="2"/>')
        return elements

    def _draw_dimensions(self, points: PatternPoints, to_svg, min_x: float, max_x: float, min_y: float, max_y: float) -> List[str]:
        elements = []
        elements.append(f'  <!-- 尺寸标注 -->')
        elements.append(f'  <g font-family="Arial, sans-serif" font-size="12" fill="#555">')
        bbox = points.bounding_box
        dim_x = min_x - 1.5
        start = to_svg(dim_x, bbox.hem_y)
        end = to_svg(dim_x, bbox.waist_y)
        elements.append(f'    <line x1="{start[0]:.2f}" y1="{start[1]:.2f}" x2="{end[0]:.2f}" y2="{end[1]:.2f}" stroke="#666" stroke-width="1" marker-start="url(#arrow-start)" marker-end="url(#arrow-end)"/>')
        mid_y = (start[1] + end[1]) / 2
        elements.append(f'    <text x="{start[0] - 8:.2f}" y="{mid_y:.2f}" text-anchor="end" dominant-baseline="middle">{bbox.waist_y:.0f}</text>')
        dim_y = max_y + 1.5
        start = to_svg(bbox.outer_seam_x, dim_y)
        end = to_svg(bbox.inner_seam_x, dim_y)
        elements.append(f'    <line x1="{start[0]:.2f}" y1="{start[1]:.2f}" x2="{end[0]:.2f}" y2="{end[1]:.2f}" stroke="#666" stroke-width="1" marker-start="url(#arrow-start)" marker-end="url(#arrow-end)"/>')
        mid_x = (start[0] + end[0]) / 2
        elements.append(f'    <text x="{mid_x:.2f}" y="{start[1] - 8:.2f}" text-anchor="middle">{bbox.inner_seam_x:.1f}</text>')
        elements.append(f'  </g>')
        return elements

    def _draw_legend(self, x: float, y: float) -> List[str]:
        elements = []
        elements.append(f'  <!-- 图例 -->')
        elements.append(f'  <g font-family="Arial, sans-serif" font-size="12">')
        legend_items = [
            ('后片腰头/下腰头', '#16a085', 'line'),
            ('后片机头线', '#e67e22', 'line'),
            ('后片后口袋', '#f39c12', 'line'),
            ('后片外/内缝', '#2c3e50', 'line'),
            ('后浪/困势线', '#2980b9', 'line'),
            ('前片轮廓线', '#2c3e50', 'line'),
            ('腰头/下腰头', '#e67e22', 'line'),
            ('前门襟', '#27ae60', 'line'),
            ('月牙袋', '#9b59b6', 'line'),
            ('参考线', '#4a90d9', 'dashed'),
        ]
        for i, (name, color, style) in enumerate(legend_items):
            ly = y + i * 20 - 40
            if style == 'line':
                elements.append(f'    <line x1="{x:.2f}" y1="{ly:.2f}" x2="{x + 30:.2f}" y2="{ly:.2f}" stroke="{color}" stroke-width="2.5"/>')
            elif style == 'dashed':
                elements.append(f'    <line x1="{x:.2f}" y1="{ly:.2f}" x2="{x + 30:.2f}" y2="{ly:.2f}" stroke="{color}" stroke-width="2" stroke-dasharray="8,4"/>')
            elements.append(f'    <text x="{x + 42:.2f}" y="{ly + 4:.2f}" fill="#333">{name}</text>')
        elements.append(f'    <text x="{x:.2f}" y="{y - 65:.2f}" fill="#333" font-size="14" font-weight="bold">版型图例</text>')
        elements.append(f'  </g>')
        return elements