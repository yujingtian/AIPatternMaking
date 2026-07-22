"""
DXF文件导出模块
"""
import ezdxf
from ezdxf.document import Drawing
from ezdxf.layouts import Modelspace
from typing import List, Tuple, Optional
from .types import PatternPoints, BoundingBox, BackPatternPoints


class DXFExporter:
    """DXF导出器"""

    def __init__(self, units: str = 'mm'):
        """
        初始化导出器

        Args:
            units: 单位，'mm' 或 'cm'。DXF通常使用毫米
        """
        self.units = units
        self.scale = 10.0 if units == 'mm' else 1.0  # cm转mm需要乘以10

    def export(self, points: PatternPoints, filepath: str,
               back_points: Optional[BackPatternPoints] = None) -> None:
        """
        导出版型到DXF文件

        Args:
            points: 版型关键点
            filepath: 输出文件路径
            back_points: 后片打版结果（可选，含步骤1~3）
        """
        # 创建新的DXF文档 - 使用R2000以最好兼容ET
        doc = ezdxf.new('R2000')
        msp = doc.modelspace()

        # 设置单位
        doc.units = ezdxf.units.MM if self.units == 'mm' else ezdxf.units.CM

        # 创建图层
        self._create_layers(doc)

        # 绘制参考线
        self._draw_reference_lines(msp, points)

        # 绘制后片（步骤1参考线/大矩形 + 步骤2后腰头 + 步骤3后立裆/落档），放在前片右侧
        if back_points is not None:
            front_max_x = points.front_rise.crotch_extension_point[0]
            back_offset_x = front_max_x + 8.0  # 前后片间隔 8cm
            self._draw_back_panel(msp, back_points, back_offset_x)

        # 绘制轮廓线
        self._draw_outline(msp, points)

        # 单独绘制门襟裁片（闭合轮廓，平移到前片下方）
        self._draw_fly_panel(msp, points)

        # 单独绘制前片整体轮廓（闭合裁片，平移到最右侧）
        self._draw_front_panel(msp, points, back_points)

        # 单独绘制前腰头裁片（闭合裁片，平移到门襟裁片下方）
        self._draw_front_waistband(msp, points)

        # 单独绘制袋贴裁片（闭合裁片，平移到前腰头裁片下方）
        self._draw_pocket_patch_panel(msp, points)

        # 单独绘制小表袋裁片（闭合裁片，平移到袋贴裁片下方）
        self._draw_watch_pocket_panel(msp, points)

        # 单独绘制袋布裁片（闭合裁片，平移到小表袋裁片下方）
        self._draw_pocket_bag_panel(msp, points)

        # 绘制关键点标注
        self._draw_points(msp, points)

        # 保存文件
        doc.saveas(filepath)
        print(f"DXF文件已保存至: {filepath}")

    def _create_layers(self, doc: Drawing) -> None:
        """创建DXF图层 - 使用英文名称兼容ET"""
        # 参考线层 - 蓝色
        doc.layers.add(name='REFERENCE', color=5)
        # 后片参考线层 - 紫红
        doc.layers.add(name='BACKPANEL', color=6)
        # 后片腰头线层 - 红色
        doc.layers.add(name='BACKWAIST', color=1)
        # 后片立裆/落档层 - 绿色
        doc.layers.add(name='BACKCROTCH', color=3)
        # 后片后浪曲线层 - 蓝色
        doc.layers.add(name='BACKRISE', color=5)
        # 后片膝围/脚口层 - 橙色
        doc.layers.add(name='BACKLEG', color=30)
        # 后片内缝/外缝层 - 白/黑（主轮廓）
        doc.layers.add(name='BACKSEAM', color=7)
        # 后片最终腰围线层 - 紫红
        doc.layers.add(name='BACKWAISTFINAL', color=40)
        # 后片腰省层 - 紫色
        doc.layers.add(name='BACKDART', color=6)
        # 后片折叠腰头层 - 青色
        doc.layers.add(name='BACKWAISTBAND', color=4)
        # 后片机头层 - 橙色
        doc.layers.add(name='BACKJITOU', color=30)
        # 后片后口袋层 - 橙色
        doc.layers.add(name='BACKPOCKET', color=30)
        # 轮廓线层 - 白色/黑色
        doc.layers.add(name='OUTLINE', color=7)
        # 腰头层 - 橙色
        doc.layers.add(name='WAISTBAND', color=1)
        # 前门襟层 - 绿色
        doc.layers.add(name='FRONTFLY', color=3)
        # 门襟裁片层 - 绿色
        doc.layers.add(name='FLYPANEL', color=3)
        # 前片整体轮廓裁片层 - 白/黑
        doc.layers.add(name='FRONTPANEL', color=7)
        # 前腰头裁片层 - 橙色
        doc.layers.add(name='FRONTWAISTBAND', color=30)
        # 袋贴裁片层 - 青色
        doc.layers.add(name='POCKETPATCHPANEL', color=4)
        # 小表袋裁片层 - 金色
        doc.layers.add(name='WATCHPOCKETPANEL', color=50)
        # 袋布裁片层 - 粉色
        doc.layers.add(name='POCKETBAGPANEL', color=40)
        # 月牙袋层 - 紫色
        doc.layers.add(name='POCKET', color=6)
        # 袋贴层 - 黄色
        doc.layers.add(name='POCKETPATCH', color=2)
        # 袋布层 - 粉色 (ACI 40)
        doc.layers.add(name='POCKETBAG', color=40)
        # 小表袋层 - 金色 (ACI 50)
        doc.layers.add(name='WATCHPOCKET', color=50)
        # 关键点层 - 红色
        doc.layers.add(name='POINTS', color=1)
        # 标注层 - 青色
        doc.layers.add(name='DIMENSION', color=4)

    def _to_dxf_coords(self, x: float, y: float) -> Tuple[float, float]:
        """
        将版型坐标转换为DXF坐标

        注意:
        - DXF通常使用毫米为单位
        - 可以根据需要调整坐标系方向
        """
        # 这里使用: Y轴向上，保持右手坐标系
        return (x * self.scale, y * self.scale)

    def _draw_reference_lines(self, msp: Modelspace, points: PatternPoints) -> None:
        """绘制参考线"""
        bbox = points.bounding_box

        # 外侧缝参考线 (X=0)
        start = self._to_dxf_coords(bbox.outer_seam_x, bbox.hem_y - 5)
        end = self._to_dxf_coords(bbox.outer_seam_x, bbox.waist_y + 5)
        msp.add_line(start, end, dxfattribs={'layer': 'REFERENCE'})

        # 内侧缝参考线
        start = self._to_dxf_coords(bbox.inner_seam_x, bbox.hem_y - 5)
        end = self._to_dxf_coords(bbox.inner_seam_x, bbox.waist_y + 5)
        msp.add_line(start, end, dxfattribs={'layer': 'REFERENCE'})

        # 裤中线
        start = self._to_dxf_coords(points.center_crease_x, bbox.hem_y - 5)
        end = self._to_dxf_coords(points.center_crease_x, bbox.waist_y + 5)
        msp.add_line(start, end, dxfattribs={'layer': 'REFERENCE'})

        # 水平参考线 - 只画线，不标注文字
        y_positions = [
            bbox.hem_y,
            bbox.knee_y,
            bbox.crotch_y,
            bbox.hip_y,
            bbox.waist_y
        ]

        for y in y_positions:
            start = self._to_dxf_coords(-5, y)
            end = self._to_dxf_coords(bbox.inner_seam_x + 10, y)
            msp.add_line(start, end, dxfattribs={'layer': 'REFERENCE'})

    def _draw_back_panel(self, msp: Modelspace, back_points: BackPatternPoints,
                         offset_x: float) -> None:
        """绘制后片（步骤1参考线/大矩形 + 步骤2后腰头线 + 步骤3后立裆/落档）

        后片整体沿X轴正向偏移 offset_x，放在前片右侧。坐标转换时先加偏移再缩放。
        """
        bbox = back_points.bounding_box

        def bx(x: float) -> Tuple[float, float]:
            """后片X坐标带偏移后转DXF坐标"""
            return self._to_dxf_coords(x + offset_x, 0.0)[0]

        def pt(p: Tuple[float, float]) -> Tuple[float, float]:
            """后片点带偏移后转DXF坐标"""
            return (bx(p[0]), self._to_dxf_coords(0, p[1])[1])

        # 外侧缝 / 内侧缝 / 裤中线 垂直参考线
        for vx in (bbox.outer_seam_x, bbox.inner_seam_x, back_points.center_crease_x):
            start = (bx(vx), self._to_dxf_coords(0, bbox.hem_y - 5)[1])
            end = (bx(vx), self._to_dxf_coords(0, bbox.waist_y + 5)[1])
            msp.add_line(start, end, dxfattribs={'layer': 'BACKPANEL'})

        # 五条水平参考线：脚口 / 膝围 / 立裆 / 臀围 / 腰围
        for y in (bbox.hem_y, bbox.knee_y, bbox.crotch_y, bbox.hip_y, bbox.waist_y):
            start = (bx(-5), self._to_dxf_coords(0, y)[1])
            end = (bx(bbox.inner_seam_x + 10), self._to_dxf_coords(0, y)[1])
            msp.add_line(start, end, dxfattribs={'layer': 'BACKPANEL'})

        # 大矩形框架（闭合多段线，标示后片当前范围）
        corners = [(bx(cx), self._to_dxf_coords(0, cy)[1]) for (cx, cy) in bbox.get_corners()]
        msp.add_lwpolyline(corners, close=True, dxfattribs={'layer': 'BACKPANEL'})

        # 步骤2: 后腰头线（后腰围外缝顶点 → 后腰围内缝顶点）
        w = back_points.waist
        msp.add_line(pt(w.back_waist_outer), pt(w.back_waist_inner),
                     dxfattribs={'layer': 'BACKWAIST'})

        # 步骤3: 落档线 + 后立裆宽顶点
        c = back_points.crotch
        d0, d1 = c.drop_crotch_line
        msp.add_line(pt(d0), pt(d1), dxfattribs={'layer': 'BACKCROTCH'})

        # 步骤4: 后浪曲线（后腰围内缝顶点 → 臀围内缝顶点 → 后立裆宽顶点）
        rise = back_points.rise
        rise_dxf = [pt(p) for p in rise.rise_curve]
        msp.add_lwpolyline(rise_dxf, dxfattribs={'layer': 'BACKRISE'})
        # 困势线（构造辅助线：臀围内缝顶点 → 困势顶点）
        msp.add_line(pt(rise.hip_inner_point), pt(rise.kunshi_point),
                     dxfattribs={'layer': 'BACKRISE'})

        # 步骤6: 实际膝围与脚口宽度线
        kh = back_points.knee_hem
        msp.add_line(pt(kh.knee_outer), pt(kh.knee_inner), dxfattribs={'layer': 'BACKLEG'})
        msp.add_line(pt(kh.hem_outer), pt(kh.hem_inner), dxfattribs={'layer': 'BACKLEG'})

        # 步骤7: 内缝与外缝曲线
        seam = back_points.seam
        msp.add_lwpolyline([pt(p) for p in seam.outer_seam_curve],
                           dxfattribs={'layer': 'BACKSEAM'})
        msp.add_lwpolyline([pt(p) for p in seam.inner_seam_curve],
                           dxfattribs={'layer': 'BACKSEAM'})

        # 步骤8: 最终腰围线（后翘）+ 两条延长段
        wf = back_points.waist_final
        msp.add_lwpolyline([pt(wf.new_waist_outer), pt(wf.new_waist_inner)],
                           dxfattribs={'layer': 'BACKWAISTFINAL'})
        msp.add_line(pt(wf.rise_extension[0]), pt(wf.rise_extension[1]),
                     dxfattribs={'layer': 'BACKRISE'})
        msp.add_line(pt(wf.outer_extension[0]), pt(wf.outer_extension[1]),
                     dxfattribs={'layer': 'BACKSEAM'})

        # 步骤9: 腰省（V 形）
        d = back_points.dart
        msp.add_line(pt(d.dart_outer), pt(d.dart_tip), dxfattribs={'layer': 'BACKDART'})
        msp.add_line(pt(d.dart_inner), pt(d.dart_tip), dxfattribs={'layer': 'BACKDART'})

        # 步骤10: 绘制腰头
        wb = back_points.waistband
        if wb is not None:
            # 下腰头曲线
            msp.add_lwpolyline([pt(p) for p in wb.lower_waist_curve],
                               dxfattribs={'layer': 'BACKWAISTBAND'})
            # 闭合腰头裁片：上腰头(外→内) + 下腰头反向(内→外)
            piece = [wb.waist_outer, wb.waist_inner] + list(reversed(wb.lower_waist_curve))
            msp.add_lwpolyline([pt(p) for p in piece], close=True,
                               dxfattribs={'layer': 'BACKWAISTBAND'})

        # 步骤11: 绘制机头
        jt = back_points.jitou
        if jt is not None:
            # 机头连接线（从外到内）
            msp.add_line(pt(jt.jitou_outer), pt(jt.jitou_inner),
                        dxfattribs={'layer': 'BACKJITOU'})

        # 步骤12: 绘制后口袋
        bp = back_points.back_pocket
        if bp is not None:
            # 后口袋轮廓
            msp.add_lwpolyline([pt(p) for p in bp.pocket_outline], close=True,
                              dxfattribs={'layer': 'BACKPOCKET'})

    def _draw_outline(self, msp: Modelspace, points: PatternPoints) -> None:
        """绘制轮廓线"""
        # 外侧缝曲线
        self._draw_polyline(msp, points.outer_seam_curve, 'OUTLINE')

        # 腰围线曲线
        self._draw_polyline(msp, points.waistline_curve, 'OUTLINE')

        # 前浪曲线
        self._draw_polyline(msp, points.front_rise_curve, 'OUTLINE')

        # 内侧缝曲线
        self._draw_polyline(msp, points.inner_seam_curve, 'OUTLINE')

        # 绘制闭合轮廓（使用样条曲线拟合）
        self._draw_closed_outline(msp, points)

        # 绘制腰头
        if hasattr(points, 'waistband') and hasattr(points, 'lower_waistline_curve'):
            self._draw_waistband(msp, points)

        # 绘制前门襟
        if hasattr(points, 'front_fly'):
            self._draw_front_fly(msp, points)

        # 绘制月牙袋
        if hasattr(points, 'crescent_pocket'):
            self._draw_crescent_pocket(msp, points)

        # 绘制袋贴
        if hasattr(points, 'pocket_patch'):
            self._draw_pocket_patch(msp, points)

        # 绘制袋布
        if hasattr(points, 'pocket_bag'):
            self._draw_pocket_bag(msp, points)

        # 绘制小表袋
        if hasattr(points, 'watch_pocket'):
            self._draw_watch_pocket(msp, points)

    def _draw_polyline(self, msp: Modelspace, curve_points: List[Tuple[float, float]],
                       layer: str) -> None:
        """绘制多段线"""
        if len(curve_points) < 2:
            return

        dxf_points = [self._to_dxf_coords(x, y) for x, y in curve_points]

        # 使用轻量多段线
        msp.add_lwpolyline(dxf_points, dxfattribs={'layer': layer})

    def _draw_closed_outline(self, msp: Modelspace, points: PatternPoints) -> None:
        """绘制闭合轮廓（使用样条曲线）"""
        # 收集所有轮廓点并按顺序排列
        # 顺序: 腰围外 -> 外侧缝 -> 脚口外 -> 脚口内 -> 内侧缝 -> 立裆 -> 前浪 -> 腰围内 -> 腰围线 -> 腰围外

        # 构建闭合轮廓点列表
        outline = []

        # 1. 腰围外开始，沿外侧缝向下
        outline.extend(reversed(points.outer_seam_curve))

        # 2. 脚口外到脚口内（直线闭合）
        outline.append(points.knee_hem.hem_inner)

        # 3. 沿内侧缝向上
        outline.extend(points.inner_seam_curve[1:])

        # 4. 沿前浪向上到腰围内
        outline.extend(reversed(points.front_rise_curve[:-1]))

        # 5. 沿腰围线回到腰围外
        outline.extend(reversed(points.waistline_curve[:-1]))

        # 转换为DXF坐标
        dxf_points = [self._to_dxf_coords(x, y) for x, y in outline]

        # 添加闭合多段线（单独图层，用于切割）
        msp.add_lwpolyline(dxf_points, close=True, dxfattribs={'layer': 'OUTLINE', 'color': 2})

    def _draw_points(self, msp: Modelspace, points: PatternPoints) -> None:
        """绘制关键点标记 - 使用英文标注兼容ET"""
        # 关键点列表 - 使用英文标注
        key_points = [
            ('WaistOuter', points.waist.waist_outer),
            ('WaistInner', points.waist.waist_inner_final),
            ('HipOuter', (points.bounding_box.outer_seam_x, points.bounding_box.hip_y)),
            ('HipInner', points.front_rise.hip_inner_point),
            ('KneeOuter', points.knee_hem.knee_outer),
            ('KneeInner', points.knee_hem.knee_inner),
            ('HemOuter', points.knee_hem.hem_outer),
            ('HemInner', points.knee_hem.hem_inner),
            ('Crotch', points.front_rise.crotch_extension_point),
        ]

        for name, (x, y) in key_points:
            # 绘制十字标记
            dxf_x, dxf_y = self._to_dxf_coords(x, y)
            size = 2.0 * self.scale

            # 横线
            msp.add_line(
                (dxf_x - size, dxf_y),
                (dxf_x + size, dxf_y),
                dxfattribs={'layer': 'POINTS'}
            )
            # 竖线
            msp.add_line(
                (dxf_x, dxf_y - size),
                (dxf_x, dxf_y + size),
                dxfattribs={'layer': 'POINTS'}
            )

            # 绘制圆点
            msp.add_circle(
                (dxf_x, dxf_y),
                0.5 * self.scale,
                dxfattribs={'layer': 'POINTS'}
            )

            # 添加文字标注 - 使用英文
            text = msp.add_text(
                name,
                dxfattribs={
                    'layer': 'DIMENSION',
                    'height': 2.5 * self.scale
                }
            )
            text.dxf.insert = (dxf_x + size, dxf_y + size)

        # 添加腰头关键点
        if hasattr(points, 'waistband'):
            waistband_points = [
                ('LowerWaistOuter', points.waistband.lower_waist_outer),
                ('LowerWaistInner', points.waistband.lower_waist_inner),
            ]
            for name, (x, y) in waistband_points:
                dxf_x, dxf_y = self._to_dxf_coords(x, y)
                size = 2.0 * self.scale
                msp.add_line((dxf_x - size, dxf_y), (dxf_x + size, dxf_y), dxfattribs={'layer': 'POINTS'})
                msp.add_line((dxf_x, dxf_y - size), (dxf_x, dxf_y + size), dxfattribs={'layer': 'POINTS'})
                msp.add_circle((dxf_x, dxf_y), 0.5 * self.scale, dxfattribs={'layer': 'POINTS'})
                text = msp.add_text(name, dxfattribs={'layer': 'DIMENSION', 'height': 2.5 * self.scale})
                text.dxf.insert = (dxf_x + size, dxf_y + size)

        # 添加前门襟关键点
        if hasattr(points, 'front_fly'):
            front_fly_points = [
                ('FlyStart', points.front_fly.fly_start_point),
                ('FlyInner', points.front_fly.fly_inner_end),
                ('FlyOuter', points.front_fly.fly_outer_end),
                ('FlyEnd', points.front_fly.fly_end_point),
            ]
            for name, (x, y) in front_fly_points:
                dxf_x, dxf_y = self._to_dxf_coords(x, y)
                size = 2.0 * self.scale
                msp.add_line((dxf_x - size, dxf_y), (dxf_x + size, dxf_y), dxfattribs={'layer': 'POINTS'})
                msp.add_line((dxf_x, dxf_y - size), (dxf_x, dxf_y + size), dxfattribs={'layer': 'POINTS'})
                msp.add_circle((dxf_x, dxf_y), 0.5 * self.scale, dxfattribs={'layer': 'POINTS'})
                text = msp.add_text(name, dxfattribs={'layer': 'DIMENSION', 'height': 2.5 * self.scale})
                text.dxf.insert = (dxf_x + size, dxf_y + size)

        # 添加月牙袋关键点
        if hasattr(points, 'crescent_pocket'):
            pocket_points = [
                ('PocketOuter', points.crescent_pocket.pocket_outer),
                ('PocketWidth', points.crescent_pocket.pocket_width),
                ('PocketDart', points.crescent_pocket.pocket_dart),
                ('PocketDartLineW', points.crescent_pocket.pocket_dart_line_width),
                ('PocketDartLineD', points.crescent_pocket.pocket_dart_line_dart),
            ]
            for name, (x, y) in pocket_points:
                dxf_x, dxf_y = self._to_dxf_coords(x, y)
                size = 2.0 * self.scale
                msp.add_line((dxf_x - size, dxf_y), (dxf_x + size, dxf_y), dxfattribs={'layer': 'POINTS'})
                msp.add_line((dxf_x, dxf_y - size), (dxf_x, dxf_y + size), dxfattribs={'layer': 'POINTS'})
                msp.add_circle((dxf_x, dxf_y), 0.5 * self.scale, dxfattribs={'layer': 'POINTS'})
                text = msp.add_text(name, dxfattribs={'layer': 'DIMENSION', 'height': 2.5 * self.scale})
                text.dxf.insert = (dxf_x + size, dxf_y + size)

        # 添加袋贴关键点
        if hasattr(points, 'pocket_patch'):
            patch_points = [
                ('PatchWaist', points.pocket_patch.patch_lower_waist),
                ('PatchOuter', points.pocket_patch.patch_outer_seam),
            ]
            for name, (x, y) in patch_points:
                dxf_x, dxf_y = self._to_dxf_coords(x, y)
                size = 2.0 * self.scale
                msp.add_line((dxf_x - size, dxf_y), (dxf_x + size, dxf_y), dxfattribs={'layer': 'POINTS'})
                msp.add_line((dxf_x, dxf_y - size), (dxf_x, dxf_y + size), dxfattribs={'layer': 'POINTS'})
                msp.add_circle((dxf_x, dxf_y), 0.5 * self.scale, dxfattribs={'layer': 'POINTS'})
                text = msp.add_text(name, dxfattribs={'layer': 'DIMENSION', 'height': 2.5 * self.scale})
                text.dxf.insert = (dxf_x + size, dxf_y + size)

        # 添加袋布关键点
        if hasattr(points, 'pocket_bag'):
            bag_points = [
                ('BagWaist', points.pocket_bag.bag_upper_waist),
                ('BagInner', points.pocket_bag.bag_inner_end),
                ('BagCorner', points.pocket_bag.bag_corner),
                ('BagOuter', points.pocket_bag.bag_outer_seam),
            ]
            for name, (x, y) in bag_points:
                dxf_x, dxf_y = self._to_dxf_coords(x, y)
                size = 2.0 * self.scale
                msp.add_line((dxf_x - size, dxf_y), (dxf_x + size, dxf_y), dxfattribs={'layer': 'POINTS'})
                msp.add_line((dxf_x, dxf_y - size), (dxf_x, dxf_y + size), dxfattribs={'layer': 'POINTS'})
                msp.add_circle((dxf_x, dxf_y), 0.5 * self.scale, dxfattribs={'layer': 'POINTS'})
                text = msp.add_text(name, dxfattribs={'layer': 'DIMENSION', 'height': 2.5 * self.scale})
                text.dxf.insert = (dxf_x + size, dxf_y + size)

        # 添加小表袋关键点
        if hasattr(points, 'watch_pocket'):
            wp_points = [
                ('WatchOutUp', points.watch_pocket.outer_upper),
                ('WatchOutDn', points.watch_pocket.outer_lower),
                ('WatchInUp', points.watch_pocket.inner_upper),
                ('WatchInDn', points.watch_pocket.inner_lower),
            ]
            for name, (x, y) in wp_points:
                dxf_x, dxf_y = self._to_dxf_coords(x, y)
                size = 2.0 * self.scale
                msp.add_line((dxf_x - size, dxf_y), (dxf_x + size, dxf_y), dxfattribs={'layer': 'POINTS'})
                msp.add_line((dxf_x, dxf_y - size), (dxf_x, dxf_y + size), dxfattribs={'layer': 'POINTS'})
                msp.add_circle((dxf_x, dxf_y), 0.5 * self.scale, dxfattribs={'layer': 'POINTS'})
                text = msp.add_text(name, dxfattribs={'layer': 'DIMENSION', 'height': 2.5 * self.scale})
                text.dxf.insert = (dxf_x + size, dxf_y + size)

    def _draw_waistband(self, msp: Modelspace, points: PatternPoints) -> None:
        """绘制腰头（含下腰头）"""
        # 绘制下腰头曲线
        self._draw_polyline(msp, points.lower_waistline_curve, 'WAISTBAND')

        # 绘制腰头闭合区域
        # 顺序：上腰头外 -> 上腰头内 -> 下腰头内 -> 下腰头外 -> 上腰头外
        waistband_outline = []
        waistband_outline.extend(points.waistline_curve)
        waistband_outline.extend(reversed(points.lower_waistline_curve))

        dxf_points = [self._to_dxf_coords(x, y) for x, y in waistband_outline]
        msp.add_lwpolyline(dxf_points, close=True, dxfattribs={'layer': 'WAISTBAND'})

    def _draw_front_fly(self, msp: Modelspace, points: PatternPoints) -> None:
        """绘制前门襟"""
        fly = points.front_fly

        # 绘制门襟线（从起点到弧起点）- 实线（实际轮廓）
        start_point = self._to_dxf_coords(fly.fly_start_point[0], fly.fly_start_point[1])
        arc_start = self._to_dxf_coords(fly.fly_end_point[0], fly.fly_end_point[1])
        msp.add_line(start_point, arc_start, dxfattribs={'layer': 'FRONTFLY'})

        # 绘制门襟线（从弧起点到内端点）- 辅助线
        inner_end = self._to_dxf_coords(fly.fly_inner_end[0], fly.fly_inner_end[1])
        msp.add_line(arc_start, inner_end, dxfattribs={'layer': 'FRONTFLY'})

        # 绘制门襟宽线（从内端点到外端点）- 辅助线
        outer_end = self._to_dxf_coords(fly.fly_outer_end[0], fly.fly_outer_end[1])
        msp.add_line(inner_end, outer_end, dxfattribs={'layer': 'FRONTFLY'})

        # 绘制门襟弧线
        self._draw_polyline(msp, fly.fly_curve, 'FRONTFLY')

        # 绘制门襟闭合区域
        # 从下腰头门襟点 -> 门襟线 -> 弧起点 -> 弧线 -> 门襟外端点 -> 前浪 -> 下腰头内缝顶点 -> 下腰头 -> 门襟起点
        fly_outline = []
        fly_outline.append(fly.fly_start_point)  # 下腰头门襟点
        fly_outline.append(fly.fly_end_point)    # 沿着门襟线到弧起点
        fly_outline.extend(fly.fly_curve)        # 沿着弧线到门襟外端点
        # 从门襟外端点沿着前浪到下腰头内缝顶点
        def distance(p1, p2):
            return ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5
        found_outer = False
        for p in points.front_rise_curve:
            if not found_outer and distance(p, fly.fly_outer_end) < 0.2:
                found_outer = True
            if found_outer:
                fly_outline.append(p)
            if hasattr(points, 'waistband') and found_outer:
                if distance(p, points.waistband.lower_waist_inner) < 0.3:
                    break
        # 添加下腰头内缝顶点
        if hasattr(points, 'waistband'):
            fly_outline.append(points.waistband.lower_waist_inner)
            # 沿着下腰头曲线从内到外，直到门襟起点
            found_lower_inner = False
            for p in reversed(points.lower_waistline_curve):
                if not found_lower_inner:
                    if distance(p, points.waistband.lower_waist_inner) < 0.2:
                        found_lower_inner = True
                if found_lower_inner:
                    fly_outline.append(p)
                    if distance(p, fly.fly_start_point) < 0.3:
                        break
        # 确保闭合
        fly_outline.append(fly.fly_start_point)

        dxf_fly_points = [self._to_dxf_coords(x, y) for x, y in fly_outline]
        msp.add_lwpolyline(dxf_fly_points, close=True, dxfattribs={'layer': 'FRONTFLY'})

    def _draw_fly_panel(self, msp: Modelspace, points: PatternPoints) -> None:
        """单独绘制门襟裁片（闭合轮廓，平移到前片下方）"""
        fly = getattr(points, 'front_fly', None)
        outline = getattr(fly, 'fly_panel_outline', None) if fly else None
        if not outline:
            return
        # 裁片最高点平移到脚口参考线下方5cm处
        panel_max_y = max(p[1] for p in outline)
        offset_y = -(panel_max_y + 5.0)
        dxf_pts = [self._to_dxf_coords(x, y + offset_y) for x, y in outline]
        msp.add_lwpolyline(dxf_pts, close=True, dxfattribs={'layer': 'FLYPANEL'})
        # 裁片标注
        min_px = min(p[0] for p in outline)
        max_px = max(p[0] for p in outline)
        label_x, label_y = self._to_dxf_coords((min_px + max_px) / 2, -3.5)
        text = msp.add_text('FLY_PANEL', dxfattribs={'layer': 'FLYPANEL', 'height': 2.5 * self.scale})
        text.dxf.insert = (label_x, label_y)

    def _draw_front_panel(self, msp: Modelspace, points: PatternPoints,
                          back_points: Optional[BackPatternPoints] = None) -> None:
        """单独绘制前片整体轮廓（闭合裁片，平移到最右侧）"""
        outline = getattr(points, 'front_panel_outline', None)
        if not outline:
            return
        panel_min_x = min(p[0] for p in outline)
        # 计算左侧已有图形的最右边缘（前片或后片）
        front_max_x = points.front_rise.crotch_extension_point[0]
        right_edge = front_max_x
        if back_points is not None:
            back_offset_x = front_max_x + 8.0
            back_max_x = max(
                back_points.bounding_box.inner_seam_x,
                back_points.crotch.back_crotch_point[0],
                back_points.waist_final.new_waist_inner[0],
                back_points.knee_hem.hem_inner[0],
            )
            right_edge = back_offset_x + back_max_x
        offset_x = right_edge + 8.0 - panel_min_x  # 与左侧图形间隔8cm
        dxf_pts = [self._to_dxf_coords(x + offset_x, y) for x, y in outline]
        msp.add_lwpolyline(dxf_pts, close=True, dxfattribs={'layer': 'FRONTPANEL'})
        # 裁片上的前门襟（门襟线 + 门襟弧线）
        fly = getattr(points, 'front_fly', None)
        if fly is not None:
            fly_start = self._to_dxf_coords(fly.fly_start_point[0] + offset_x, fly.fly_start_point[1])
            fly_arc_start = self._to_dxf_coords(fly.fly_end_point[0] + offset_x, fly.fly_end_point[1])
            msp.add_line(fly_start, fly_arc_start, dxfattribs={'layer': 'FRONTFLY'})
            fly_curve_pts = [self._to_dxf_coords(x + offset_x, y) for x, y in fly.fly_curve]
            msp.add_lwpolyline(fly_curve_pts, dxfattribs={'layer': 'FRONTFLY'})
        # 裁片标注
        max_px = max(p[0] for p in outline)
        max_py = max(p[1] for p in outline)
        label_x, label_y = self._to_dxf_coords((panel_min_x + max_px) / 2 + offset_x, max_py + 1.5)
        text = msp.add_text('FRONT_PANEL', dxfattribs={'layer': 'FRONTPANEL', 'height': 2.5 * self.scale})
        text.dxf.insert = (label_x, label_y)

    def _panel_stack_bottom_y(self, points: PatternPoints, level: int) -> float:
        """计算纵向堆叠裁片区域的底部Y坐标
        level 为当前裁片上方已堆叠的裁片个数：
        0=门襟裁片之上无前片外裁片，1=门襟，2=+前腰头，3=+袋贴，4=+小表袋"""
        bottom_y = 0.0
        fly = getattr(points, 'front_fly', None)
        stacked = [
            getattr(fly, 'fly_panel_outline', None) if fly else None,  # 门襟裁片
            getattr(points, 'front_waistband_outline', None),          # 前腰头裁片
            getattr(points, 'pocket_patch_outline', None),             # 袋贴裁片
            getattr(points, 'watch_pocket_outline', None),             # 小表袋裁片
        ]
        for panel in stacked[:level]:
            if panel:
                bottom_y = bottom_y - 5.0 - (max(p[1] for p in panel) - min(p[1] for p in panel))
        return bottom_y

    def _draw_front_waistband(self, msp: Modelspace, points: PatternPoints) -> None:
        """单独绘制前腰头裁片（闭合轮廓，平移到门襟裁片下方）"""
        outline = getattr(points, 'front_waistband_outline', None)
        if not outline:
            return
        bottom_y = self._panel_stack_bottom_y(points, level=1)
        wb_max_y = max(p[1] for p in outline)
        offset_y = bottom_y - 5.0 - wb_max_y  # 与上方图形间隔5cm
        dxf_pts = [self._to_dxf_coords(x, y + offset_y) for x, y in outline]
        msp.add_lwpolyline(dxf_pts, close=True, dxfattribs={'layer': 'FRONTWAISTBAND'})
        # 裁片标注
        min_px = min(p[0] for p in outline)
        max_px = max(p[0] for p in outline)
        label_x, label_y = self._to_dxf_coords((min_px + max_px) / 2, wb_max_y + offset_y + 1.5)
        text = msp.add_text('FRONT_WAISTBAND', dxfattribs={'layer': 'FRONTWAISTBAND', 'height': 2.5 * self.scale})
        text.dxf.insert = (label_x, label_y)

    def _draw_pocket_patch_panel(self, msp: Modelspace, points: PatternPoints) -> None:
        """单独绘制袋贴裁片（闭合轮廓，平移到前腰头裁片下方）
        裁片上同时绘制月牙袋弧线和小表袋轮廓作为对位线。"""
        outline = getattr(points, 'pocket_patch_outline', None)
        if not outline:
            return
        bottom_y = self._panel_stack_bottom_y(points, level=2)
        patch_max_y = max(p[1] for p in outline)
        offset_y = bottom_y - 5.0 - patch_max_y  # 与上方图形间隔5cm
        dxf_pts = [self._to_dxf_coords(x, y + offset_y) for x, y in outline]
        msp.add_lwpolyline(dxf_pts, close=True, dxfattribs={'layer': 'POCKETPATCHPANEL'})

        def draw_line(pts, layer):
            line_pts = [self._to_dxf_coords(x, y + offset_y) for x, y in pts]
            msp.add_lwpolyline(line_pts, dxfattribs={'layer': layer})

        # 月牙袋弧线（袋口对位线）
        pocket = getattr(points, 'crescent_pocket', None)
        if pocket is not None:
            draw_line(pocket.pocket_curve, 'POCKET')
        # 小表袋轮廓（对位线）：顶边 + 外线 + 内线 + 底边
        wp = getattr(points, 'watch_pocket', None)
        if wp is not None:
            draw_line([wp.outer_upper, wp.inner_upper], 'WATCHPOCKET')
            draw_line(wp.outer_line, 'WATCHPOCKET')
            draw_line(wp.inner_line, 'WATCHPOCKET')
            draw_line(wp.bottom_curve, 'WATCHPOCKET')

        # 裁片标注
        min_px = min(p[0] for p in outline)
        max_px = max(p[0] for p in outline)
        label_x, label_y = self._to_dxf_coords((min_px + max_px) / 2, patch_max_y + offset_y + 1.5)
        text = msp.add_text('POCKET_PATCH', dxfattribs={'layer': 'POCKETPATCHPANEL', 'height': 2.5 * self.scale})
        text.dxf.insert = (label_x, label_y)

    def _draw_watch_pocket_panel(self, msp: Modelspace, points: PatternPoints) -> None:
        """单独绘制小表袋裁片（闭合轮廓，平移到袋贴裁片下方）"""
        outline = getattr(points, 'watch_pocket_outline', None)
        if not outline:
            return
        bottom_y = self._panel_stack_bottom_y(points, level=3)
        wp_max_y = max(p[1] for p in outline)
        offset_y = bottom_y - 5.0 - wp_max_y  # 与上方图形间隔5cm
        dxf_pts = [self._to_dxf_coords(x, y + offset_y) for x, y in outline]
        msp.add_lwpolyline(dxf_pts, close=True, dxfattribs={'layer': 'WATCHPOCKETPANEL'})
        # 裁片标注
        min_px = min(p[0] for p in outline)
        max_px = max(p[0] for p in outline)
        label_x, label_y = self._to_dxf_coords((min_px + max_px) / 2, wp_max_y + offset_y + 1.5)
        text = msp.add_text('WATCH_POCKET', dxfattribs={'layer': 'WATCHPOCKETPANEL', 'height': 2.5 * self.scale})
        text.dxf.insert = (label_x, label_y)

    def _draw_pocket_bag_panel(self, msp: Modelspace, points: PatternPoints) -> None:
        """单独绘制袋布裁片（闭合轮廓，沿袋布线镜像的完整袋布，平移到小表袋裁片下方）
        裁片上同时绘制对称轴（袋布线）和月牙袋省道弧线/省道点作为对位线。"""
        outline = getattr(points, 'pocket_bag_outline', None)
        if not outline:
            return
        bottom_y = self._panel_stack_bottom_y(points, level=4)
        bag_max_y = max(p[1] for p in outline)
        offset_y = bottom_y - 5.0 - bag_max_y  # 与上方图形间隔5cm
        dxf_pts = [self._to_dxf_coords(x, y + offset_y) for x, y in outline]
        msp.add_lwpolyline(dxf_pts, close=True, dxfattribs={'layer': 'POCKETBAGPANEL'})

        # 对称轴（袋布线）
        fold = getattr(points, 'pocket_bag_fold_line', None)
        if fold:
            fold_pts = [self._to_dxf_coords(x, y + offset_y) for x, y in fold]
            msp.add_lwpolyline(fold_pts, dxfattribs={'layer': 'POCKETBAGPANEL'})

        # 月牙袋省道弧线 + 省道点（袋口对位线）
        pocket = getattr(points, 'crescent_pocket', None)
        if pocket is not None:
            dart_pts = [self._to_dxf_coords(x, y + offset_y) for x, y in pocket.pocket_dart_curve]
            msp.add_lwpolyline(dart_pts, dxfattribs={'layer': 'POCKET'})
            dp = self._to_dxf_coords(pocket.pocket_dart[0], pocket.pocket_dart[1] + offset_y)
            size = 0.5 * self.scale
            msp.add_line((dp[0] - size, dp[1]), (dp[0] + size, dp[1]), dxfattribs={'layer': 'POCKET'})
            msp.add_line((dp[0], dp[1] - size), (dp[0], dp[1] + size), dxfattribs={'layer': 'POCKET'})

        # 裁片标注
        min_px = min(p[0] for p in outline)
        max_px = max(p[0] for p in outline)
        label_x, label_y = self._to_dxf_coords((min_px + max_px) / 2, bag_max_y + offset_y + 1.5)
        text = msp.add_text('POCKET_BAG', dxfattribs={'layer': 'POCKETBAGPANEL', 'height': 2.5 * self.scale})
        text.dxf.insert = (label_x, label_y)

    def _draw_crescent_pocket(self, msp: Modelspace, points: PatternPoints) -> None:
        """绘制月牙袋"""
        pocket = points.crescent_pocket
        waistband = points.waistband

        # 绘制月牙袋弧线（口袋开口）
        self._draw_polyline(msp, pocket.pocket_curve, 'POCKET')

        # 绘制月牙袋省道弧线
        self._draw_polyline(msp, pocket.pocket_dart_curve, 'POCKET')

        # 绘制月牙袋省道的两条垂直线
        dart_line_start1 = self._to_dxf_coords(pocket.pocket_width[0], pocket.pocket_width[1])
        dart_line_end1 = self._to_dxf_coords(pocket.pocket_dart_line_width[0], pocket.pocket_dart_line_width[1])
        msp.add_line(dart_line_start1, dart_line_end1, dxfattribs={'layer': 'POCKET'})

        dart_line_start2 = self._to_dxf_coords(pocket.pocket_dart[0], pocket.pocket_dart[1])
        dart_line_end2 = self._to_dxf_coords(pocket.pocket_dart_line_dart[0], pocket.pocket_dart_line_dart[1])
        msp.add_line(dart_line_start2, dart_line_end2, dxfattribs={'layer': 'POCKET'})

    def _draw_pocket_patch(self, msp: Modelspace, points: PatternPoints) -> None:
        """绘制袋贴"""
        patch = points.pocket_patch
        pocket = points.crescent_pocket

        def distance(p1, p2):
            return ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5

        # 绘制袋贴弧线
        self._draw_polyline(msp, patch.patch_curve, 'POCKETPATCH')

        # 绘制袋贴闭合区域（袋贴贴片）：
        # 袋贴下腰头顶点 -> 袋贴弧线 -> 袋贴外缝顶点 -> 外侧缝(向上) -> 月牙袋外缝顶点
        # -> 月牙袋省道弧线(反向) -> 月牙袋省道点 -> 下腰头(向内) -> 袋贴下腰头顶点
        patch_outline = []
        # 1. 袋贴弧线
        patch_outline.extend(patch.patch_curve)

        # 2. 沿外侧缝从袋贴外缝顶点向上到月牙袋外缝顶点
        found_patch_outer = False
        for p in points.outer_seam_curve:
            if not found_patch_outer and distance(p, patch.patch_outer_seam) < 0.3:
                found_patch_outer = True
            if found_patch_outer:
                patch_outline.append(p)
            if found_patch_outer and distance(p, pocket.pocket_outer) < 0.3:
                break

        # 3. 沿月牙袋省道弧线反向（外缝顶点 -> 省道点）
        patch_outline.extend(reversed(pocket.pocket_dart_curve))

        # 4. 沿下腰头从月牙袋省道点向内到袋贴下腰头顶点
        found_dart = False
        for p in points.lower_waistline_curve:
            if not found_dart and distance(p, pocket.pocket_dart) < 0.3:
                found_dart = True
            if found_dart:
                patch_outline.append(p)
            if found_dart and distance(p, patch.patch_lower_waist) < 0.3:
                break

        dxf_patch_points = [self._to_dxf_coords(x, y) for x, y in patch_outline]
        msp.add_lwpolyline(dxf_patch_points, close=True, dxfattribs={'layer': 'POCKETPATCH'})

    def _draw_pocket_bag(self, msp: Modelspace, points: PatternPoints) -> None:
        """绘制袋布"""
        bag = points.pocket_bag

        # 袋布线（上腰头顶点 → 内端点）
        self._draw_polyline(msp, bag.bag_line, 'POCKETBAG')
        # 底边（内端点 → 拐点）
        self._draw_polyline(msp, bag.bag_bottom_edge, 'POCKETBAG')
        # 袋布弧线（拐点 → 外缝顶点）
        self._draw_polyline(msp, bag.bag_curve, 'POCKETBAG')

        # 袋布闭合区域
        bag_outline = []
        bag_outline.extend(bag.bag_line)
        bag_outline.extend(bag.bag_bottom_edge[1:])
        bag_outline.extend(bag.bag_curve[1:])
        bag_outline.extend(bag.bag_top_edge[1:])
        dxf_bag_points = [self._to_dxf_coords(x, y) for x, y in bag_outline]
        msp.add_lwpolyline(dxf_bag_points, close=True, dxfattribs={'layer': 'POCKETBAG'})

    def _draw_watch_pocket(self, msp: Modelspace, points: PatternPoints) -> None:
        """绘制小表袋"""
        wp = points.watch_pocket

        # 顶边（上外 → 上内）
        self._draw_polyline(msp, [wp.outer_upper, wp.inner_upper], 'WATCHPOCKET')
        # 外线（上外 → 下外）
        self._draw_polyline(msp, wp.outer_line, 'WATCHPOCKET')
        # 内线（上内 → 下内）
        self._draw_polyline(msp, wp.inner_line, 'WATCHPOCKET')
        # 底边（沿袋贴弧线 下内 → 下外）
        self._draw_polyline(msp, wp.bottom_curve, 'WATCHPOCKET')

        # 小表袋闭合区域
        wp_outline = []
        wp_outline.extend([wp.outer_upper, wp.inner_upper])
        wp_outline.extend(wp.inner_line[1:])
        wp_outline.extend(wp.bottom_curve[1:])
        wp_outline.extend(list(reversed(wp.outer_line))[1:])
        dxf_wp_points = [self._to_dxf_coords(x, y) for x, y in wp_outline]
        msp.add_lwpolyline(dxf_wp_points, close=True, dxfattribs={'layer': 'WATCHPOCKET'})


