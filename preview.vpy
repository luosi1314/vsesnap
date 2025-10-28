import vapoursynth as vs
core = vs.core
import os

# 预览脚本 - 偏移量为0

# 设置缓存目录
cache_dir = os.path.join(os.getcwd(), '.cache')
os.makedirs(cache_dir, exist_ok=True)

try:
    import havsfunc as haf
    HAF_AVAILABLE = True
except ImportError:
    HAF_AVAILABLE = False
    print('警告: havsfunc 未安装，QTGMC 将被跳过')

try:
    import awsmfunc as awf
    HAS_AWSMFUNC = True
except ImportError:
    HAS_AWSMFUNC = False
    print('警告: awsmfunc 未安装，将不显示帧信息')

HAS_LSMASH = hasattr(core, 'lsmas')
HAS_BS = hasattr(core, 'bs')
HAS_FFMS2 = hasattr(core, 'ffms2')
def load_source(path):
    if HAS_LSMASH:
        return core.lsmas.LWLibavSource(path, cachedir=cache_dir)
    elif HAS_BS:
        return core.bs.VideoSource(source=path)
    elif HAS_FFMS2:
        return core.ffms2.Source(path)
    else:
        raise RuntimeError('未找到视频源插件: 需要 LSMASHSource/BestSource/FFMS2')

# “他曾把情郎思,也曾把君王刺”【焦恩俊___黄天霸】.“他曾把情郎思,也曾把君王刺”【焦恩俊___黄天霸】.978494961.mp4 - 原生PAL (25fps)
他曾把情郎思_也曾把君王刺__焦恩俊___黄天霸___他曾把情郎思_也曾把君王刺__焦恩俊___黄天霸__978494961_mp4 = load_source(r"D:/Documents/“他曾把情郎思,也曾把君王刺”【焦恩俊___黄天霸】.“他曾把情郎思,也曾把君王刺”【焦恩俊___黄天霸】.978494961.mp4")
if HAF_AVAILABLE:
    他曾把情郎思_也曾把君王刺__焦恩俊___黄天霸___他曾把情郎思_也曾把君王刺__焦恩俊___黄天霸__978494961_mp4 = haf.QTGMC(他曾把情郎思_也曾把君王刺__焦恩俊___黄天霸___他曾把情郎思_也曾把君王刺__焦恩俊___黄天霸__978494961_mp4, Preset="Slower", TFF=True, FPSDivisor=2)
else:
    print('警告: havsfunc 未安装，跳过 QTGMC')
if HAS_AWSMFUNC:
    他曾把情郎思_也曾把君王刺__焦恩俊___黄天霸___他曾把情郎思_也曾把君王刺__焦恩俊___黄天霸__978494961_mp4 = awf.FrameInfo(他曾把情郎思_也曾把君王刺__焦恩俊___黄天霸___他曾把情郎思_也曾把君王刺__焦恩俊___黄天霸__978494961_mp4, '“他曾把情郎思,也曾把君王刺”【焦恩俊___黄天霸】.“他曾把情郎思,也曾把君王刺”【焦恩俊___黄天霸】.978494961.mp4')

他曾把情郎思_也曾把君王刺__焦恩俊___黄天霸___他曾把情郎思_也曾把君王刺__焦恩俊___黄天霸__978494961_mp4.set_output(0)
