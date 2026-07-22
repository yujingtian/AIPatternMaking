"""
数据类型定义
"""
from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class PatternParams:
    """打版输入参数"""
    waist: float = 70.0      # 腰围 (cm)
    hip: float = 90.0        # 臀围 (cm)
    knee: float = 36.0       # 膝围 (cm)
    hem: float = 39.0        # 裤口 (cm)
    front_rise: float = 24.0 # 前浪 (cm)
    back_rise: float = 35.0  # 后浪 (cm)
    pants_length: float = 100.0 # 裤长 (cm)

    # 可选微调参数
    waist_ease: float = 0.3  # 腰围松量
    hip_ease: float = 0.2    # 臀围松量
    dart_width: float = 0.6  # 省道宽
    front_rise_curve: float = 1.5  # 前浪曲线凹陷程度，越大越凹


@dataclass
class BoundingBox:
    """大矩形框架"""
    # 垂直参考线
    outer_seam_x: float = 0.0       # 外侧缝参考线 X=0
    inner_seam_x: float = 0.0       # 内侧缝参考线

    # 水平参考线 Y坐标
    hem_y: float = 0.0              # 脚口参考线
    knee_y: float = 0.0             # 膝围参考线
    crotch_y: float = 0.0           # 立裆参考线
    hip_y: float = 0.0              # 臀围参考线
    waist_y: float = 0.0            # 腰围参考线

    # 大矩形四个角
    def get_corners(self) -> List[Tuple[float, float]]:
        return [
            (self.outer_seam_x, self.hem_y),
            (self.inner_seam_x, self.hem_y),
            (self.inner_seam_x, self.waist_y),
            (self.outer_seam_x, self.waist_y),
        ]


@dataclass
class FrontRisePoints:
    """前浪曲线关键点"""
    hip_inner_point: Tuple[float, float]  # 臀围内缝顶点
    crotch_extension_point: Tuple[float, float]  # 立裆宽顶点
    rise_helper_point: Tuple[float, float]  # 前浪辅助点
    new_waist_inner_ref: Tuple[float, float]  # 新腰围内缝参考顶点


@dataclass
class KneeHemPoints:
    """膝围与脚口点"""
    knee_inner: Tuple[float, float]   # 膝围内缝顶点
    knee_outer: Tuple[float, float]   # 膝围外缝顶点
    hem_inner: Tuple[float, float]    # 脚口内缝顶点
    hem_outer: Tuple[float, float]    # 脚口外缝顶点


@dataclass
class BackWaistPoints:
    """后片腰围关键点（步骤2）"""
    back_waist_outer: Tuple[float, float]   # 后腰围外缝顶点（向内收1cm）
    back_waist_inner: Tuple[float, float]   # 后腰围内缝顶点


@dataclass
class BackCrotchPoints:
    """后片立裆/落档关键点（步骤3）"""
    crotch_extend_point: Tuple[float, float]      # 立裆延伸点（未落档）
    back_crotch_point: Tuple[float, float]        # 后立裆宽顶点（落档后）
    drop_crotch_line: List[Tuple[float, float]]   # 落档线（水平线段）
    drop_amount: float                             # 落档量


@dataclass
class BackRisePoints:
    """后浪曲线关键点（步骤4）"""
    hip_inner_point: Tuple[float, float]                 # 臀围内缝顶点 B
    kunshi_point: Tuple[float, float]                    # 困势顶点 K（困势线与落档线交点）
    helper_point: Tuple[float, float]                    # 后浪辅助点 H（角平分线上）
    rise_curve: List[Tuple[float, float]]                # 后浪曲线采样点（腰内→臀内→后立裆宽顶点）


@dataclass
class BackSeamPoints:
    """后片内缝/外缝曲线（步骤7）"""
    hip_outer_point: Tuple[float, float]                # 后臀围外缝顶点 (0, 84.6)
    outer_seam_curve: List[Tuple[float, float]]         # 外缝：腰外→臀外→膝外→脚口外
    inner_seam_curve: List[Tuple[float, float]]         # 内缝：立裆宽顶点→膝内→脚口内


@dataclass
class BackWaistFinalPoints:
    """后片最终腰围线（步骤8）"""
    new_waist_inner: Tuple[float, float]                # 新腰围内缝顶点（后浪长处，含后翘）
    new_waist_outer: Tuple[float, float]                # 新腰围外缝顶点（垂线与外缝延长线交点）
    waistline: List[Tuple[float, float]]                # 最终腰围线（外→内）
    rise_extension: List[Tuple[float, float]]           # 后浪切线延长段（A→新内顶点）
    outer_extension: List[Tuple[float, float]]          # 外缝切线延长段（W→新外顶点）


@dataclass
class BackDartPoints:
    """后片腰省（步骤9）"""
    dart_mid: Tuple[float, float]       # 省中点（腰围线中点）
    dart_tip: Tuple[float, float]       # 省尖（沿臀围线垂线向下11cm）
    dart_outer: Tuple[float, float]     # 省外端点（靠外缝侧）
    dart_inner: Tuple[float, float]     # 省内端点（靠内缝侧）


