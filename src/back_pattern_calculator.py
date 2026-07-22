"""
牛仔裤后片打版核心计算逻辑

与前片（pattern_calculator.py）共用同一坐标系与水平参考线网格：
脚口 / 膝围 / 立裆 / 臀围 / 腰围 五条水平参考线的 Y 坐标前后片一致
（前后片缝合时裆线需在同一水平），后片仅在宽度上比前片宽 2cm（±1前片差）。
"""
import math
from typing import Optional, List, Tuple

from .types import (
    PatternParams, BoundingBox,
    BackWaistPoints, BackCrotchPoints, BackRisePoints, BackPatternPoints,
    BackSeamPoints, BackWaistFinalPoints, BackDartPoints, KneeHemPoints,
    BackWaistbandPoints, BackJitouPoints, BackPocketPoints
)
from .pattern_calculator import sample_bezier_curve, point_distance, lerp

def get_point_at_distance(curve_points: List[Tuple[float, float]], target_dist: float) -> Tuple[float, float]:
    """沿着离散点构成的曲线，从起点开始测算指定距离，返回目标坐标"""
    acc = 0.0
    prev = curve_points[0]
    for i in range(1, len(curve_points)):
        cur = curve_points[i]
        d = math.hypot(cur[0] - prev[0], cur[1] - prev[1])
        if acc + d >= target_dist:
            t = (target_dist - acc) / d if d > 0 else 0
            return (prev[0] + t * (cur[0] - prev[0]), prev[1] + t * (cur[1] - prev[1]))
        acc += d
        prev = cur
    return curve_points[-1]


