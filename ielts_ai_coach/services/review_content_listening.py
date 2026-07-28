"""Reviewed static Chinese content for every bundled Listening item."""

from __future__ import annotations


LISTENING_REVIEW_SEEDS: dict[str, tuple[str, str]] = {
    "L1-Q01": ("我想报名城市速写课程。", "urban sketching 是报名课程的完整名称，不能只选泛指的绘画课程。"),
    "L1-Q02": ("我的名字是 Maya Chen；Chen 拼作 C-H-E-N。", "拼写被逐字确认，填空必须写 Chen 而不是只凭读音猜测。"),
    "L1-Q03": ("课程在九月十四日开始。", "日期信息在 begin 后直接给出，要保留日和月。"),
    "L1-Q04": ("课程在周二晚上进行。", "runs on 表示固定安排，答案是 Tuesday。"),
    "L1-Q05": ("在 204 教室。", "room 后的数字就是地点答案，不能写成楼层。"),
    "L1-Q06": ("全额费用是八十五英镑。", "fee 后的金额为 85，注意不是课程编号或房间号。"),
    "L1-Q07": ("请带一本 A4 速写本，铅笔会提供。", "自带物品是 A4 sketchbook；pencils 是由课程提供的干扰信息。"),
    "L1-Q08": ("Daniel Chen，他是我的哥哥。", "联系人姓名由名字和姓氏组成，不能只写 Daniel。"),
    "L1-Q09": ("服务台在一楼。", "地点由 on the first floor 明确给出。"),
    "L1-Q10": ("安静室 3B 在历史藏书旁边。", "房间编号包含数字和字母，漏掉 B 会失分。"),
    "L1-Q11": ("小组房必须提前四十八小时预订。", "in advance 前的时间量是 48 hours。"),
    "L1-Q12": ("普通图书可以借十四天。", "借阅期限对应 ordinary books，不要与其他服务混淆。"),
    "L1-Q13": ("可以在线续借两次。", "twice 表示 2 次，注意题目要求次数而不是天数。"),
    "L1-Q14": ("打印机在东侧楼梯旁。", "方位词 east 是定位答案，stairs 只是参照物。"),
    "L1-Q15": ("研究技能讲座本周五下午四点开始。", "时间表达 four p.m. this Friday 要同时听出日期和时刻。"),
    "L1-Q16": ("在花园门口集合。", "meet at 后的 garden gate 是集合点。"),
    "L2-Q01": ("在 Riverside Station 的主入口集合。", "地点名称是 Riverside，main entrance 提供更完整的定位。"),
    "L2-Q02": ("在七点四十五分。", "At seven forty-five 直接给出集合时间。"),
    "L2-Q03": ("八点十分从六号站台出发。", "题目问出发时间，答案是 8:10；platform six 是相邻信息。"),
    "L2-Q04": ("从六号站台出发。", "题目问站台号，因此取 platform six 中的 6。"),
    "L2-Q05": ("带防水外套，而不是雨伞。", "rather than 明确排除 umbrella，正确物品是 waterproof jacket。"),
    "L2-Q06": ("还需要带午餐和笔记本。", "also need 后列出两个物品，题目空格对应 notebook。"),
    "L2-Q07": ("Priya Shah 博士。", "称呼后的完整姓名是 Priya Shah，填空不要遗漏姓氏。"),
    "L2-Q08": ("晚上六点半。", "时间表达 six thirty in the evening 对应 6:30 pm。"),
    "L2-Q09": ("研究屋顶花园如何影响城市热量。", "讲座主题是 rooftop gardens 与 urban heat 的关系。"),
    "L2-Q10": ("我们的团队监测了十二栋办公楼。", "数量 12 修饰 office buildings，不要写成测量频率。"),
    "L2-Q11": ("每十分钟记录一次读数。", "every ten minutes 表示间隔，答案是 10。"),
    "L2-Q12": ("朝北的绿色屋顶平均低 2.4 度。", "原文明确比较 north-facing roofs，因此选择该屋顶方向。"),
    "L2-Q13": ("比裸屋顶低 2.4 度。", "本题问温差，取 two point four 而不是屋顶方向。"),
    "L2-Q14": ("最低土层深度为二十厘米。", "minimum soil depth 后的数字 20 是条件阈值。"),
    "L2-Q15": ("我们惊讶地记录到许多野生蜜蜂。", "surprised to record 后的对象是 wild bees。"),
    "L2-Q16": ("下一阶段将收集冬季数据。", "next phase 指未来安排，答案为 winter。"),
}