# ==================== 新增：后片腰头数据类型 ====================
@dataclass
class BackWaistbandPoints:
    """后片腰头关键点（步骤10）"""
    # 上腰头（已有腰围线）
    waist_outer: Tuple[float, float]       # 上腰头外缝顶点（腰围外缝顶点）
    waist_inner: Tuple[float, float]       # 上腰头内缝顶点（腰围内缝顶点）
    # 下腰头
    lower_waist_outer: Tuple[float, float]  # 下腰头外端点（沿外缝向下4cm）
    lower_waist_inner: Tuple[float, float]  # 下腰头内端点（沿后浪向下4cm）
    # 下腰头曲线（与上腰头平行）
    lower_waist_curve: List[Tuple[float, float]]  # 下腰头曲线采样点
# =================================================================

# ==================== 新增：后片机头数据类型 ====================
@dataclass
class BackJitouPoints:
    """后片机头关键点（步骤11）"""
    jitou_inner: Tuple[float, float]  # 机头内缝顶点（从下腰头内端点沿后浪向下7cm）
    jitou_outer: Tuple[float, float]  # 机头外缝顶点（从下腰头外端点沿外缝向下3.5cm）
# =================================================================

# ==================== 新增：后片后口袋数据类型 ====================
@dataclass
class BackPocketPoints:
    """后片后口袋关键点（步骤12）"""
    pocket_mid_up: Tuple[float, float]  # 后口袋上中点
    pocket_mid_down: Tuple[float, float]  # 后口袋下中点
    pocket_up_inner: Tuple[float, float]  # 后口袋上内端点
    pocket_up_outer: Tuple[float, float]  # 后口袋上外端点
    pocket_down_inner: Tuple[float, float]  # 后口袋下内端点（最终）
    pocket_down_outer: Tuple[float, float]  # 后口袋下外端点（最终）
    pocket_outline: List[Tuple[float, float]]  # 后口袋轮廓点
# =================================================================


@dataclass
class BackPatternPoints:
    """后片打版所有关键点（随步骤推进逐步填充）"""
    params: PatternParams
    bounding_box: BoundingBox        # 步骤1
    waist: BackWaistPoints           # 步骤2
    crotch: BackCrotchPoints         # 步骤3
    rise: BackRisePoints             # 步骤4
    center_crease_x: float           # 步骤5 裤中线横坐标
    knee_hem: KneeHemPoints          # 步骤6 实际膝围与脚口顶点（复用前片结构）
    seam: 'BackSeamPoints'           # 步骤7 内缝/外缝曲线
    waist_final: 'BackWaistFinalPoints'  # 步骤8 最终腰围线
    dart: 'BackDartPoints'           # 步骤9 腰省
    
    # ==================== 新增：腰头结果字段 ====================
    waistband: Optional['BackWaistbandPoints'] = None  # 步骤10 后片腰头 (设为Optional防报错)
    # ==================== 新增：机头结果字段 ====================
    jitou: Optional['BackJitouPoints'] = None  # 步骤11 后片机头 (设为Optional防报错)
    # ==================== 新增：后口袋结果字段 ====================
    back_pocket: Optional['BackPocketPoints'] = None  # 步骤12 后片后口袋 (设为Optional防报错)
    # =================================================================


@dataclass
class WaistbandPoints:
    """腰头关键点（含下腰头）"""
    # 上腰头
    waist_outer: Tuple[float, float]       # 上腰头外端点（腰围外缝顶点）
    waist_inner_final: Tuple[float, float] # 上腰头内端点（腰围内缝顶点）
    waist_control: Tuple[float, float]     # 上腰头贝塞尔控制点

    # 下腰头
    lower_waist_outer: Tuple[float, float]  # 下腰头外端点（沿外侧缝向下4cm）
    lower_waist_inner: Tuple[float, float]  # 下腰头内端点（沿前浪向下4cm）
    lower_waist_control: Tuple[float, float] # 下腰头贝塞尔控制点


@dataclass
class FrontFlyPoints:
    """前门襟关键点"""
    fly_start_point: Tuple[float, float]    # 门襟起点（从下腰头内端点向外3cm）
    fly_inner_end: Tuple[float, float]      # 门襟内端点（与臀围线交叉再延伸1cm）
    fly_outer_end: Tuple[float, float]      # 门襟外端点（与前浪交叉点）
    fly_end_point: Tuple[float, float]      # 门襟弧线终点（门襟线上离门襟内端点往上3cm）
    fly_curve: List[Tuple[float, float]]    # 门襟弧线
    fly_panel_outline: List[Tuple[float, float]] = None  # 门襟裁片闭合轮廓（单独裁片）