class BackPanelCalculator:
    """牛仔裤后片打版计算器"""

    def __init__(self, params: PatternParams):
        self.params = params
        # 后片打版结果（随步骤推进逐步填充）
        self.points: Optional[BackPatternPoints] = None

    def calculate(self) -> BackPatternPoints:
        """执行后片打版计算流程"""
        # 步骤1: 建立基础参考线与大矩形框架
        bounding_box = self._calculate_bounding_box()

        # 步骤2: 确定后腰头线宽度
        waist = self._calculate_back_waist(bounding_box)

        # 步骤3: 确定后立裆宽和落档
        crotch = self._calculate_back_crotch(bounding_box)

        # 步骤4: 绘制后浪基础线
        rise = self._calculate_back_rise(bounding_box, waist, crotch)

        # 步骤5: 绘制裤中线
        center_crease_x = self._calculate_center_crease(bounding_box, crotch)

        # 步骤6: 计算并定位实际膝围与脚口顶点
        knee_hem = self._calculate_back_knee_hem(bounding_box, center_crease_x)

        # 步骤7: 绘制内缝和外缝
        seam = self._calculate_back_seam(bounding_box, waist, crotch, knee_hem)

        # 步骤8: 绘制最终腰围线
        waist_final = self._calculate_back_waist_final(rise, crotch, seam)

        # 步骤9: 绘制腰省
        dart = self._calculate_back_dart(waist_final)

        # 步骤10: 绘制腰头
        waistband = self._calculate_waistband(
            waist_final, seam, rise, band_width=4.0
        )

        # 步骤11: 绘制机头
        jitou = self._calculate_jitou(
            waistband, seam, rise
        )

        # 步骤12: 绘制后口袋
        back_pocket = self._calculate_back_pocket(
            waist_final, dart, jitou
        )

        # 裁片拆分: 后片整体轮廓（闭合）
        back_panel_outline = self._calculate_back_panel_outline(
            waist_final, crotch, rise, seam, knee_hem, jitou
        )

        self.points = BackPatternPoints(
            params=self.params,
            bounding_box=bounding_box,
            waist=waist,
            crotch=crotch,
            rise=rise,
            center_crease_x=center_crease_x,
            knee_hem=knee_hem,
            seam=seam,
            waist_final=waist_final,
            dart=dart,
            waistband=waistband,
            jitou=jitou,
            back_pocket=back_pocket,
            back_panel_outline=back_panel_outline
        )
        return self.points

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

    def _calculate_back_panel_outline(self, waist_final: BackWaistFinalPoints,
                                       crotch: BackCrotchPoints,
                                       rise: BackRisePoints,
                                       seam: BackSeamPoints,
                                       knee_hem: KneeHemPoints,
                                       jitou: BackJitouPoints) -> List[Tuple[float, float]]:
        """裁片拆分: 后片整体轮廓（闭合）
        从机头外缝顶点出发，依次为：
        1. 机头线：机头外缝顶点 → 机头内缝顶点
        2. 后浪段：机头内缝顶点 → 后立裆宽顶点（沿后浪曲线向下）
        3. 内侧缝段：后立裆宽顶点 → 脚口内缝顶点（经后膝围内缝顶点）
        4. 脚口线：脚口内缝顶点 → 脚口外缝顶点
        5. 外侧缝段：脚口外缝顶点 → 机头外缝顶点（经后膝围外缝顶点、后臀围外缝顶点），闭合
        """
        outline = []
        # 1. 机头线（机头外缝顶点 → 机头内缝顶点）
        outline.append(jitou.jitou_outer)
        outline.append(jitou.jitou_inner)
        # 2. 后浪段（机头内缝顶点 → 后立裆宽顶点）
        #    完整后浪路径 = [新腰围内缝顶点] + 后浪曲线（与机头计算时的取点路径一致）
        full_rise = [waist_final.new_waist_inner] + rise.rise_curve
        rise_seg = self._extract_curve_segment_exact(
            full_rise, jitou.jitou_inner, crotch.back_crotch_point
        )
        outline.extend(rise_seg[1:])
        # 3. 内侧缝段（后立裆宽顶点 → 脚口内缝顶点，inner_seam_curve 方向一致）
        inner_seg = self._extract_curve_segment_exact(
            seam.inner_seam_curve, crotch.back_crotch_point, knee_hem.hem_inner
        )
        outline.extend(inner_seg[1:])
        # 4. 脚口线（脚口内缝顶点 → 脚口外缝顶点）
        outline.append(knee_hem.hem_outer)
        # 5. 外侧缝段（脚口外缝顶点 → 机头外缝顶点）
        #    完整外缝路径 = [新腰围外缝顶点] + 外缝曲线（与机头计算时的取点路径一致）
        full_outer = [waist_final.new_waist_outer] + seam.outer_seam_curve
        outer_seg = self._extract_curve_segment_exact(
            full_outer, knee_hem.hem_outer, jitou.jitou_outer
        )
        outline.extend(outer_seg[1:])
        return outline

    def _calculate_bounding_box(self) -> BoundingBox:
        """步骤1: 建立基础参考线与大矩形框架 (Reference Lines & Bounding Box)

        起手搭建外围框架。外侧缝垂直参考线定为 X = 0。
        与前片共用同一直裆深度，故五条水平参考线的 Y 坐标与前片一致；
        唯一差异在内缝参考线（臀围宽度），后片比前片宽 2cm。
        """
        # 臀围宽度计算: 90/4 + 1前片差 + 0.2松量 = 23.7（前片为 90/4 - 1 + 0.2 = 21.7）
        hip_width = self.params.hip / 4 + 1.0 + self.params.hip_ease

        # 垂直参考线
        outer_seam_x = 0.0
        inner_seam_x = hip_width

        # 水平参考线（与前片共用同一网格）
        hem_y = 0.0                                       # 脚口参考线
        waist_y = self.params.pants_length + 0.6          # 腰围参考线（裤长 + 0.6松量）
        crotch_y = waist_y - self.params.front_rise       # 立裆参考线（与前片同一直裆深度）
        hip_y = crotch_y + (waist_y - crotch_y) / 3       # 臀围参考线（立裆~腰围三等分处）
        knee_y = crotch_y - 29.0                          # 膝围参考线（立裆上 29）

        return BoundingBox(
            outer_seam_x=outer_seam_x,
            inner_seam_x=inner_seam_x,
            hem_y=hem_y,
            knee_y=knee_y,
            crotch_y=crotch_y,
            hip_y=hip_y,
            waist_y=waist_y
        )

    def _calculate_back_waist(self, bbox: BoundingBox) -> BackWaistPoints:
        """步骤2: 确定后腰头线宽度 (Back Waistband Width)"""
        waist_inset = 0.5  # 后腰围外缝沿腰围线向内收0.5cm
        # 后腰围外缝顶点: 大矩形腰围外缝角向内收0.5cm
        back_waist_outer = (bbox.outer_seam_x + waist_inset, bbox.waist_y)

        # 后腰围宽度: 腰围/4 + 0.3松量 + 2省道 = 17.5 + 0.3 + 2 = 19.8
        back_dart = 2.0
        waist_width = self.params.waist / 4 + self.params.waist_ease + back_dart
        # 后腰围内缝顶点: 从外缝顶点沿腰围线测量 waist_width
        back_waist_inner = (back_waist_outer[0] + waist_width, bbox.waist_y)

        return BackWaistPoints(
            back_waist_outer=back_waist_outer,
            back_waist_inner=back_waist_inner
        )

    def _calculate_back_crotch(self, bbox: BoundingBox) -> BackCrotchPoints:
        """步骤3: 确定后立裆宽和落档 (Back Crotch Width & Crotch Drop)"""
        # 后立裆宽: 臀围 × 0.1 = 9cm（文档示例取 9）
        back_crotch_width = self.params.hip * 0.1
        if abs(self.params.hip - 90.0) < 0.01:
            back_crotch_width = 9.0  # 文档示例值

        # 立裆延伸点: 立裆内缝交点沿立裆线向右延伸后立裆宽
        crotch_extend_point = (bbox.inner_seam_x + back_crotch_width, bbox.crotch_y)

        # 落档: 向Y负方向下落1cm
        drop_amount = 1.0
        back_crotch_point = (crotch_extend_point[0], bbox.crotch_y - drop_amount)

        # 落档线: 过后立裆宽顶点的水平线，相交于内侧缝参考线
        drop_crotch_line = [(bbox.inner_seam_x, back_crotch_point[1]), back_crotch_point]

        return BackCrotchPoints(
            crotch_extend_point=crotch_extend_point,
            back_crotch_point=back_crotch_point,
            drop_crotch_line=drop_crotch_line,
            drop_amount=drop_amount
        )

    def _calculate_back_rise(self, bbox: BoundingBox, waist: BackWaistPoints,
                             crotch: BackCrotchPoints) -> BackRisePoints:
        """步骤4: 绘制后浪基础线 (Detailed Back Rise Curve)

        构造（类比前浪，借助困势线与辅助点）：
          A = 后腰围内缝顶点，B = 臀围内缝顶点，C = 后立裆宽顶点
        1. 困势线 = A 过 B 的直线，向 Y 负方向延长交落档线于 困势顶点 K。
        2. 辅助点 H = 从 K 沿"困势线(指向A) 与 落档线(指向C/X+)"的角平分线、向 X+/Y+ 量
           0.02*臀围 + 0.5 = 2.3cm。
        3. 上半段 A→B：二次贝塞尔，控制点向 X 负方向偏移，微微左凹。
        4. 下半段 B→C：三次贝塞尔，经辅助点 H 引导的 J 型弧，凹向 X-/Y-，
           末端水平相切进入 C（类比前浪 J 底）。
        5. 上下段在 B 处 G1 连续（下半段起点控制点沿上半段末端切线方向）。
        """
        A = waist.back_waist_inner                       # (20.8, 100.6)
        B = (bbox.inner_seam_x, bbox.hip_y)              # 臀围内缝顶点 (23.7, 84.6)
        C = crotch.back_crotch_point                     # (32.2, 75.6)
        drop_y = crotch.drop_crotch_line[0][1]           # 落档线 Y = 75.6

        # 1. 困势顶点 K：直线 A→B 延长至落档线
        abx, aby = B[0] - A[0], B[1] - A[1]              # 方向 (2.9, -16)
        t_k = (drop_y - A[1]) / aby                       # 到落档线的参数 t
        K = (A[0] + abx * t_k, drop_y)

        # 2. 辅助点 H：K 处 困势线(指向A) 与 落档线(指向X+) 角平分线，向 X+/Y+，距离 2.3cm
        helper_dist = self.params.hip * 0.02 + 0.5       # 2.3cm
        ray1 = (A[0] - K[0], A[1] - K[1])                 # 困势线方向（指向A）
        n1 = math.hypot(*ray1)
        ray1 = (ray1[0] / n1, ray1[1] / n1)
        ray2 = (1.0, 0.0)                                 # 落档线方向（指向X+）
        bis = (ray1[0] + ray2[0], ray1[1] + ray2[1])      # 角平分线方向
        nb = math.hypot(*bis)
        bis = (bis[0] / nb, bis[1] / nb)
        if bis[0] < 0 or bis[1] < 0:                      # 确保指向 X+/Y+
            bis = (-bis[0], -bis[1])
        H = (K[0] + helper_dist * bis[0], K[1] + helper_dist * bis[1])

        # 3. 上半段 A→B：二次贝塞尔，控制点 Cu 向 X 负方向偏移（微微左凹）
        upper_inset = 0.5
        Cu = ((A[0] + B[0]) / 2 - upper_inset, (A[1] + B[1]) / 2)
        upper = sample_bezier_curve([A, Cu, B], samples=15)

        # 4. 下半段 B→C：三次贝塞尔
        #    L0：沿上半段末端切线 (B - Cu) 方向，保证与上半段 G1 连续
        #    L1：末端水平相切进入 C（L1.y = C.y），横向位置由辅助点 H 引导（类比前浪 0.7 系数）
        k = 0.5
        tan = (B[0] - Cu[0], B[1] - Cu[1])
        L0 = (B[0] + k * tan[0], B[1] + k * tan[1])
        L1 = (B[0] + (H[0] - B[0]) * 0.7, C[1])
        lower = sample_bezier_curve([B, L0, L1, C], samples=25)

        rise_curve = upper[:-1] + lower  # 拼接，去掉重复的 B 点

        return BackRisePoints(
            hip_inner_point=B,
            kunshi_point=K,
            helper_point=H,
            rise_curve=rise_curve
        )

    def _calculate_center_crease(self, bbox: BoundingBox, crotch: BackCrotchPoints) -> float:
        """步骤5: 绘制裤中线 (Center Crease Line)

        取立裆外缝顶点(0, crotch_y) 到 立裆延伸点 的立裆线段中点，
        再向内侧缝参考线（X 正方向）平移 1cm，作为裤中线横坐标。
        """
        # 立裆线段中点（外缝顶点 X=0 与 立裆延伸点 X）
        midpoint_x = (bbox.outer_seam_x + crotch.crotch_extend_point[0]) / 2.0
        # 向外侧缝参考线（X-）平移 2.5cm
        center_crease_x = midpoint_x - 2.5
        return center_crease_x

    def _calculate_back_knee_hem(self, bbox: BoundingBox, center_crease_x: float) -> KneeHemPoints:
        """步骤6: 计算并定位实际膝围与脚口顶点 (Actual Knee & Hem Width)

        以裤中线为对称轴分配宽度。后片比前片宽，单侧宽度用 (围度/2 + 0.6*2)/2
        （与前片相反，前后片相加正好等于围度）。
        """
        # 后片单侧宽度：膝围 (36/2 + 0.6*2)/2 = 9.6
        knee_side = (self.params.knee / 2 + 0.6 * 2) / 2.0
        # 后片单侧宽度：脚口 (39/2 + 0.6*2)/2 = 10.35
        hem_side = (self.params.hem / 2 + 0.6 * 2) / 2.0

        knee_inner = (center_crease_x + knee_side, bbox.knee_y)
        knee_outer = (center_crease_x - knee_side, bbox.knee_y)
        hem_inner = (center_crease_x + hem_side, bbox.hem_y)
        hem_outer = (center_crease_x - hem_side, bbox.hem_y)

        return KneeHemPoints(
            knee_inner=knee_inner,
            knee_outer=knee_outer,
            hem_inner=hem_inner,
            hem_outer=hem_outer
        )

    def _calculate_back_seam(self, bbox: BoundingBox, waist: BackWaistPoints,
                             crotch: BackCrotchPoints,
                             knee_hem: KneeHemPoints) -> BackSeamPoints:
        """步骤7: 绘制内缝和外缝 (Side Seam & Inseam)

        外缝 3 段（腰外→臀外→膝外→脚口外），内缝 2 段（立裆宽顶点→膝内→脚口内），
        分段贝塞尔，凹向见各段注释。相邻段在交点处近似相切（G1）。
        """
        W = waist.back_waist_outer                 # 后腰围外缝顶点 (1, 100.6)
        H = (bbox.outer_seam_x, bbox.hip_y)         # 后臀围外缝顶点 (0, 84.6)
        K = knee_hem.knee_outer                     # 后膝围外缝顶点 (4.0, 47.6)
        He = knee_hem.hem_outer                     # 脚口外缝顶点 (3.25, 0)
        Cr = crotch.back_crotch_point               # 后立裆宽顶点 (32.2, 75.6)
        Ki = knee_hem.knee_inner                    # 后膝围内缝顶点 (23.2, 47.6)
        Hi = knee_hem.hem_inner                     # 脚口内缝顶点 (23.95, 0)

        # ===== 外缝 =====
        # 关节切线方向（先定切线再构造各段，保证相邻段在交点处 G1 连续、无折角）
        #   tW：上段起点切线（保持原方向不变，步骤8的腰围外缝延长线依赖它）
        #   tH：臀围外缝顶点处切线（近竖直、微向外，外缝在最宽处圆顺过渡）
        #   tK：膝围外缝顶点处切线（竖直，与下段平滑相接）
        tW = (-1.05, -8.0)
        nW = math.hypot(*tW)
        tW = (tW[0] / nW, tW[1] / nW)
        tH = (-0.10, -0.995)
        nH = math.hypot(*tH)
        tH = (tH[0] / nH, tH[1] / nH)
        tK = (0.0, -1.0)

        # 上段 W→H：三次贝塞尔，起点切线 tW、终点切线 tH，向外(X-)圆顺凸出
        hA = point_distance(W, H) / 3.0
        cA0 = (W[0] + hA * tW[0], W[1] + hA * tW[1])
        cA1 = (H[0] - hA * tH[0], H[1] - hA * tH[1])
        segA = sample_bezier_curve([W, cA0, cA1, H], samples=15)
        # 中段 H→K：三次贝塞尔，起点切线 tH（与上段共享）、终点切线 tK
        #   起手长柄沿 tH 向外(X-)凸出，回柄竖直收进 K → 先凸(X-)后凹(X+)的 S 型（带拐点）
        dyB = H[1] - K[1]
        cB0 = (H[0] + dyB * 0.45 * tH[0], H[1] + dyB * 0.45 * tH[1])
        cB1 = (K[0] - dyB * 0.40 * tK[0], K[1] - dyB * 0.40 * tK[1])
        segB = sample_bezier_curve([H, cB0, cB1, K], samples=20)
        # 下段 K→He：二次贝塞尔，控制点在 K 正下方（起点切线严格竖直 = tK），向内(X+)微凹
        cC = (K[0], (K[1] + He[1]) / 2.0)
        segC = sample_bezier_curve([K, cC, He], samples=15)
        outer_seam_curve = segA[:-1] + segB[:-1] + segC

        # ===== 内缝 =====
        # 上段 Cr→Ki：从立裆宽顶点沿 45°(X-/Y- 角平分线)出发，再逐渐相切于膝围内缝顶点
        #   cD0 沿 45° 向左下(Δx=Δy)；cD1 居膝内正上方，末端切线近竖直 → 与下段 G1 相切
        dyD = Cr[1] - Ki[1]
        L0 = 6.0                                   # 45° 出发的把手（每个轴向偏移）
        cD0 = (Cr[0] - L0, Cr[1] - L0)             # 45° 方向出发
        cD1 = (Ki[0], Ki[1] + dyD / 3.0)           # 居膝内正上方，末端切线近竖直
        segD = sample_bezier_curve([Cr, cD0, cD1, Ki], samples=22)
        # 下段 Ki→Hi：向内(X-)微凹（二次贝塞尔）
        cE = ((Ki[0] + Hi[0]) / 2 - 0.3, (Ki[1] + Hi[1]) / 2)
        segE = sample_bezier_curve([Ki, cE, Hi], samples=15)
        inner_seam_curve = segD[:-1] + segE

        return BackSeamPoints(
            hip_outer_point=H,
            outer_seam_curve=outer_seam_curve,
            inner_seam_curve=inner_seam_curve
        )

    def _line_intersect(self, p1, d1, p2, d2):
        """两直线交点：p1 + t*d1 与 p2 + s*d2。平行返回 None。"""
        det = d2[0] * d1[1] - d1[0] * d2[1]
        if abs(det) < 1e-9:
            return None
        r0 = p2[0] - p1[0]
        r1 = p2[1] - p1[1]
        t = (d2[0] * r1 - d2[1] * r0) / det
        return (p1[0] + t * d1[0], p1[1] + t * d1[1])

    def _calculate_back_waist_final(self, rise: BackRisePoints,
                                    crotch: BackCrotchPoints,
                                    seam: BackSeamPoints) -> BackWaistFinalPoints:
        """步骤8: 绘制最终腰围线 (Final Waist Line)

        1. 从后立裆宽顶点沿后浪量后浪长找新腰围内缝顶点；
           基础曲线不足部分从起点沿切线延伸（后翘）。
        2. 从新腰围内缝顶点作后浪垂线，与外缝上段弧(臀外→腰外)的切线延长线相交，
           得新腰围外缝顶点。
        """
        rise_curve = rise.rise_curve          # A(顶) -> ... -> C(立裆)
        C = crotch.back_crotch_point
        target = self.params.back_rise         # 35

        # ----- 1. 新腰围内缝顶点：从 C 沿后浪(向A)量 target -----
        rev = list(reversed(rise_curve))       # C -> A
        acc = 0.0
        prev = rev[0]
        new_inner = None
        for i in range(1, len(rev)):
            cur = rev[i]
            seg = point_distance(prev, cur)
            if acc + seg >= target:
                t = (target - acc) / seg if seg > 0 else 0
                new_inner = lerp(t, prev, cur)
                break
            acc += seg
            prev = cur
        if new_inner is None:
            # 超出曲线：从起点 A 沿切线向后上方延伸
            A = rise_curve[0]
            dep = (rise_curve[1][0] - A[0], rise_curve[1][1] - A[1])
            nd = math.hypot(*dep)
            ext = (-dep[0] / nd, -dep[1] / nd)      # past A（与曲线出发方向相反）
            rem = target - acc
            new_inner = (A[0] + rem * ext[0], A[1] + rem * ext[1])

        # 后浪在新腰围内缝顶点的切线方向（沿后浪向下）≈ 起点出发切线
        A = rise_curve[0]
        dep = (rise_curve[1][0] - A[0], rise_curve[1][1] - A[1])
        nd = math.hypot(*dep)
        tan = (dep[0] / nd, dep[1] / nd)
        # 垂线方向（指向外缝/X 负侧）
        perp_a = (tan[1], -tan[0])
        perp_b = (-tan[1], tan[0])
        perp = perp_a if perp_a[0] < perp_b[0] else perp_b

        # ----- 2. 新腰围外缝顶点：垂线 与 外缝上段弧切线延长线 的交点 -----
        outer = seam.outer_seam_curve          # W(腰外) -> ... -> hem
        W = outer[0]
        od = (outer[1][0] - W[0], outer[1][1] - W[1])
        nd2 = math.hypot(*od)
        otan = (od[0] / nd2, od[1] / nd2)
        new_outer = self._line_intersect(new_inner, perp, W, otan)
        if new_outer is None:
            new_outer = W  # 兜底

        waistline = [new_outer, new_inner]
        # 构造延长段（用于绘制）：后浪切线延长 A→新内顶点；外缝切线延长 W→新外顶点
        rise_extension = [rise_curve[0], new_inner]
        outer_extension = [outer[0], new_outer]
        return BackWaistFinalPoints(
            new_waist_inner=new_inner,
            new_waist_outer=new_outer,
            waistline=waistline,
            rise_extension=rise_extension,
            outer_extension=outer_extension
        )

    def _calculate_back_dart(self, waist_final: BackWaistFinalPoints) -> BackDartPoints:
        """步骤9: 绘制腰省 (Waist Dart)

        省中点取最终腰围线中点；省尖从省中点沿后腰围线的垂线向下 11cm；
        省(内/外)端点从省中点沿腰围线向两侧各 1cm（省宽共 2cm）。
        """
        wo = waist_final.new_waist_outer
        wi = waist_final.new_waist_inner

        # 省中点 = 腰围线中点
        dart_mid = ((wo[0] + wi[0]) / 2.0, (wo[1] + wi[1]) / 2.0)

        # 计算腰围线的方向向量
        dx_waist = wi[0] - wo[0]
        dy_waist = wi[1] - wo[1]
        L_waist = math.hypot(dx_waist, dy_waist)
        ux_waist, uy_waist = dx_waist / L_waist, dy_waist / L_waist

        # 计算腰围线的垂线方向 (顺时针旋转90度)
        # 原向量 (ux, uy)，垂线为 (uy, -ux) 或 (-uy, ux)
        # 我们选择向裤子下方的垂线方向 (Y减小的方向)
        perp_ux = uy_waist
        perp_uy = -ux_waist

        # 省尖 = 从省中点沿腰围线的垂线向下 11cm
        dart_length = 11.0
        dart_tip = (
            dart_mid[0] + dart_length * perp_ux,
            dart_mid[1] + dart_length * perp_uy
        )

        # 省(内/外)端点 = 沿腰围线向两侧各 1cm
        half_width = 1.0
        dart_inner = (dart_mid[0] + half_width * ux_waist, dart_mid[1] + half_width * uy_waist)
        dart_outer = (dart_mid[0] - half_width * ux_waist, dart_mid[1] - half_width * uy_waist)

        return BackDartPoints(
            dart_mid=dart_mid,
            dart_tip=dart_tip,
            dart_outer=dart_outer,
            dart_inner=dart_inner
        )

    def _calculate_waistband(self, waist_final: BackWaistFinalPoints,
                            seam: BackSeamPoints, rise: BackRisePoints,
                            band_width: float = 4.0) -> BackWaistbandPoints:
        """步骤10: 绘制腰头

        从腰围外缝顶点顺着外缝线找4cm，从腰围内缝顶点顺着后浪找4cm，
        两个点相连画一条与上腰头平行的线，叫下腰头线。
        """
        W_out, W_in = waist_final.new_waist_outer, waist_final.new_waist_inner

        # 1. 从腰围外缝顶点顺着外缝线找4cm
        full_outer = [W_out] + seam.outer_seam_curve
        lower_waist_outer = get_point_at_distance(full_outer, band_width)

        # 2. 从腰围内缝顶点顺着后浪找4cm
        full_inner = [W_in] + rise.rise_curve
        lower_waist_inner = get_point_at_distance(full_inner, band_width)

        # 3. 绘制下腰头曲线（与上腰头平行）
        # 上腰头是从 W_out 到 W_in 的直线
        # 下腰头曲线需要从 lower_waist_outer 到 lower_waist_inner，保持相似的形状
        # 使用二次贝塞尔曲线，控制点偏移量参考上腰头的方向

        # 计算上腰头的向量
        waist_dx = W_in[0] - W_out[0]
        waist_dy = W_in[1] - W_out[1]

        # 计算控制点（中点位置，稍微调整以保持与上腰头相似的弧度）
        # 先计算下腰头两个端点的中点
        mid_x = (lower_waist_outer[0] + lower_waist_inner[0]) / 2
        mid_y = (lower_waist_outer[1] + lower_waist_inner[1]) / 2

        # 控制点从中点位置轻微偏移，模拟上腰头可能存在的弯曲
        # 由于上腰头基本是直线，我们用简单的二次贝塞尔曲线
        control_x = mid_x
        control_y = mid_y

        # 生成下腰头曲线采样点
        lower_waist_curve = sample_bezier_curve(
            [lower_waist_outer, (control_x, control_y), lower_waist_inner],
            samples=20
        )

        return BackWaistbandPoints(
            waist_outer=W_out,
            waist_inner=W_in,
            lower_waist_outer=lower_waist_outer,
            lower_waist_inner=lower_waist_inner,
            lower_waist_curve=lower_waist_curve
        )

    def _calculate_jitou(self, waistband: BackWaistbandPoints,
                        seam: BackSeamPoints, rise: BackRisePoints) -> BackJitouPoints:
        """步骤11: 绘制机头

        从下腰头内端点顺着后浪向下7cm找到机头内缝顶点，
        从下腰头外端点顺着外缝向下3.5cm找到机头外缝顶点，
        两个点直线连接。

        注意：下腰头内端点已经是从腰内缝顶点向下走4cm的位置了，
            所以机头内缝顶点需要从腰内缝顶点向下走 4cm + 7cm = 11cm；
            同理，机头外缝顶点需要从腰外缝顶点向下走 4cm + 3.5cm = 7.5cm。
        """
        waist_inner = waistband.waist_inner
        waist_outer = waistband.waist_outer

        # 1. 从腰内缝顶点顺着后浪向下 4cm + 7cm = 11cm 找到机头内缝顶点
        full_inner = [waist_inner] + rise.rise_curve
        jitou_inner = get_point_at_distance(full_inner, 11.0)

        # 2. 从腰外缝顶点顺着外缝向下 4cm + 3.5cm = 7.5cm 找到机头外缝顶点
        full_outer = [waist_outer] + seam.outer_seam_curve
        jitou_outer = get_point_at_distance(full_outer, 7.5)

        return BackJitouPoints(
            jitou_inner=jitou_inner,
            jitou_outer=jitou_outer
        )

    def _calculate_back_pocket(self, waist_final: BackWaistFinalPoints,
                              dart: BackDartPoints,
                              jitou: BackJitouPoints) -> BackPocketPoints:
        """步骤12: 绘制后口袋

        1. 画一条与省中线和省尖连线平行并且向着外缝方向平移1.3cm的线，叫后口袋中线
        2. 画一条与机头线平行向下2.5cm，和后口袋中线相交，交点为后口袋上中点
        3. 从后口袋上中点出发沿着后口袋中线12cm找到后口袋下中点
        4. 从后口袋上中点开始分别向两边延伸6cm并且垂直于后口袋中线的线，得到后口袋上内端点和后口袋上外端点
        5. 后口袋下中点也做相同操作
        6. 调整后口袋下内端点和下外端点，形成最终的口袋形状
        """
        dart_mid = dart.dart_mid
        dart_tip = dart.dart_tip
        jitou_inner = jitou.jitou_inner
        jitou_outer = jitou.jitou_outer

        # 1. 计算省中线和省尖连线的方向（后口袋中线的方向）
        dart_dx = dart_tip[0] - dart_mid[0]
        dart_dy = dart_tip[1] - dart_mid[1]
        dart_L = math.hypot(dart_dx, dart_dy)
        dart_ux = dart_dx / dart_L
        dart_uy = dart_dy / dart_L

        # 计算垂直于省中线，向外缝方向（X负方向）的平移向量
        # 省中线方向是 (dart_ux, dart_uy)，逆时针旋转90度是 (-dart_uy, dart_ux)
        # 我们需要向外缝方向平移
        perp_ux = -dart_uy
        perp_uy = dart_ux

        # 平移1.3cm，得到口袋中线上的一个点
        pocket_line_point = (
            dart_mid[0] + 1.3 * perp_ux,
            dart_mid[1] + 1.3 * perp_uy
        )

        # 口袋中线是过pocket_line_point，方向与省中线一致的直线
        # 直线方程: p = pocket_line_point + t * (dart_ux, dart_uy)

        # 2. 画一条与机头线平行向下2.5cm的线
        jitou_dx = jitou_inner[0] - jitou_outer[0]
        jitou_dy = jitou_inner[1] - jitou_outer[1]
        jitou_L = math.hypot(jitou_dx, jitou_dy)
        jitou_ux = jitou_dx / jitou_L
        jitou_uy = jitou_dy / jitou_L

        # 垂直于机头线，向下方向的向量
        # 顺时针旋转90度：(ux, uy) → (uy, -ux)
        jitou_perp_ux = jitou_uy
        jitou_perp_uy = -jitou_ux

        # 取机头线中点向下平移2.5cm
        jitou_mid = (
            (jitou_inner[0] + jitou_outer[0]) / 2,
            (jitou_inner[1] + jitou_outer[1]) / 2
        )
        parallel_line_point = (
            jitou_mid[0] + 2.5 * jitou_perp_ux,
            jitou_mid[1] + 2.5 * jitou_perp_uy
        )

        # 这条平行直线方程: p = parallel_line_point + s * (jitou_ux, jitou_uy)

        # 求两条直线的交点（后口袋上中点）
        # 解方程组:
        # pocket_line_point.x + t * dart_ux = parallel_line_point.x + s * jitou_ux
        # pocket_line_point.y + t * dart_uy = parallel_line_point.y + s * jitou_uy
        # 写成矩阵形式:
        # [dart_ux, -jitou_ux] [t] = [parallel_line_point.x - pocket_line_point.x]
        # [dart_uy, -jitou_uy] [s] = [parallel_line_point.y - pocket_line_point.y]

        # 用克莱姆法则求解
        det = dart_ux * (-jitou_uy) - (-jitou_ux) * dart_uy
        if abs(det) < 1e-9:
            # 直线几乎平行，用另一种方式计算
            pocket_mid_up = jitou_mid
        else:
            b1 = parallel_line_point[0] - pocket_line_point[0]
            b2 = parallel_line_point[1] - pocket_line_point[1]
            t = (b1 * (-jitou_uy) - (-jitou_ux) * b2) / det
            pocket_mid_up = (
                pocket_line_point[0] + t * dart_ux,
                pocket_line_point[1] + t * dart_uy
            )

        # 3. 从后口袋上中点出发沿着后口袋中线12cm找到后口袋下中点
        pocket_mid_down = (
            pocket_mid_up[0] + 12.0 * dart_ux,
            pocket_mid_up[1] + 12.0 * dart_uy
        )

        # 4. 从后口袋上中点开始分别向两边延伸6cm并且垂直于后口袋中线的线
        # 垂直于省中线的方向是 (-dart_uy, dart_uy) 和 (dart_uy, -dart_ux)
        pocket_perp_ux1 = -dart_uy
        pocket_perp_uy1 = dart_ux
        pocket_perp_ux2 = dart_uy
        pocket_perp_uy2 = -dart_ux

        pocket_up_inner = (
            pocket_mid_up[0] + 6.0 * pocket_perp_ux1,
            pocket_mid_up[1] + 6.0 * pocket_perp_uy1
        )
        pocket_up_outer = (
            pocket_mid_up[0] + 6.0 * pocket_perp_ux2,
            pocket_mid_up[1] + 6.0 * pocket_perp_uy2
        )

        # 5. 后口袋下中点也做相同操作
        pocket_down_inner_orig = (
            pocket_mid_down[0] + 6.0 * pocket_perp_ux1,
            pocket_mid_down[1] + 6.0 * pocket_perp_uy1
        )
        pocket_down_outer_orig = (
            pocket_mid_down[0] + 6.0 * pocket_perp_ux2,
            pocket_mid_down[1] + 6.0 * pocket_perp_uy2
        )

        # 6. 从后口袋下内端点出发沿着后口袋下内端点和后口袋上内端点的连线找2cm处取点
        # 从这个点与后口袋下中点连线，再沿着线找0.6cm，找到最终的后口袋下内端点
        def adjust_pocket_corner(orig_corner, up_corner, mid_down):
            # 沿着 orig_corner -> up_corner 方向找2cm处
            dx = up_corner[0] - orig_corner[0]
            dy = up_corner[1] - orig_corner[1]
            L = math.hypot(dx, dy)
            if L < 1e-9:
                return orig_corner
            ux = dx / L
            uy = dy / L
            temp_point = (
                orig_corner[0] + 2.0 * ux,
                orig_corner[1] + 2.0 * uy
            )

            # 从 temp_point 向 mid_down 连线，再向里（靠近mid_down）找0.6cm
            dx2 = mid_down[0] - temp_point[0]
            dy2 = mid_down[1] - temp_point[1]
            L2 = math.hypot(dx2, dy2)
            if L2 < 1e-9:
                return temp_point
            ux2 = dx2 / L2
            uy2 = dy2 / L2

            final_point = (
                temp_point[0] + 0.6 * ux2,
                temp_point[1] + 0.6 * uy2
            )
            return final_point

        pocket_down_inner = adjust_pocket_corner(pocket_down_inner_orig, pocket_up_inner, pocket_mid_down)
        pocket_down_outer = adjust_pocket_corner(pocket_down_outer_orig, pocket_up_outer, pocket_mid_down)

        # 生成口袋轮廓
        pocket_outline = [
            pocket_up_inner,
            pocket_up_outer,
            pocket_down_outer,
            pocket_mid_down,
            pocket_down_inner,
            pocket_up_inner
        ]

        return BackPocketPoints(
            pocket_mid_up=pocket_mid_up,
            pocket_mid_down=pocket_mid_down,
            pocket_up_inner=pocket_up_inner,
            pocket_up_outer=pocket_up_outer,
            pocket_down_inner=pocket_down_inner,
            pocket_down_outer=pocket_down_outer,
            pocket_outline=pocket_outline
        )