LISTENING_VOCABULARY_SEEDS: dict[str, tuple[tuple[str, str, str, str, str, str, str], ...]] = {
    "LISTEN-V1-001-S1": (("register", "/ˈredʒɪstə/", "verb", "报名登记", "to sign up officially", "enrol", "表格与课程场景的高频动词"), ("urban sketching", "/ˈɜːbən ˈsketʃɪŋ/", "noun phrase", "城市速写", "drawing scenes in a city", "city drawing", "课程名需连读并整体记录"), ("begins", "/bɪˈɡɪnz/", "verb", "开始", "starts at a time", "starts", "听到 begins 后注意日期或时间"), ("Tuesday evenings", "/ˈtjuːzdeɪ ˈiːvnɪŋz/", "noun phrase", "周二晚上", "Tuesday night sessions", "on Tuesday nights", "固定安排常用 runs on 表达"), ("Room", "/ruːm/", "noun", "房间、教室", "a numbered indoor space", "classroom", "后面常跟数字或字母编号"), ("full fee", "/fʊl fiː/", "noun phrase", "全额费用", "total price to pay", "total cost", "数字题要核对货币单位"), ("sketchbook", "/ˈsketʃbʊk/", "noun", "速写本", "book for drawings", "drawing pad", "复合名词拼写容易漏写 book"), ("provided", "/prəˈvaɪdɪd/", "verb", "提供", "supplied for users", "supplied", "区分自带物品和机构提供物品")),
    "LISTEN-V1-001-S2": (("help desk", "/help desk/", "noun phrase", "咨询台", "place for assistance", "information desk", "方位题先听地点再听楼层"), ("quiet room", "/ˈkwaɪət ruːm/", "noun phrase", "安静学习室", "room for silent study", "silent room", "编号可能含数字与字母"), ("booked", "/bʊkt/", "verb", "预订", "reserved in advance", "reserved", "注意被动结构 must be booked"), ("in advance", "/ɪn ədˈvɑːns/", "phrase", "提前", "before the event", "ahead of time", "常与时间间隔搭配"), ("borrowed", "/ˈbɒrəʊd/", "verb", "借阅", "taken temporarily", "checked out", "图书规则题常考期限"), ("renewed", "/rɪˈnjuːd/", "verb", "续借", "extended for longer", "extended", "注意次数与借阅期限不同"), ("printers", "/ˈprɪntəz/", "noun", "打印机", "machines for printing", "printing machines", "位置题常以楼梯等地标参照"), ("workshop", "/ˈwɜːkʃɒp/", "noun", "研讨讲座", "practical learning session", "training session", "日期时间应作为整体记录")),
    "LISTEN-V1-002-S1": (("main entrance", "/meɪn ˈentrəns/", "noun phrase", "主入口", "principal way into a place", "front entrance", "集合地点常包含场所名加具体入口"), ("platform", "/ˈplætfɔːm/", "noun", "站台", "railway boarding area", "trackside platform", "数字紧跟 platform 时注意题目问时间还是站台"), ("waterproof jacket", "/ˈwɔːtəpruːf ˈdʒækɪt/", "noun phrase", "防水外套", "jacket that keeps out rain", "rain jacket", "rather than 后常出现排除性干扰项"), ("packed lunch", "/pækt lʌntʃ/", "noun phrase", "自备午餐", "meal prepared to take along", "prepared lunch", "并列物品题要找所填空格对应项"), ("notebook", "/ˈnəʊtbʊk/", "noun", "笔记本", "book for notes", "note pad", "注意与笔记 note 不同"), ("Doctor", "/ˈdɒktə/", "title", "博士、医生称谓", "title before a name", "Dr", "姓名题通常只填人名，不填称谓"), ("evening", "/ˈiːvnɪŋ/", "noun", "傍晚、晚上", "later part of the day", "p.m.", "12 小时制要依靠 evening 确认"), ("briefing", "/ˈbriːfɪŋ/", "noun", "行前说明", "short instruction meeting", "orientation", "用于说明活动安排和要求")),
    "LISTEN-V1-002-S2": (("rooftop gardens", "/ˈruːftɒp ˈɡɑːdnz/", "noun phrase", "屋顶花园", "gardens on building roofs", "green roofs", "研究主题应抓住名词短语"), ("urban heat", "/ˈɜːbən hiːt/", "noun phrase", "城市热量", "heat conditions in cities", "city heat", "题干常把 affect 与 impact 同义替换"), ("monitored", "/ˈmɒnɪtəd/", "verb", "监测", "observed over time", "tracked", "后面常跟样本数量"), ("reading", "/ˈriːdɪŋ/", "noun", "读数", "a measured value", "measurement", "不要误解为阅读行为"), ("north-facing", "/ˌnɔːθ ˈfeɪsɪŋ/", "adjective", "朝北的", "facing north", "northward-facing", "方位比较题的定位词"), ("bare roofs", "/beə ruːfs/", "noun phrase", "裸露屋顶", "roofs without garden cover", "uncovered roofs", "与绿色屋顶构成比较对象"), ("soil depth", "/sɔɪl depθ/", "noun phrase", "土层深度", "how deep the soil is", "depth of soil", "minimum 后的数字表示阈值"), ("wild bees", "/waɪld biːz/", "noun phrase", "野生蜜蜂", "bees living naturally", "native bees", "surprised to record 后面是发现对象")),
}