class SimpleDXFExporter:
    """简化版DXF导出器 - 直接输出闭合轮廓，适合切割"""

    def __init__(self, units: str = 'mm'):
        self.units = units
        self.scale = 10.0 if units == 'mm' else 1.0

    def export(self, points: PatternPoints, filepath: str) -> None:
        """导出简化版DXF - 只有闭合轮廓"""
        # 使用R2000格式兼容ET
        doc = ezdxf.new('R2000')
        msp = doc.modelspace()

        doc.units = ezdxf.units.MM if self.units == 'mm' else ezdxf.units.CM

        # 构建闭合轮廓（裤身）
        outline = []

        # 顺序: 腰围外 -> 外侧缝 -> 脚口外 -> 脚口内 -> 内侧缝 -> 立裆 -> 前浪 -> 腰围内 -> 腰围线 -> 腰围外

        # 1. 腰围外开始，沿外侧缝向下
        outline.extend(reversed(points.outer_seam_curve))

        # 2. 脚口外到脚口内
        outline.append(points.knee_hem.hem_inner)

        # 3. 沿内侧缝向上
        outline.extend(points.inner_seam_curve[1:])

        # 4. 沿前浪向上到腰围内
        outline.extend(reversed(points.front_rise_curve[:-1]))

        # 5. 沿腰围线回到腰围外
        outline.extend(reversed(points.waistline_curve[:-1]))

        # 转换坐标
        dxf_points = [(x * self.scale, y * self.scale) for x, y in outline]

        # 添加闭合多段线
        msp.add_lwpolyline(dxf_points, close=True)

        # 如果有腰头，也添加腰头轮廓
        if hasattr(points, 'waistband') and hasattr(points, 'lower_waistline_curve'):
            waistband_outline = []
            waistband_outline.extend(points.waistline_curve)
            waistband_outline.extend(reversed(points.lower_waistline_curve))
            dxf_wb_points = [(x * self.scale, y * self.scale) for x, y in waistband_outline]
            msp.add_lwpolyline(dxf_wb_points, close=True)

        # 如果有前门襟，也添加前门襟轮廓
        if hasattr(points, 'front_fly'):
            fly = points.front_fly
            fly_outline = []
            fly_outline.append(fly.fly_start_point)  # 下腰头门襟点
            fly_outline.append(fly.fly_end_point)    # 沿着门襟线到弧起点
            fly_outline.extend(fly.fly_curve)        # 沿着弧线到门襟外端点
            # 从门襟外端点沿着前浪到下腰头内缝顶点
            def distance(p1, p2):
                return ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5
            found_outer = False
            for p in points.front_rise_curve:
                if not found_outer and distance(p, fly.fly_outer_end) < 0.2:
                    found_outer = True
                if found_outer:
                    fly_outline.append(p)
                if hasattr(points, 'waistband') and found_outer:
                    if distance(p, points.waistband.lower_waist_inner) < 0.3:
                        break
            # 添加下腰头内缝顶点
            if hasattr(points, 'waistband'):
                fly_outline.append(points.waistband.lower_waist_inner)
                # 沿着下腰头曲线从内到外，直到门襟起点
                found_lower_inner = False
                for p in reversed(points.lower_waistline_curve):
                    if not found_lower_inner:
                        if distance(p, points.waistband.lower_waist_inner) < 0.2:
                            found_lower_inner = True
                    if found_lower_inner:
                        fly_outline.append(p)
                        if distance(p, fly.fly_start_point) < 0.3:
                            break
            # 确保闭合
            fly_outline.append(fly.fly_start_point)

            dxf_fly_points = [(x * self.scale, y * self.scale) for x, y in fly_outline]
            msp.add_lwpolyline(dxf_fly_points, close=True)

            # 门襟裁片单独平移到前片下方
            panel_outline = getattr(fly, 'fly_panel_outline', None)
            if panel_outline:
                panel_max_y = max(p[1] for p in panel_outline)
                offset_y = -(panel_max_y + 5.0)
                dxf_panel_points = [(x * self.scale, (y + offset_y) * self.scale) for x, y in panel_outline]
                msp.add_lwpolyline(dxf_panel_points, close=True)

        # 前腰头裁片平移到门襟裁片下方单独展示
        front_wb = getattr(points, 'front_waistband_outline', None)
        if front_wb:
            bottom_y = 0.0
            fly = getattr(points, 'front_fly', None)
            fly_outline = getattr(fly, 'fly_panel_outline', None) if fly else None
            if fly_outline:
                bottom_y = (min(p[1] for p in fly_outline)
                            - (max(p[1] for p in fly_outline) + 5.0))
            wb_offset_y = bottom_y - 5.0 - max(p[1] for p in front_wb)
            dxf_wb_points = [(x * self.scale, (y + wb_offset_y) * self.scale) for x, y in front_wb]
            msp.add_lwpolyline(dxf_wb_points, close=True)

        # 袋贴裁片平移到前腰头裁片下方单独展示
        patch_panel = getattr(points, 'pocket_patch_outline', None)
        if patch_panel:
            bottom_y = 0.0
            fly = getattr(points, 'front_fly', None)
            fly_outline = getattr(fly, 'fly_panel_outline', None) if fly else None
            if fly_outline:
                bottom_y = (min(p[1] for p in fly_outline)
                            - (max(p[1] for p in fly_outline) + 5.0))
            wb = getattr(points, 'front_waistband_outline', None)
            if wb:
                bottom_y = bottom_y - 5.0 - (max(p[1] for p in wb) - min(p[1] for p in wb))
            patch_offset_y = bottom_y - 5.0 - max(p[1] for p in patch_panel)
            dxf_pp_points = [(x * self.scale, (y + patch_offset_y) * self.scale) for x, y in patch_panel]
            msp.add_lwpolyline(dxf_pp_points, close=True)

        # 小表袋裁片平移到袋贴裁片下方单独展示
        wp_panel = getattr(points, 'watch_pocket_outline', None)
        if wp_panel:
            bottom_y = 0.0
            fly = getattr(points, 'front_fly', None)
            fly_outline = getattr(fly, 'fly_panel_outline', None) if fly else None
            if fly_outline:
                bottom_y = (min(p[1] for p in fly_outline)
                            - (max(p[1] for p in fly_outline) + 5.0))
            for panel in (getattr(points, 'front_waistband_outline', None),
                          getattr(points, 'pocket_patch_outline', None)):
                if panel:
                    bottom_y = bottom_y - 5.0 - (max(p[1] for p in panel) - min(p[1] for p in panel))
            wp_offset_y = bottom_y - 5.0 - max(p[1] for p in wp_panel)
            dxf_wp_points = [(x * self.scale, (y + wp_offset_y) * self.scale) for x, y in wp_panel]
            msp.add_lwpolyline(dxf_wp_points, close=True)

        # 袋布裁片平移到小表袋裁片下方单独展示
        bag_panel = getattr(points, 'pocket_bag_outline', None)
        if bag_panel:
            bottom_y = 0.0
            fly = getattr(points, 'front_fly', None)
            for panel in (getattr(fly, 'fly_panel_outline', None) if fly else None,
                          getattr(points, 'front_waistband_outline', None),
                          getattr(points, 'pocket_patch_outline', None),
                          getattr(points, 'watch_pocket_outline', None)):
                if panel:
                    bottom_y = bottom_y - 5.0 - (max(p[1] for p in panel) - min(p[1] for p in panel))
            bag_offset_y = bottom_y - 5.0 - max(p[1] for p in bag_panel)
            dxf_bg_points = [(x * self.scale, (y + bag_offset_y) * self.scale) for x, y in bag_panel]
            msp.add_lwpolyline(dxf_bg_points, close=True)

        # 前片整体轮廓裁片平移到右侧单独展示
        front_panel = getattr(points, 'front_panel_outline', None)
        if front_panel:
            panel_min_x = min(p[0] for p in front_panel)
            offset_x = points.front_rise.crotch_extension_point[0] + 8.0 - panel_min_x
            dxf_fp_points = [((x + offset_x) * self.scale, y * self.scale) for x, y in front_panel]
            msp.add_lwpolyline(dxf_fp_points, close=True)
            # 裁片上的前门襟（门襟线 + 门襟弧线）
            fly = getattr(points, 'front_fly', None)
            if fly is not None:
                fly_start = ((fly.fly_start_point[0] + offset_x) * self.scale, fly.fly_start_point[1] * self.scale)
                fly_arc_start = ((fly.fly_end_point[0] + offset_x) * self.scale, fly.fly_end_point[1] * self.scale)
                msp.add_line(fly_start, fly_arc_start)
                fly_curve_pts = [((x + offset_x) * self.scale, y * self.scale) for x, y in fly.fly_curve]
                msp.add_lwpolyline(fly_curve_pts)

        # 如果有月牙袋，也添加月牙袋轮廓
        if hasattr(points, 'crescent_pocket'):
            pocket = points.crescent_pocket
            waistband = points.waistband
            pocket_outline = []
            # 1. 从月牙袋外缝顶点开始
            pocket_outline.append(pocket.pocket_outer)
            # 2. 沿袋口弧线到宽顶点
            pocket_outline.extend(pocket.pocket_curve[1:])
            # 3. 沿下腰头弧线到上腰头外缝顶点
            def distance(p1, p2):
                return ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5
            found_width = False
            for p in points.lower_waistline_curve:
                if not found_width and distance(p, pocket.pocket_width) < 0.3:
                    found_width = True
                if found_width:
                    pocket_outline.append(p)
                if found_width and distance(p, waistband.lower_waist_outer) < 0.3:
                    break
            # 4. 沿外侧缝弧线回到月牙袋外缝顶点
            found_lower_waist = False
            for p in points.outer_seam_curve:
                if not found_lower_waist and distance(p, waistband.lower_waist_outer) < 0.3:
                    found_lower_waist = True
                if found_lower_waist:
                    pocket_outline.append(p)
                if found_lower_waist and distance(p, pocket.pocket_outer) < 0.3:
                    break

            dxf_pocket_points = [(x * self.scale, y * self.scale) for x, y in pocket_outline]
            msp.add_lwpolyline(dxf_pocket_points, close=True)

            # 添加月牙袋省道弧线
            dxf_dart_curve = [(x * self.scale, y * self.scale) for x, y in pocket.pocket_dart_curve]
            msp.add_lwpolyline(dxf_dart_curve, dxfattribs={'layer': 'POCKET'})

            # 添加月牙袋省道的两条直线
            dart_line_start1 = (pocket.pocket_width[0] * self.scale, pocket.pocket_width[1] * self.scale)
            dart_line_end1 = (pocket.pocket_dart_line_width[0] * self.scale, pocket.pocket_dart_line_width[1] * self.scale)
            msp.add_line(dart_line_start1, dart_line_end1, dxfattribs={'layer': 'POCKET'})

            dart_line_start2 = (pocket.pocket_dart[0] * self.scale, pocket.pocket_dart[1] * self.scale)
            dart_line_end2 = (pocket.pocket_dart_line_dart[0] * self.scale, pocket.pocket_dart_line_dart[1] * self.scale)
            msp.add_line(dart_line_start2, dart_line_end2, dxfattribs={'layer': 'POCKET'})

        # 如果有袋贴，也添加袋贴轮廓（闭合贴片）
        if hasattr(points, 'pocket_patch'):
            patch = points.pocket_patch
            pocket = points.crescent_pocket

            def distance_patch(p1, p2):
                return ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5

            patch_outline = []
            # 1. 袋贴弧线
            patch_outline.extend(patch.patch_curve)
            # 2. 沿外侧缝从袋贴外缝顶点向上到月牙袋外缝顶点
            found_patch_outer = False
            for p in points.outer_seam_curve:
                if not found_patch_outer and distance_patch(p, patch.patch_outer_seam) < 0.3:
                    found_patch_outer = True
                if found_patch_outer:
                    patch_outline.append(p)
                if found_patch_outer and distance_patch(p, pocket.pocket_outer) < 0.3:
                    break
            # 3. 沿月牙袋省道弧线反向（外缝顶点 -> 省道点）
            patch_outline.extend(reversed(pocket.pocket_dart_curve))
            # 4. 沿下腰头从月牙袋省道点向内到袋贴下腰头顶点
            found_dart = False
            for p in points.lower_waistline_curve:
                if not found_dart and distance_patch(p, pocket.pocket_dart) < 0.3:
                    found_dart = True
                if found_dart:
                    patch_outline.append(p)
                if found_dart and distance_patch(p, patch.patch_lower_waist) < 0.3:
                    break

            dxf_patch_points = [(x * self.scale, y * self.scale) for x, y in patch_outline]
            msp.add_lwpolyline(dxf_patch_points, close=True)

            # 单独添加袋贴弧线
            dxf_patch_curve = [(x * self.scale, y * self.scale) for x, y in patch.patch_curve]
            msp.add_lwpolyline(dxf_patch_curve)

        # 如果有袋布，也添加袋布轮廓（闭合袋布片）
        if hasattr(points, 'pocket_bag'):
            bag = points.pocket_bag
            bag_outline = []
            bag_outline.extend(bag.bag_line)
            bag_outline.extend(bag.bag_bottom_edge[1:])
            bag_outline.extend(bag.bag_curve[1:])
            bag_outline.extend(bag.bag_top_edge[1:])
            dxf_bag_points = [(x * self.scale, y * self.scale) for x, y in bag_outline]
            msp.add_lwpolyline(dxf_bag_points, close=True)

        # 如果有小表袋，也添加小表袋轮廓（闭合小表袋片）
        if hasattr(points, 'watch_pocket'):
            wp = points.watch_pocket
            wp_outline = []
            wp_outline.extend([wp.outer_upper, wp.inner_upper])
            wp_outline.extend(wp.inner_line[1:])
            wp_outline.extend(wp.bottom_curve[1:])
            wp_outline.extend(list(reversed(wp.outer_line))[1:])
            dxf_wp_points = [(x * self.scale, y * self.scale) for x, y in wp_outline]
            msp.add_lwpolyline(dxf_wp_points, close=True)

        doc.saveas(filepath)
        print(f"简化版DXF已保存至: {filepath}")