@dataclass
class CrescentPocketPoints:
    """月牙袋关键点"""
    pocket_outer: Tuple[float, float]       # 月牙袋外缝顶点（沿外侧缝向下7cm）
    pocket_width: Tuple[float, float]       # 月牙袋宽顶点（沿下腰头向内10cm）
    pocket_curve: List[Tuple[float, float]] # 月牙袋弧线
    pocket_dart: Tuple[float, float]        # 月牙袋省道点（沿下腰头再延伸0.6cm）
    pocket_dart_curve: List[Tuple[float, float]] # 月牙袋省道弧线
    pocket_dart_line_width: Tuple[float, float] # 月牙袋宽顶点向上腰头方向的垂直线终点
    pocket_dart_line_dart: Tuple[float, float] # 月牙袋省道点向上腰头方向的垂直线终点


@dataclass
class PocketPatchPoints:
    """袋贴关键点"""
    patch_lower_waist: Tuple[float, float]       # 袋贴下腰头顶点（月牙袋省道点沿下腰头再扩展3.5cm）
    patch_outer_seam: Tuple[float, float]        # 袋贴外缝顶点（月牙袋外缝顶点沿外缝再向下3.5cm）
    patch_curve: List[Tuple[float, float]]       # 袋贴弧线（与月牙袋省道弧线平行，间距3.5cm）


@dataclass
class PocketBagPoints:
    """袋布关键点"""
    bag_upper_waist: Tuple[float, float]       # 袋布上腰头顶点（袋贴下腰头顶点沿下腰头再延伸0.65cm）
    bag_inner_end: Tuple[float, float]         # 袋布内端点（袋布线离立裆线1cm处）
    bag_corner: Tuple[float, float]            # 袋布拐点（从内端点垂直于袋布线5.5cm）
    bag_outer_seam: Tuple[float, float]        # 袋布外缝顶点（袋贴外缝顶点沿外缝向下2.5cm）
    bag_line: List[Tuple[float, float]]        # 袋布线（上腰头顶点 → 内端点）
    bag_bottom_edge: List[Tuple[float, float]] # 袋布底边（内端点 → 拐点）
    bag_curve: List[Tuple[float, float]]       # 袋布弧线（拐点 → 外缝顶点）
    bag_top_edge: List[Tuple[float, float]]    # 袋布顶边（外缝顶点沿外缝+下腰头 → 上腰头顶点）


@dataclass
class WatchPocketPoints:
    """小表袋关键点"""
    outer_upper: Tuple[float, float]           # 小表袋上外端点
    outer_lower: Tuple[float, float]           # 小表袋下外端点（与袋贴交叉）
    inner_upper: Tuple[float, float]           # 小表袋上内端点
    inner_lower: Tuple[float, float]           # 小表袋下内端点（与袋贴交叉）
    outer_line: List[Tuple[float, float]]      # 小表袋外线（上外端点 → 下外端点）
    inner_line: List[Tuple[float, float]]      # 小表袋内线（上内端点 → 下内端点）
    bottom_curve: List[Tuple[float, float]]    # 小表袋底边（沿袋贴弧线 下内端点 → 下外端点）


@dataclass
class WaistPoints:
    """腰围线关键点（已废弃，保留兼容性）"""
    waist_outer: Tuple[float, float]       # 最终腰围外缝顶点
    waist_inner_final: Tuple[float, float] # 最终腰围内缝顶点
    waist_control: Tuple[float, float]     # 腰围线贝塞尔控制点


@dataclass
class PatternPoints:
    """完整的版型所有关键点"""
    params: PatternParams
    bounding_box: BoundingBox
    center_crease_x: float  # 裤中线X坐标

    # 前浪相关
    front_rise: FrontRisePoints

    # 膝围脚口
    knee_hem: KneeHemPoints

    # 腰围（保留兼容性）
    waist: WaistPoints

    # 腰头（含下腰头）
    waistband: WaistbandPoints

    # 前门襟
    front_fly: FrontFlyPoints

    # 月牙袋
    crescent_pocket: CrescentPocketPoints

    # 袋贴
    pocket_patch: PocketPatchPoints

    # 袋布
    pocket_bag: PocketBagPoints

    # 小表袋
    watch_pocket: WatchPocketPoints

    # 轮廓线采样点（用于绘制曲线）
    # 每条曲线由一系列点组成
    outer_seam_curve: List[Tuple[float, float]]  # 外侧缝曲线
    inner_seam_curve: List[Tuple[float, float]]  # 内侧缝曲线
    front_rise_curve: List[Tuple[float, float]]  # 前浪曲线
    waistline_curve: List[Tuple[float, float]]   # 上腰头曲线
    lower_waistline_curve: List[Tuple[float, float]]  # 下腰头曲线

    # 前片整体轮廓（裁片拆分，闭合轮廓）
    front_panel_outline: Optional[List[Tuple[float, float]]] = None

    # 前腰头裁片（裁片拆分，闭合轮廓，省道已拼合）
    front_waistband_outline: Optional[List[Tuple[float, float]]] = None

    # 袋贴裁片（裁片拆分，闭合轮廓）
    pocket_patch_outline: Optional[List[Tuple[float, float]]] = None

    # 小表袋裁片（裁片拆分，闭合轮廓）
    watch_pocket_outline: Optional[List[Tuple[float, float]]] = None