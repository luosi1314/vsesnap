import vapoursynth as vs
core = vs.core
import havsfunc as haf
import os

# 预览脚本 - 偏移量为0

# 设置缓存目录
cache_dir = os.path.join(os.getcwd(), '.cache')
os.makedirs(cache_dir, exist_ok=True)

try:
    import awsmfunc as awf
    HAS_AWSMFUNC = True
except ImportError:
    HAS_AWSMFUNC = False
    print('警告: awsmfunc 未安装，将不显示帧信息')

# [P003]【4K修复】魔幻手机1 1.1.mp4 - 原生PAL (25fps)
P003__4K修复_魔幻手机1_1_1_mp4 = core.lsmas.LWLibavSource(r"Y:/画质对比/魔幻手机/all/[P003]【4K修复】魔幻手机1 1.1.mp4", cachedir=cache_dir)
if HAS_AWSMFUNC:
    P003__4K修复_魔幻手机1_1_1_mp4 = awf.FrameInfo(P003__4K修复_魔幻手机1_1_1_mp4, '[P003]【4K修复】魔幻手机1 1.1.mp4')

P003__4K修复_魔幻手机1_1_1_mp4.set_output(0)
