from blocklay import Blocklay

blocklay = Blocklay()


async def script1():
    """
    # TOML document
    # 独立脚本，需要手动调用才会执行
    pos = [x, y] # x和y是在工作区的位置（第一个积木）

    # 折叠
    fold = false/true
    """
    pin.level(2, 1)


# 入口
@blocklay.entry()
async def script2():
    """
    # 程序入口（可以多个），启动时自动调用
    pos = [x, y]
    """
    pass


async def block1(arg1: int = 0, arg2: int = 0) -> None:
    """
    # 标准积木定义
    # 返回类型为None是一个普通标准积木
    # 返回类型为str/int/float/bool表示是一个内嵌积木
    # arg是可内嵌的积木，str/int/float/bool，默认值是""/0/False

    # 过程被保护的
    protected = false/true

    # 允许展开时，可以通过x和y，在工作区显示积木定义，没有设置时只会在积木区显示单个积木
    pos = [x, y]

    # [label]是积木显示的文本表（多语言）
    # en是积木默认显示的文本（英文），[]中是参数名（必须为英文，函数声明参数），冒号后面的是显示文本，没有则用参数名（仅在显示积木定义时有）
    # zh-hans是中文翻译
    [label]
    en = "sum [arg1] [arg2]"
    zh-hans = "求和 [arg1:参数1] [arg2:参数2]"

    # [tip]是积木的提示文本表（多语言）
    [tip]
    en = "sum"
    zh-hans = "求和"
    """
    pass


# 非可见代码
async def __condition1():
    return False


# 带条件入口
@blocklay.entry(__condition1)
async def script4():
    """
    # 当条件满足时才会被执行
    pos = [x, y]
    """
    pass
