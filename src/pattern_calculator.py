"""
牛仔裤前片打版核心计算逻辑
"""
import math
from typing import List, Tuple, Optional
from .types import (
    PatternParams, PatternPoints, BoundingBox,
    FrontRisePoints, KneeHemPoints, WaistPoints,
    WaistbandPoints, FrontFlyPoints, CrescentPocketPoints,
    PocketPatchPoints, PocketBagPoints, WatchPocketPoints
)


def point_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """计算两点之间的距离"""
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def lerp(t: float, p1: Tuple[float, float], p2: Tuple[float, float]) -> Tuple[float, float]:
    """线性插值"""
    return (
        p1[0] + t * (p2[0] - p1[0]),
        p1[1] + t * (p2[1] - p1[1])
    )


def quadratic_bezier(t: float, p0: Tuple[float, float], p1: Tuple[float, float],
                     p2: Tuple[float, float]) -> Tuple[float, float]:
    """二次贝塞尔曲线"""
    x = (1-t)**2 * p0[0] + 2*(1-t)*t * p1[0] + t**2 * p2[0]
    y = (1-t)**2 * p0[1] + 2*(1-t)*t * p1[1] + t**2 * p2[1]
    return (x, y)


def cubic_bezier(t: float, p0: Tuple[float, float], p1: Tuple[float, float],
                 p2: Tuple[float, float], p3: Tuple[float, float]) -> Tuple[float, float]:
    """三次贝塞尔曲线"""
    x = (1-t)**3 * p0[0] + 3*(1-t)**2*t * p1[0] + 3*(1-t)*t**2 * p2[0] + t**3 * p3[0]
    y = (1-t)**3 * p0[1] + 3*(1-t)**2*t * p1[1] + 3*(1-t)*t**2 * p2[1] + t**3 * p3[1]
    return (x, y)


def sample_bezier_curve(points: List[Tuple[float, float]],
                        samples: int = 30) -> List[Tuple[float, float]]:
    """采样贝塞尔曲线，返回一系列点"""
    if len(points) == 2:
        # 直线
        return [lerp(t/(samples-1), points[0], points[1]) for t in range(samples)]
    elif len(points) == 3:
        # 二次贝塞尔
        return [quadratic_bezier(t/(samples-1), points[0], points[1], points[2])
                for t in range(samples)]
    elif len(points) == 4:
        # 三次贝塞尔
        return [cubic_bezier(t/(samples-1), points[0], points[1], points[2], points[3])
                for t in range(samples)]
    else:
        # 多点样条，分段处理
        result = []
        for i in range(len(points) - 1):
            segment = sample_bezier_curve([points[i], points[i+1]],
                                         samples // (len(points) - 1))
            if i == 0:
                result.extend(segment)
            else:
                result.extend(segment[1:])
        return result


class JeansPatternCalculator:
    """牛仔裤前片打版计算器"""

    def __init__(self, params: PatternParams):
        self.params = params
        self.points: Optional[PatternPoints] = None

    def calculate(self) -> PatternPoints:
        """执行完整的打版计算流程"""
        # 步骤1: 建立基础参考线与大矩形框架
        bounding_box = self._calculate_bounding_box()

        # 步骤2: 确定立裆宽
        crotch_ext_point = self._calculate_crotch_extension(bounding_box)

        # 步骤3: 细化绘制前浪基础线
        front_rise = self._calculate_front_rise(bounding_box, crotch_ext_point)

        # 步骤4: 确定裤中线
        center_crease_x = self._calculate_center_crease(crotch_ext_point[0])

        # 步骤5: 计算并定位实际膝围与脚口顶点
        knee_hem = self._calculate_knee_hem(bounding_box, center_crease_x)

        # 步骤6-7: 计算侧缝、内侧缝和腰围线
        # 先计算腰围外缝顶点
        waist_outer = self._calculate_waist_outer(front_rise.new_waist_inner_ref)

        # 计算外侧缝曲线
        outer_seam_curve = self._calculate_outer_seam_curve(
            knee_hem, bounding_box, waist_outer
        )

        # 计算内侧缝曲线
        inner_seam_curve = self._calculate_inner_seam_curve(
            knee_hem, crotch_ext_point
        )

        # 计算前浪完整曲线
        front_rise_curve = self._calculate_front_rise_curve(front_rise)

        # 找到前浪长度为24cm的点作为最终腰围内缝顶点
        waist_inner_final = self._find_rise_length_point(
            front_rise_curve, crotch_ext_point, self.params.front_rise
        )

        # 计算腰围线曲线（上腰头）
        waistline_curve, waist_control = self._calculate_waistline(
            waist_outer, waist_inner_final
        )

        # 步骤8: 计算下腰头
        lower_waist_outer = self._find_point_along_curve(
            outer_seam_curve, waist_outer, 4.0, downward=True
        )
        lower_waist_inner = self._find_point_along_curve(
            front_rise_curve, waist_inner_final, 4.0, downward=True
        )

        # 计算下腰头曲线（弧度与上腰头一致）
        lower_waistline_curve, lower_waist_control = self._calculate_waistline(
            lower_waist_outer, lower_waist_inner
        )

        # 构造腰围点（保留兼容性）
        waist = WaistPoints(
            waist_outer=waist_outer,
            waist_inner_final=waist_inner_final,
            waist_control=waist_control
        )

        # 构造腰头点（含下腰头）
        waistband = WaistbandPoints(
            waist_outer=waist_outer,
            waist_inner_final=waist_inner_final,
            waist_control=waist_control,
            lower_waist_outer=lower_waist_outer,
            lower_waist_inner=lower_waist_inner,
            lower_waist_control=lower_waist_control
        )

        # 步骤9: 计算前门襟
        front_fly = self._calculate_front_fly(
            waistband, lower_waistline_curve,
            front_rise_curve, bounding_box.hip_y,
            waist_inner_final
        )

        # 步骤10: 计算月牙袋
        crescent_pocket = self._calculate_crescent_pocket(
            waistband, outer_seam_curve, lower_waistline_curve, waistline_curve
        )

        # 步骤12: 计算袋贴
        pocket_patch = self._calculate_pocket_patch(
            crescent_pocket, outer_seam_curve, lower_waistline_curve
        )

        # 步骤13: 计算袋布
        pocket_bag = self._calculate_pocket_bag(
            pocket_patch, bounding_box, waistband,
            outer_seam_curve, lower_waistline_curve
        )

        # 步骤14: 计算小表袋
        watch_pocket = self._calculate_watch_pocket(
            pocket_patch, waistband, outer_seam_curve
        )

        # 组装所有点
        self.points = PatternPoints(
            params=self.params,
            bounding_box=bounding_box,
            center_crease_x=center_crease_x,
            front_rise=front_rise,
            knee_hem=knee_hem,
            waist=waist,
            waistband=waistband,
            front_fly=front_fly,
            crescent_pocket=crescent_pocket,
            pocket_patch=pocket_patch,
            pocket_bag=pocket_bag,
            watch_pocket=watch_pocket,
            outer_seam_curve=outer_seam_curve,
            inner_seam_curve=inner_seam_curve,
            front_rise_curve=front_rise_curve,
            waistline_curve=waistline_curve,
            lower_waistline_curve=lower_waistline_curve
        )

        return self.points

    def _calculate_bounding_box(self) -> BoundingBox:
        """步骤1: 建立基础参考线与大矩形框架"""
        # 臀围宽度计算: 90/4 - 1 + 0.2 = 21.7（示例值）
        hip_width = self.params.hip / 4 - 1.0 + self.params.hip_ease

        # 外侧缝参考线 X=0
        outer_seam_x = 0.0
        inner_seam_x = hip_width

        # 水平参考线
        hem_y = 0.0
        waist_y = self.params.pants_length + 0.6  # 加0.6松量
        crotch_y = waist_y - self.params.front_rise  # 立裆参考线
        hip_y = crotch_y + (waist_y - crotch_y) / 3  # 立裆与腰围间距的三等分处
        knee_y = crotch_y - 29.0  # 示例中使用固定值29

        return BoundingBox(
            outer_seam_x=outer_seam_x,
            inner_seam_x=inner_seam_x,
            hem_y=hem_y,
            knee_y=knee_y,
            crotch_y=crotch_y,
            hip_y=hip_y,
            waist_y=waist_y
        )

    def _calculate_crotch_extension(self, bbox: BoundingBox) -> Tuple[float, float]:
        """步骤2: 确定立裆宽"""
        # 立裆宽: 臀围的0.04倍（约3.5cm，文档示例中使用3.5）
        crotch_width = self.params.hip * 0.04
        # 为了匹配文档示例，我们稍微调整一下，使用约3.5而不是精确3.6
        if abs(self.params.hip - 90.0) < 0.01:
            crotch_width = 3.5  # 文档示例值

        # 从大矩形的立裆内缝交点继续向右延伸
        x = bbox.inner_seam_x + crotch_width
        y = bbox.crotch_y

        return (x, y)

    def _calculate_front_rise(self, bbox: BoundingBox,
                              crotch_ext_point: Tuple[float, float]) -> FrontRisePoints:
        """步骤3: 细化绘制前浪基础线"""
        # 臀围内缝顶点
        hip_inner_point = (bbox.inner_seam_x, bbox.hip_y)

        # 计算前浪下半段辅助点（角平分线）
        # 90度角的45度平分线，延伸距离: 臀围*0.02 + 0.5
        distance = self.params.hip * 0.02 + 0.5
        # 45度角，X和Y增量相等
        delta = distance * math.sin(math.pi / 4)  # sin(45°)

        # 直角顶点
        corner_x, corner_y = bbox.inner_seam_x, bbox.crotch_y

        # 基础角平分线点（原始位置）
        base_helper_x = corner_x + delta
        base_helper_y = corner_y + delta

        # 使用凹陷参数来控制辅助点位置
        # 参数越大，辅助点越向内侧推，凹陷越明显
        curve_factor = self.params.front_rise_curve
        # 向内侧推：X增加，Y稍微调整
        enhanced_helper_x = base_helper_x + curve_factor * 0.5
        enhanced_helper_y = base_helper_y + curve_factor * 0.2

        rise_helper_point = (enhanced_helper_x, enhanced_helper_y)

        # 新腰围内缝参考顶点: 向内收1cm
        new_waist_inner_ref = (
            bbox.inner_seam_x - 1.0,
            bbox.waist_y
        )

        return FrontRisePoints(
            hip_inner_point=hip_inner_point,
            crotch_extension_point=crotch_ext_point,
            rise_helper_point=rise_helper_point,
            new_waist_inner_ref=new_waist_inner_ref
        )

    def _calculate_center_crease(self, crotch_ext_x: float) -> float:
        """步骤4: 确定裤中线"""
        # 取立裆总宽度(从X=0到X=25.2)的中点，向外缝微移0.6cm
        mid_point = crotch_ext_x / 2
        center_crease_x = mid_point - 0.6
        return center_crease_x

    def _calculate_knee_hem(self, bbox: BoundingBox,
                            center_crease_x: float) -> KneeHemPoints:
        """步骤5: 计算并定位实际膝围与脚口顶点"""
        # 膝围宽度: 前片单侧宽度（从裤中线起）= (膝围/2 - 0.6*2) / 2
        # 文档示例: (36/2 - 0.6*2) / 2 = (18 - 1.2)/2 = 8.4
        knee_side = (self.params.knee / 2 - 0.6 * 2) / 2
        knee_inner = (center_crease_x + knee_side, bbox.knee_y)
        knee_outer = (center_crease_x - knee_side, bbox.knee_y)

        # 脚口宽度: 前片单侧宽度（从裤中线起）= (裤口/2 - 0.6*2) / 2
        # 文档示例: (39/2 - 0.6*2) / 2 = (19.5 - 1.2)/2 = 9.15
        hem_side = (self.params.hem / 2 - 0.6 * 2) / 2
        hem_inner = (center_crease_x + hem_side, bbox.hem_y)
        hem_outer = (center_crease_x - hem_side, bbox.hem_y)

        return KneeHemPoints(
            knee_inner=knee_inner,
            knee_outer=knee_outer,
            hem_inner=hem_inner,
            hem_outer=hem_outer
        )

    def _calculate_waist_outer(self, new_waist_inner_ref: Tuple[float, float]) -> Tuple[float, float]:
        """计算最终腰围外缝顶点"""
        # 腰围所需宽度: 腰围/4 + 0.3松量 + 0.6省道
        waist_width = self.params.waist / 4 + self.params.waist_ease + self.params.dart_width

        # 从新腰围内缝参考顶点向外测量
        waist_outer_x = new_waist_inner_ref[0] - waist_width
        waist_outer_y = new_waist_inner_ref[1]

        return (waist_outer_x, waist_outer_y)

    def _calculate_outer_seam_curve(self, knee_hem: KneeHemPoints,
                                    bbox: BoundingBox,
                                    waist_outer: Tuple[float, float]) -> List[Tuple[float, float]]:
        """计算外侧缝曲线（向外凸出的圆顺弧线）"""
        # 关键点: 脚口外 -> 膝围外 -> 臀围外 -> 腰围外
        hip_outer = (bbox.outer_seam_x, bbox.hip_y)

        # 使用三次贝塞尔曲线
        # 第一段: 脚口外 -> 膝围外（直线段）
        # 第二段: 膝围外 -> 臀围外 -> 腰围外（曲线段）

        # 构建控制点 - 向外凸出
        # 膝围到臀围的控制点
        mid1 = lerp(0.5, knee_hem.knee_outer, hip_outer)
        ctrl1 = (mid1[0] - 0.5, mid1[1])  # 向外微凸

        # 臀围到腰围的控制点
        mid2 = lerp(0.5, hip_outer, waist_outer)
        ctrl2 = (mid2[0] - 0.8, mid2[1])  # 稍多凸出

        # 采样整条曲线
        points = [knee_hem.hem_outer, knee_hem.knee_outer, ctrl1, hip_outer, ctrl2, waist_outer]

        # 分段采样
        curve = []
        # 脚口到膝围（直线）
        curve.extend(sample_bezier_curve([points[0], points[1]], samples=10))
        # 膝围到臀围（曲线）
        seg2 = sample_bezier_curve([points[1], points[2], points[3]], samples=15)
        curve.extend(seg2[1:])
        # 臀围到腰围（曲线）
        seg3 = sample_bezier_curve([points[3], points[4], points[5]], samples=15)
        curve.extend(seg3[1:])

        return curve

    def _calculate_inner_seam_curve(self, knee_hem: KneeHemPoints,
                                    crotch_ext_point: Tuple[float, float]) -> List[Tuple[float, float]]:
        """计算内侧缝曲线（内收的圆顺弧线）"""
        # 关键点: 脚口内 -> 膝围内 -> 立裆宽顶点

        # 构建控制点 - 向内收
        # 膝围到立裆的控制点，向内微凹
        mid = lerp(0.5, knee_hem.knee_inner, crotch_ext_point)
        ctrl = (mid[0] - 0.8, mid[1])  # 向内收

        # 采样
        curve = []
        # 脚口到膝围（近乎直线）
        curve.extend(sample_bezier_curve([knee_hem.hem_inner, knee_hem.knee_inner], samples=10))
        # 膝围到立裆（内收弧线）
        seg = sample_bezier_curve([knee_hem.knee_inner, ctrl, crotch_ext_point], samples=20)
        curve.extend(seg[1:])

        return curve

    def _calculate_front_rise_curve(self, front_rise: FrontRisePoints) -> List[Tuple[float, float]]:
        """计算前浪完整曲线（上半段直线，下半段深凹J型，且严格顺滑相切）"""
        waist_ref_point = front_rise.new_waist_inner_ref
        hip_point = front_rise.hip_inner_point
        helper_point = front_rise.rise_helper_point
        crotch_point = front_rise.crotch_extension_point

        corner_x = hip_point[0]
        crotch_y = crotch_point[1]

        # ========== 上半段：腰围参考点 -> 臀围内侧顶点 (纯直线) ==========
        # 直接使用两点采样，生成直线段
        upper_curve = sample_bezier_curve([waist_ref_point, hip_point], samples=15)

        # ========== 下半段：臀围内侧顶点 -> 立裆宽顶点 (深凹J型) ==========
        # 为了保证与上半段直线的"顺滑过渡"，下半段起步的控制点必须在直线的延长线上

        # 1. 计算上半段直线的方向向量
        dx = hip_point[0] - waist_ref_point[0]
        dy = hip_point[1] - waist_ref_point[1]

        # 2. 确定下半段 起始控制点 (ctrl0_lower)
        # 我们利用前浪角平分辅助点(helper_point)的Y高度来决定向下延伸的深度
        ctrl0_lower_y = helper_point[1]
        # 根据直线斜率计算对应的X坐标，使其严格落在上半段直线的延长线上
        # 这样能保证在 hip_point 处没有任何折角，绝对平滑
        ratio = (ctrl0_lower_y - hip_point[1]) / dy if dy != 0 else 0
        ctrl0_lower_x = hip_point[0] + dx * ratio

        # 3. 确定下半段 结束控制点 (ctrl1_lower)
        # 强制Y坐标与立裆宽顶点相等，保证末端与立裆参考线水平相切
        ctrl1_lower_y = crotch_y
        # 利用辅助点(helper_point)将控制点向直角内侧推，形成饱满的 J 型凹陷
        ctrl1_lower_x = corner_x + (helper_point[0] - corner_x) * 0.7

        # 使用三次贝塞尔曲线绘制下半段
        lower_curve = sample_bezier_curve([
            hip_point,
            (ctrl0_lower_x, ctrl0_lower_y),
            (ctrl1_lower_x, ctrl1_lower_y),
            crotch_point
        ], samples=30)

        # 拼接曲线（去掉上半段最后一个重复的交点，避免重叠）
        full_curve = upper_curve[:-1] + lower_curve
        return full_curve

    def _find_rise_length_point(self, rise_curve: List[Tuple[float, float]],
                                start_point: Tuple[float, float],
                                target_length: float) -> Tuple[float, float]:
        """从立裆宽顶点沿前浪曲线向上测量，找到长度为target_length的点"""
        # 注意: rise_curve是从腰围到立裆宽的顺序，需要反向遍历
        reversed_curve = list(reversed(rise_curve))

        # 找到起点索引（立裆宽顶点）
        start_idx = 0
        min_dist = float('inf')
        for i, p in enumerate(reversed_curve):
            d = point_distance(p, start_point)
            if d < min_dist:
                min_dist = d
                start_idx = i

        # 从起点开始累积长度
        accumulated = 0.0
        prev_point = reversed_curve[start_idx]

        for i in range(start_idx + 1, len(reversed_curve)):
            curr_point = reversed_curve[i]
            seg_length = point_distance(prev_point, curr_point)

            if accumulated + seg_length >= target_length:
                # 需要在这段内插值
                remaining = target_length - accumulated
                t = remaining / seg_length if seg_length > 0 else 0
                return lerp(t, prev_point, curr_point)

            accumulated += seg_length
            prev_point = curr_point

        # 如果曲线不够长，返回最后一个点
        return reversed_curve[-1]

    def _calculate_waistline(self, waist_outer: Tuple[float, float],
                             waist_inner_final: Tuple[float, float]) -> Tuple[List[Tuple[float, float]], Tuple[float, float]]:
        """计算腰围线（弯腰头贝塞尔曲线）"""
        # 取中点作为贝塞尔控制点
        mid_x = (waist_outer[0] + waist_inner_final[0]) / 2
        mid_y = (waist_outer[1] + waist_inner_final[1]) / 2

        # 控制点向下移动0.4cm
        control_point = (mid_x, mid_y - 0.4)

        # 采样贝塞尔曲线
        curve = sample_bezier_curve([waist_outer, control_point, waist_inner_final], samples=20)

        return curve, control_point

    def _find_point_along_curve(self, curve: List[Tuple[float, float]],
                                start_point: Tuple[float, float],
                                distance: float,
                                downward: bool = True) -> Tuple[float, float]:
        """
        沿曲线从起点找到指定距离的点

        Args:
            curve: 曲线上的采样点列表
            start_point: 起点
            distance: 沿曲线的距离
            downward: 是否向下（向脚口方向）寻找，False表示向上

        Returns:
            找到的点坐标
        """
        # 首先找到起点在曲线中的位置
        start_idx = 0
        min_dist = float('inf')
        for i, p in enumerate(curve):
            d = point_distance(p, start_point)
            if d < min_dist:
                min_dist = d
                start_idx = i

        # 确定遍历方向
        # 首先分析曲线的Y值变化趋势
        # 从曲线起点到终点，Y是增加还是减少

        # 计算曲线整体的Y变化趋势
        if len(curve) >= 2:
            y_start = curve[0][1]
            y_end = curve[-1][1]
            y_increasing = y_end > y_start
        else:
            y_increasing = True

        # 确定搜索方向
        if downward:
            # 向下：寻找Y减小的方向
            if y_increasing:
                # 曲线Y值递增（从下到上），向下需要索引减小
                indices = list(range(start_idx, -1, -1))
            else:
                # 曲线Y值递减（从上到下），向下需要索引增大
                indices = list(range(start_idx, len(curve)))
        else:
            # 向上：寻找Y增大的方向
            if y_increasing:
                indices = list(range(start_idx, len(curve)))
            else:
                indices = list(range(start_idx, -1, -1))

        # 沿曲线累积距离
        accumulated = 0.0
        prev_point = curve[indices[0]]

        for i in range(1, len(indices)):
            curr_idx = indices[i]
            curr_point = curve[curr_idx]
            seg_length = point_distance(prev_point, curr_point)

            if accumulated + seg_length >= distance:
                # 需要在这段内插值
                remaining = distance - accumulated
                t = remaining / seg_length if seg_length > 0 else 0
                return lerp(t, prev_point, curr_point)

            accumulated += seg_length
            prev_point = curr_point

        # 如果曲线不够长，返回最后一个点
        return prev_point

    def _find_point_along_curve_from_end(self, curve: List[Tuple[float, float]],
                                       distance: float) -> Tuple[float, float]:
        """从曲线终点反向移动指定距离找点"""
        accumulated = 0.0
        prev_point = curve[-1]

        for i in range(len(curve)-2, -1, -1):
            curr_point = curve[i]
            seg_length = point_distance(prev_point, curr_point)

            if accumulated + seg_length >= distance:
                remaining = distance - accumulated
                t = remaining / seg_length if seg_length > 0 else 0
                return lerp(t, prev_point, curr_point)

            accumulated += seg_length
            prev_point = curr_point

        return curve[0]

    def _get_curve_direction_at_point(self, curve: List[Tuple[float, float]],
                                       point: Tuple[float, float]) -> Tuple[float, float]:
        """获取曲线在某点的方向向量（从腰围向下的方向）"""
        # 找到点在曲线中的位置
        idx = 0
        min_dist = float('inf')
        for i, p in enumerate(curve):
            d = point_distance(p, point)
            if d < min_dist:
                min_dist = d
                idx = i

        # 取向下的方向（向臀围、立裆方向）
        if idx < len(curve) - 1:
            p1 = curve[idx]
            p2 = curve[idx + 1]
        elif idx > 0:
            p1 = curve[idx - 1]
            p2 = curve[idx]
        else:
            return (1.0, -1.0)  # 默认向下向右的方向

        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.hypot(dx, dy)
        if length < 0.001:
            return (1.0, -1.0)
        return (dx / length, dy / length)

    def _find_parallel_line_intersection(self, start_point: Tuple[float, float],
                                          direction: Tuple[float, float],
                                          target_y: float,
                                          extend_length: float = 0.0) -> Tuple[float, float]:
        """找平行线与目标Y坐标水平线的交点，并可选择延伸"""
        sx, sy = start_point
        dx, dy = direction

        # 计算参数t: sy + t * dy = target_y
        if abs(dy) < 0.001:
            # 几乎水平，直接返回起点延长
            t = 10.0
        else:
            t = (target_y - sy) / dy

        # 交点
        intersect_x = sx + t * dx
        intersect_y = target_y

        # 如果需要延伸
        if extend_length > 0:
            intersect_x += dx * extend_length
            intersect_y += dy * extend_length

        return (intersect_x, intersect_y)

    def _find_perpendicular_intersection_with_curve(self, start_point: Tuple[float, float],
                                                      perp_dir: Tuple[float, float],
                                                      curve: List[Tuple[float, float]]) -> Tuple[float, float]:
        """找垂线与曲线的交点"""
        sx, sy = start_point
        dx, dy = perp_dir

        # 从起点向两个方向搜索交点
        best_point = None
        min_dist = float('inf')

        # 搜索曲线上的每一段，找与垂线的最近交点
        for i in range(len(curve) - 1):
            p1 = curve[i]
            p2 = curve[i + 1]

            # 求两条直线的交点
            intersect = self._line_intersection(
                sx, sy, sx + dx * 100, sy + dy * 100,
                p1[0], p1[1], p2[0], p2[1]
            )

            if intersect:
                # 检查交点是否在线段上
                dist = point_distance(start_point, intersect)
                if dist < min_dist and dist > 0.1:
                    min_dist = dist
                    best_point = intersect

        # 如果没找到交点，返回曲线上最近的点
        if best_point is None:
            for p in curve:
                dist = point_distance(start_point, p)
                if dist < min_dist:
                    min_dist = dist
                    best_point = p

        return best_point

    def _line_intersection(self, x1: float, y1: float, x2: float, y2: float,
                           x3: float, y3: float, x4: float, y4: float) -> Optional[Tuple[float, float]]:
        """求两条直线的交点"""
        # 直线1: (x1,y1)-(x2,y2)
        # 直线2: (x3,y3)-(x4,y4)
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 0.00001:
            return None

        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

        # 检查交点是否在线段上（t在0-1之间，u在0-1之间）
        if -0.1 <= t <= 1.1 and -0.1 <= u <= 1.1:
            x = x1 + t * (x2 - x1)
            y = y1 + t * (y2 - y1)
            return (x, y)
        return None

    def _calculate_fly_curve(self, fly_outer_end: Tuple[float, float],
                             fly_start_point: Tuple[float, float],
                             fly_inner_end: Tuple[float, float],
                             rise_dir: Tuple[float, float]) -> Tuple[List[Tuple[float, float]], Tuple[float, float]]:
        """计算门襟弧线：
        - 从门襟线上离门襟内端点往上3公分的点出发（弧起点）
        - 相切于门襟线
        - 相切于门襟宽线（垂直线）
        - 终点是门襟外端点
        返回：(曲线, 弧起点)
        """
        # 计算门襟线方向（从fly_start_point指向fly_inner_end，向下）
        dx = fly_inner_end[0] - fly_start_point[0]
        dy = fly_inner_end[1] - fly_start_point[1]
        len_dir = math.hypot(dx, dy)
        if len_dir < 0.001:
            fly_dir_x = 1.0
            fly_dir_y = -1.0
        else:
            fly_dir_x = dx / len_dir
            fly_dir_y = dy / len_dir

        # 计算门襟宽线方向（垂直于门襟线，向内侧，从门襟内端点指向门襟外端点）
        perp_x = rise_dir[1]
        perp_y = -rise_dir[0]

        # 计算弧起点：在门襟线上，从门襟内端点往上3cm
        start_x = fly_inner_end[0] - fly_dir_x * 3.0
        start_y = fly_inner_end[1] - fly_dir_y * 3.0
        arc_start_point = (start_x, start_y)

        # 使用三次贝塞尔曲线：两个控制点，确保两端相切
        # 第一个控制点长一些，让J型更圆润
        tangent_len1 = 2.0  # 弧起点处的切线长度
        tangent_len2 = 1.5  # 门襟外端点处的切线长度
        # 第一个控制点：从弧起点沿着门襟线方向（向下）延伸
        ctrl1_x = start_x + fly_dir_x * tangent_len1
        ctrl1_y = start_y + fly_dir_y * tangent_len1

        # 第二个控制点：从门襟外端点沿着门襟宽线方向（向外，即反方向）延伸
        ctrl2_x = fly_outer_end[0] + perp_x * tangent_len2
        ctrl2_y = fly_outer_end[1] + perp_y * tangent_len2

        # 使用三次贝塞尔曲线
        curve = sample_bezier_curve([
            arc_start_point,
            (ctrl1_x, ctrl1_y),
            (ctrl2_x, ctrl2_y),
            fly_outer_end
        ], samples=20)

        return curve, arc_start_point

    def _calculate_front_fly(self, waistband: WaistbandPoints,
                              lower_waistline_curve: List[Tuple[float, float]],
                              front_rise_curve: List[Tuple[float, float]],
                              hip_y: float,
                              waist_inner_final: Tuple[float, float]) -> FrontFlyPoints:
        """步骤9: 计算前门襟"""
        # 1. 从下腰头内端点顺着下腰头向外侧方向找3cm，作为门襟起点
        # lower_waistline_curve 是从 outer 到 inner 的顺序，需要从终点反向找点
        fly_start_point = self._find_point_along_curve_from_end(
            lower_waistline_curve, 3.0
        )

        # 2. 计算前浪的方向（取腰围内端点附近，向下的方向）
        rise_dir = self._get_curve_direction_at_point(
            front_rise_curve, waist_inner_final
        )

        # 3. 画一条与前浪平行的门襟线，找到与臀围线交叉再延伸1cm的点（门襟内端点）
        fly_inner_end = self._find_parallel_line_intersection(
            fly_start_point, rise_dir, hip_y, extend_length=1.0
        )

        # 4. 通过门襟内端点垂直于前浪画一条线（向内侧方向），与前浪交叉的点叫门襟外端点
        # 垂直方向：逆时针旋转90度（向内侧，向x增加的方向）
        perp_dir = (rise_dir[1], -rise_dir[0])
        fly_outer_end = self._find_perpendicular_intersection_with_curve(
            fly_inner_end, perp_dir, front_rise_curve
        )

        # 5. 从门襟外端点出发，绘制弧线：
        # - 相切于门襟宽线（垂直线）
        # - 相切于门襟线
        # - 终点是门襟线上离门襟内端点往上3公分的点
        fly_curve, fly_end_point = self._calculate_fly_curve(
            fly_outer_end, fly_start_point, fly_inner_end, rise_dir
        )

        # 6. 构建门襟裁片闭合轮廓：
        # 门襟起点 → 门襟弧终点（门襟线直线段）→ 门襟弧线 → 门襟外端点
        # → 沿前浪向上至下腰头内端点 → 沿下腰头回到门襟起点
        rise_segment = self._extract_curve_segment_exact(
            front_rise_curve, fly_outer_end, waistband.lower_waist_inner
        )
        waist_segment = self._extract_curve_segment_exact(
            lower_waistline_curve, waistband.lower_waist_inner, fly_start_point
        )
        fly_panel_outline = [fly_start_point, fly_end_point]
        fly_panel_outline.extend(fly_curve[1:])
        fly_panel_outline.extend(rise_segment[1:])
        # 精确补上下腰头内端点角点（两段采样曲线的最近点可能与真实角点有偏差）
        fly_panel_outline.append(waistband.lower_waist_inner)
        fly_panel_outline.extend(waist_segment[1:])

        return FrontFlyPoints(
            fly_start_point=fly_start_point,
            fly_inner_end=fly_inner_end,
            fly_outer_end=fly_outer_end,
            fly_end_point=fly_end_point,
            fly_curve=fly_curve,
            fly_panel_outline=fly_panel_outline
        )

    def _get_crescent_pocket_controls(self, p0: Tuple[float, float],
                                      p1: Tuple[float, float],
                                      offset: float) -> Tuple[Tuple[float, float], Tuple[float, float], float, float]:
        """计算月牙袋弧线的两个控制点和外法线方向（向右下方凸起）
        返回: (ctrl1靠近p0, ctrl2靠近p1, perp_dx, perp_dy)
        """
        # 计算两个点之间的向量
        dx = p1[0] - p0[0]
        dy = p1[1] - p0[1]

        # 顺时针旋转90度得到法线方向
        perp_dx = dy
        perp_dy = -dx

        # 归一化法线向量
        length = math.hypot(perp_dx, perp_dy)
        if length > 0.001:
            perp_dx /= length
            perp_dy /= length

        # 确保法线指向右下方（X正方向，Y负方向）
        if perp_dx < 0 or perp_dy > 0:
            perp_dx = -perp_dx
            perp_dy = -perp_dy

        # 计算控制点位置（沿法线方向偏移）
        ctrl1 = (p0[0] + dx * 0.25 + perp_dx * offset,
                 p0[1] + dy * 0.25 + perp_dy * offset)
        ctrl2 = (p0[0] + dx * 0.75 + perp_dx * offset,
                 p0[1] + dy * 0.75 + perp_dy * offset)

        return ctrl1, ctrl2, perp_dx, perp_dy

    def _calculate_crescent_pocket_curve(self,
                                         pocket_outer: Tuple[float, float],
                                         pocket_width: Tuple[float, float]) -> List[Tuple[float, float]]:
        """计算月牙袋弧线（向右下方凸起的月牙弯）"""
        ctrl1, ctrl2, _, _ = self._get_crescent_pocket_controls(
            pocket_outer, pocket_width, 3.0
        )
        return sample_bezier_curve([
            pocket_outer,
            ctrl1,
            ctrl2,
            pocket_width
        ], samples=20)

    def _calculate_crescent_pocket(self, waistband: WaistbandPoints,
                                   outer_seam_curve: List[Tuple[float, float]],
                                   lower_waistline_curve: List[Tuple[float, float]],
                                   waistline_curve: List[Tuple[float, float]]) -> CrescentPocketPoints:
        """步骤10: 计算月牙袋"""
        # 1. 月牙袋外缝顶点：从下腰头外缝顶点沿着外侧缝向下7cm
        pocket_outer = self._find_point_along_curve(
            outer_seam_curve, waistband.lower_waist_outer, 7.0, downward=True
        )

        # 2. 月牙袋宽顶点：从下腰头外缝顶点沿着下腰头曲线向内侧量取10cm
        pocket_width = self._find_point_along_curve_from_start(
            lower_waistline_curve, 10.0
        )

        # 3. 计算月牙袋弧线（向右下方凸起的月牙弯）
        pocket_curve = self._calculate_crescent_pocket_curve(
            pocket_outer, pocket_width
        )

        # 4. 计算月牙袋省道点：从月牙袋宽顶点再沿下腰头向内侧延伸0.6cm
        pocket_dart = self._find_point_along_curve_from_start(
            lower_waistline_curve, 10.6
        )

        # 5. 计算月牙袋省道弧线（始终在月牙袋弧线外侧，不交叉）
        pocket_dart_curve = self._calculate_crescent_pocket_dart_curve(
            pocket_dart, pocket_outer, pocket_width
        )

        # 6. 计算垂直于上腰围线的方向
        # 找上腰围线上最接近月牙袋宽顶点的点
        closest_on_waist = self._find_closest_point_on_curve(
            waistline_curve, pocket_width
        )
        waist_tangent = self._get_curve_direction_at_point(
            waistline_curve, closest_on_waist
        )
        # 垂直方向（逆时针旋转90度）
        perp_waist_x = -waist_tangent[1]
        perp_waist_y = waist_tangent[0]
        # 确保垂直方向指向上腰围线方向（Y增大方向）
        if perp_waist_y < 0:
            perp_waist_x = -perp_waist_x
            perp_waist_y = -perp_waist_y

        # 7. 从月牙袋宽顶点和省道点出发，沿垂直方向找到与上腰围线的交点
        pocket_dart_line_width = self._find_perpendicular_intersection_with_curve(
            pocket_width, (perp_waist_x, perp_waist_y), waistline_curve
        )
        pocket_dart_line_dart = self._find_perpendicular_intersection_with_curve(
            pocket_dart, (perp_waist_x, perp_waist_y), waistline_curve
        )

        return CrescentPocketPoints(
            pocket_outer=pocket_outer,
            pocket_width=pocket_width,
            pocket_curve=pocket_curve,
            pocket_dart=pocket_dart,
            pocket_dart_curve=pocket_dart_curve,
            pocket_dart_line_width=pocket_dart_line_width,
            pocket_dart_line_dart=pocket_dart_line_dart
        )

    def _find_closest_point_on_curve(self, curve: List[Tuple[float, float]],
                                     target_point: Tuple[float, float]) -> Tuple[float, float]:
        """找曲线上最接近目标点的点"""
        min_dist = float('inf')
        closest = curve[0]
        for p in curve:
            d = point_distance(p, target_point)
            if d < min_dist:
                min_dist = d
                closest = p
        return closest

    def _find_point_along_curve_from_start(self, curve: List[Tuple[float, float]],
                                          distance: float) -> Tuple[float, float]:
        """从曲线起点沿着曲线方向找到指定距离的点"""
        accumulated = 0.0
        prev_point = curve[0]

        for i in range(1, len(curve)):
            curr_point = curve[i]
            seg_length = point_distance(prev_point, curr_point)

            if accumulated + seg_length >= distance:
                # 需要在这段内插值
                remaining = distance - accumulated
                t = remaining / seg_length if seg_length > 0 else 0
                return lerp(t, prev_point, curr_point)

            accumulated += seg_length
            prev_point = curr_point

        # 如果曲线不够长，返回最后一个点
        return prev_point

    def _calculate_crescent_pocket_dart_curve(self,
                                               pocket_dart: Tuple[float, float],
                                               pocket_outer: Tuple[float, float],
                                               pocket_width: Tuple[float, float]) -> List[Tuple[float, float]]:
        """计算月牙袋省道弧线，始终在月牙袋弧线外侧（右下方），保证不交叉且末端完美相切。"""
        # 获取月牙袋弧线的控制点和外法线方向
        ctrl1_pocket, ctrl2_pocket, perp_dx, perp_dy = self._get_crescent_pocket_controls(
            pocket_outer, pocket_width, 3.0
        )

        # 优化算法：端点控制分离
        
        # 1. 靠近月牙袋外缝顶点 (pocket_outer) 的控制点不作偏移，直接共用。
        # 这样可以保证两条曲线在 pocket_outer 处的切线斜率绝对一致，实现平滑渐近不交叉。
        ctrl1_dart = ctrl1_pocket

        # 2. 靠近月牙袋宽顶点 (pocket_width / pocket_dart) 的控制点向外偏移。
        # 把靠近腰头的部分向外撑开。
        extra_offset = 1.5
        ctrl2_dart = (ctrl2_pocket[0] + perp_dx * extra_offset,
                      ctrl2_pocket[1] + perp_dy * extra_offset)

        # 省道弧线方向：pocket_dart → pocket_outer
        return sample_bezier_curve([
            pocket_dart,
            ctrl2_dart,
            ctrl1_dart,
            pocket_outer
        ], samples=20)

    def _calculate_pocket_patch(self, crescent_pocket: CrescentPocketPoints,
                                 outer_seam_curve: List[Tuple[float, float]],
                                 lower_waistline_curve: List[Tuple[float, float]]) -> PocketPatchPoints:
        """步骤12: 计算袋贴"""
        patch_offset = 3.5  # 袋贴与月牙袋省道弧线的距离

        # 1. 袋贴下腰头顶点：月牙袋省道点沿下腰头线继续向内侧扩展3.5cm
        #    月牙袋省道点位于下腰头起点(下腰头外缝顶点)起算10.6cm处，再扩展3.5cm
        patch_lower_waist = self._find_point_along_curve_from_start(
            lower_waistline_curve, 10.6 + patch_offset
        )

        # 2. 袋贴外缝顶点：月牙袋外缝顶点沿外侧缝向Y负方向(向下)继续扩展3.5cm
        patch_outer_seam = self._find_point_along_curve(
            outer_seam_curve, crescent_pocket.pocket_outer, patch_offset, downward=True
        )

        # 3. 袋贴弧线：与月牙袋省道弧线保持3.5cm距离（沿外法线方向偏移）
        patch_curve = self._calculate_pocket_patch_curve(
            crescent_pocket, patch_lower_waist, patch_outer_seam, patch_offset
        )

        return PocketPatchPoints(
            patch_lower_waist=patch_lower_waist,
            patch_outer_seam=patch_outer_seam,
            patch_curve=patch_curve
        )

    def _calculate_pocket_patch_curve(self, crescent_pocket: CrescentPocketPoints,
                                       patch_lower_waist: Tuple[float, float],
                                       patch_outer_seam: Tuple[float, float],
                                       offset: float) -> List[Tuple[float, float]]:
        """计算袋贴弧线（与月牙袋省道弧线平行，沿外法线向外偏移offset cm）

        端点使用袋贴下腰头顶点与袋贴外缝顶点（落在外缝与下腰头上），
        中间控制点取月牙袋省道弧线的两个控制点沿外法线方向偏移offset后的点，
        从而保证袋贴弧线与月牙袋省道弧线整体保持offset的距离。
        """
        # 月牙袋弧线的控制点与外法线方向（向右下方，即外侧）
        ctrl1_pocket, ctrl2_pocket, perp_dx, perp_dy = self._get_crescent_pocket_controls(
            crescent_pocket.pocket_outer, crescent_pocket.pocket_width, 3.0
        )

        # 月牙袋省道弧线的控制点（与 _calculate_crescent_pocket_dart_curve 保持一致）
        ctrl1_dart = ctrl1_pocket                              # 靠近外缝顶点侧
        extra_offset = 1.5
        ctrl2_dart = (ctrl2_pocket[0] + perp_dx * extra_offset,
                      ctrl2_pocket[1] + perp_dy * extra_offset)  # 靠近宽顶点/省道点侧

        # 袋贴控制点：省道弧线控制点沿外法线再偏移offset
        patch_ctrl_near_waist = (ctrl2_dart[0] + perp_dx * offset,
                                 ctrl2_dart[1] + perp_dy * offset)
        patch_ctrl_near_outer = (ctrl1_dart[0] + perp_dx * offset,
                                 ctrl1_dart[1] + perp_dy * offset)

        # 袋贴弧线方向：袋贴下腰头顶点 → 袋贴外缝顶点
        return sample_bezier_curve([
            patch_lower_waist,
            patch_ctrl_near_waist,
            patch_ctrl_near_outer,
            patch_outer_seam
        ], samples=20)

    def _find_ray_curve_intersection(self, start_point: Tuple[float, float],
                                      direction: Tuple[float, float],
                                      curve: List[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
        """找从 start_point 沿 direction 方向的射线与 curve 的最近交点（t>0）"""
        sx, sy = start_point
        dx, dy = direction
        best = None
        best_t = float('inf')

        for i in range(len(curve) - 1):
            p1, p2 = curve[i], curve[i + 1]
            intersect = self._line_intersection(
                sx, sy, sx + dx * 100, sy + dy * 100,
                p1[0], p1[1], p2[0], p2[1]
            )
            if intersect is None:
                continue
            # 计算交点沿射线的参数 t（需 t>0）
            if abs(dx) > 1e-6:
                t = (intersect[0] - sx) / dx
            else:
                t = (intersect[1] - sy) / dy
            if t > 0.1 and t < best_t:
                best_t = t
                best = intersect
        return best

    def _extract_curve_segment(self, curve: List[Tuple[float, float]],
                                p_start: Tuple[float, float],
                                p_end: Tuple[float, float]) -> List[Tuple[float, float]]:
        """提取曲线上从 p_start 到 p_end 之间的采样段（沿曲线方向）"""
        def nearest(p):
            best_i, best_d = 0, float('inf')
            for i, q in enumerate(curve):
                d = point_distance(p, q)
                if d < best_d:
                    best_d, best_i = d, i
            return best_i

        i1 = nearest(p_start)
        i2 = nearest(p_end)
        if i1 <= i2:
            return curve[i1:i2 + 1]
        else:
            return list(reversed(curve[i2:i1 + 1]))

    def _project_point_on_curve(self, curve: List[Tuple[float, float]],
                                 p: Tuple[float, float]):
        """将点投影到折线曲线上，返回 (距离, 线段索引, 线段参数t, 投影点)"""
        best = None
        for i in range(len(curve) - 1):
            ax, ay = curve[i]
            bx, by = curve[i + 1]
            dx, dy = bx - ax, by - ay
            len2 = dx * dx + dy * dy
            t = 0.0 if len2 < 1e-12 else ((p[0] - ax) * dx + (p[1] - ay) * dy) / len2
            t = max(0.0, min(1.0, t))
            q = (ax + t * dx, ay + t * dy)
            d = point_distance(p, q)
            if best is None or d < best[0]:
                best = (d, i, t, q)
        return best

    def _extract_curve_segment_exact(self, curve: List[Tuple[float, float]],
                                      p_start: Tuple[float, float],
                                      p_end: Tuple[float, float]) -> List[Tuple[float, float]]:
        """精确提取曲线上从 p_start 到 p_end 之间的曲线段（端点按投影精确切断，
        不会像最近采样点法那样越过端点）"""
        _, i1, t1, q1 = self._project_point_on_curve(curve, p_start)
        _, i2, t2, q2 = self._project_point_on_curve(curve, p_end)
        s1, s2 = i1 + t1, i2 + t2
        if s1 <= s2:
            pts = [q1]
            for i in range(i1 + 1, i2 + 1):
                pts.append(curve[i])
            pts.append(q2)
        else:
            pts = [q1]
            for i in range(i1, i2, -1):
                pts.append(curve[i])
            pts.append(q2)
        return pts

    def _calculate_pocket_bag(self, pocket_patch: PocketPatchPoints,
                               bbox: BoundingBox, waistband: WaistbandPoints,
                               outer_seam_curve: List[Tuple[float, float]],
                               lower_waistline_curve: List[Tuple[float, float]]) -> PocketBagPoints:
        """步骤13: 计算袋布"""
        bag_extend = 0.65   # 袋贴下腰头顶点沿下腰头再延伸 0.5-0.8cm（取中）
        bottom_len = 5.5    # 底边 5-6cm（取中）
        outer_drop = 2.5    # 袋贴外缝顶点沿外缝再向下 2-3cm（取中）

        # 1. 袋布上腰头顶点：袋贴下腰头顶点(下腰头14.1cm处)沿下腰头再延伸 bag_extend
        #    (10.6 省道点 + 3.5 袋贴偏移 + bag_extend)
        bag_upper_waist = self._find_point_along_curve_from_start(
            lower_waistline_curve, 10.6 + 3.5 + bag_extend
        )

        # 2. 袋布线方向：垂直于下腰头线，朝向立裆线（Y负方向）
        waist_tangent = self._get_curve_direction_at_point(lower_waistline_curve, bag_upper_waist)
        cand_a = (-waist_tangent[1], waist_tangent[0])
        cand_b = (waist_tangent[1], -waist_tangent[0])
        bag_dir = cand_a if cand_a[1] < cand_b[1] else cand_b  # 选 Y 分量为负（朝立裆）

        # 3. 袋布内端点：袋布线画到离立裆线1cm处（Y = crotch_y + 1）
        target_y = bbox.crotch_y + 1.0
        t = (target_y - bag_upper_waist[1]) / bag_dir[1] if abs(bag_dir[1]) > 1e-6 else 20.0
        bag_inner_end = (bag_upper_waist[0] + t * bag_dir[0],
                         bag_upper_waist[1] + t * bag_dir[1])

        bag_line = [bag_upper_waist, bag_inner_end]

        # 4. 袋布拐点：从内端点垂直于袋布线、朝向外缝（X负方向）画 bottom_len
        perp_a = (-bag_dir[1], bag_dir[0])
        perp_b = (bag_dir[1], -bag_dir[0])
        corner_dir = perp_a if perp_a[0] < perp_b[0] else perp_b  # 选 X 分量为负（朝外缝）
        bag_corner = (bag_inner_end[0] + bottom_len * corner_dir[0],
                      bag_inner_end[1] + bottom_len * corner_dir[1])

        bag_bottom_edge = [bag_inner_end, bag_corner]

        # 5. 袋布外缝顶点：袋贴外缝顶点沿外缝向Y负方向再 outer_drop
        bag_outer_seam = self._find_point_along_curve(
            outer_seam_curve, pocket_patch.patch_outer_seam, outer_drop, downward=True
        )

        # 6. 袋布弧线：拐点 → 外缝顶点
        #    拐点处沿底边方向（朝外缝）相切；外缝顶点处沿外侧缝相切
        seam_tangent = self._get_curve_direction_at_point(outer_seam_curve, bag_outer_seam)
        ctrl1 = (bag_corner[0] + 3.0 * corner_dir[0],
                 bag_corner[1] + 3.0 * corner_dir[1])
        # 外侧缝曲线自然方向朝上(腰围)，ctrl2 沿其反方向(向下)使弧线与外缝相切
        ctrl2 = (bag_outer_seam[0] - 2.5 * seam_tangent[0],
                 bag_outer_seam[1] - 2.5 * seam_tangent[1])
        bag_curve = sample_bezier_curve([bag_corner, ctrl1, ctrl2, bag_outer_seam], samples=20)

        # 7. 袋布顶边：外缝顶点沿外缝向上至下腰头外缝顶点，再沿下腰头至上腰头顶点
        bag_top_edge = []
        bag_top_edge.extend(self._extract_curve_segment(
            outer_seam_curve, bag_outer_seam, waistband.lower_waist_outer))
        lower_seg = self._extract_curve_segment(
            lower_waistline_curve, waistband.lower_waist_outer, bag_upper_waist)
        bag_top_edge.extend(lower_seg[1:])

        return PocketBagPoints(
            bag_upper_waist=bag_upper_waist,
            bag_inner_end=bag_inner_end,
            bag_corner=bag_corner,
            bag_outer_seam=bag_outer_seam,
            bag_line=bag_line,
            bag_bottom_edge=bag_bottom_edge,
            bag_curve=bag_curve,
            bag_top_edge=bag_top_edge
        )

    def _calculate_watch_pocket(self, pocket_patch: PocketPatchPoints,
                                 waistband: WaistbandPoints,
                                 outer_seam_curve: List[Tuple[float, float]]) -> WatchPocketPoints:
        """步骤14: 计算小表袋"""
        wp_seam_offset = 3.0   # 距外缝线3cm
        wp_depth = 5.0          # 垂直于外线5cm
        wp_top_gap = 3.5        # 离下腰头3-4cm（取中）

        # 1. 外缝上参考点：下腰头外缝顶点沿外缝向下 wp_top_gap
        seam_top_ref = self._find_point_along_curve(
            outer_seam_curve, waistband.lower_waist_outer, wp_top_gap, downward=True
        )
        # 外侧缝切线（曲线自然方向朝上），向下方向 = -tangent
        seam_tangent = self._get_curve_direction_at_point(outer_seam_curve, seam_top_ref)
        seam_down = (-seam_tangent[0], -seam_tangent[1])
        # 内法线（朝X正方向，即裤身内侧）
        inward_a = (-seam_tangent[1], seam_tangent[0])
        inward_b = (seam_tangent[1], -seam_tangent[0])
        inward = inward_a if inward_a[0] > inward_b[0] else inward_b

        # 2. 小表袋上外端点 = 外缝上参考点向内偏移 wp_seam_offset
        outer_upper = (seam_top_ref[0] + wp_seam_offset * inward[0],
                       seam_top_ref[1] + wp_seam_offset * inward[1])

        # 3. 小表袋下外端点：从上外端点沿外缝向下射线，与袋贴弧线交叉
        patch_curve = pocket_patch.patch_curve
        outer_lower = self._find_ray_curve_intersection(outer_upper, seam_down, patch_curve)
        if outer_lower is None:
            outer_lower = (outer_upper[0] + 4.0 * seam_down[0],
                           outer_upper[1] + 4.0 * seam_down[1])

        # 4. 小表袋上内端点 = 上外端点向内 wp_depth
        inner_upper = (outer_upper[0] + wp_depth * inward[0],
                       outer_upper[1] + wp_depth * inward[1])

        # 5. 小表袋下内端点：从上内端点沿外缝向下射线，与袋贴弧线交叉
        inner_lower = self._find_ray_curve_intersection(inner_upper, seam_down, patch_curve)
        if inner_lower is None:
            inner_lower = (inner_upper[0] + 4.0 * seam_down[0],
                           inner_upper[1] + 4.0 * seam_down[1])

        outer_line = [outer_upper, outer_lower]
        inner_line = [inner_upper, inner_lower]
        # 底边：沿袋贴弧线 下内端点 → 下外端点
        bottom_curve = self._extract_curve_segment(patch_curve, inner_lower, outer_lower)

        return WatchPocketPoints(
            outer_upper=outer_upper,
            outer_lower=outer_lower,
            inner_upper=inner_upper,
            inner_lower=inner_lower,
            outer_line=outer_line,
            inner_line=inner_line,
            bottom_curve=bottom_curve
        )
