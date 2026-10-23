# settings.py
WIDTH, HEIGHT = 960, 540
TILE_SIZE = 40
FPS = 60

# 场景颜色
BG_COLOR_CAVE = (25, 20, 35)
BG_COLOR_GRASS = (50, 140, 60)
GRASS_DETAIL = (60, 160, 70)
WALL_COLOR_CAVE = (60, 60, 70)
WALL_BORDER = (30, 30, 40)
TEXT_COLOR = (220, 220, 220)
GOLD_COLOR = (255, 215, 0)

# 角色基础颜色
SKIN_COLOR = (255, 200, 150)
HAIR_COLOR = (80, 50, 30)

# 物理与数值
PLAYER_SPEED = 4.0
MAX_HP = 100          # 具体血量，不再是 3 颗心
HP_PER_LEVEL = 25
GRAVITY = 0.7
JUMP_VELOCITY = 11.0      # 向上为正，z 就是离地高度
MAX_ENERGY = 100
EXP_PER_KILL = 15
INVINCIBLE_FRAMES = 40

# 怪物数值
ENEMY_SPEED = 2.0
ENEMY_MAX_HP = 55     # 以史莱姆为基准
BOSS_MAX_HP = 620     # 第 1 关 BOSS；后面每关自动递增

# 武器类型
WEAPON_SWORD = 1
WEAPON_BOW = 2
WEAPON_STAFF = 3

# 职业展示名
CLASS_NAME = {WEAPON_SWORD: "剑士", WEAPON_BOW: "弓箭手", WEAPON_STAFF: "法师"}

# 每个职业一套完全不同的技能
SKILL_SPIN = "spin"      # 剑士：旋风斩（周身环形斩击 + 击退）
SKILL_VOLLEY = "volley"  # 弓箭手：箭雨（扇形穿透连射）
SKILL_NOVA = "nova"      # 法师：冰霜新星（范围冰爆 + 冻结）

SKILL_BY_WEAPON = {
    WEAPON_SWORD: {
        "type": SKILL_SPIN, "name": "旋风斩", "icon": "旋", "cd": 330,
        "radius": 132, "mult": 3.0, "color": (255, 122, 196),
        "desc": "周身环形斩击，强力击退",
    },
    WEAPON_BOW: {
        "type": SKILL_VOLLEY, "name": "箭雨", "icon": "雨", "cd": 300,
        "count": 7, "mult": 1.5, "color": (255, 156, 214),
        "desc": "扇形七连射，可穿透",
    },
    WEAPON_STAFF: {
        "type": SKILL_NOVA, "name": "冰霜新星", "icon": "冰", "cd": 420,
        "radius": 196, "mult": 2.2, "freeze": 150, "color": (255, 110, 196),
        "desc": "冰爆全场，冻结敌人 2.5 秒",
    },
}

# 每个职业的第三个技能（U 键）
SKILL3_BY_WEAPON = {
    WEAPON_SWORD: {
        "type": "quake", "name": "裂地斩", "icon": "裂", "cd": 380,
        "mult": 2.6, "radius": 170, "freeze": 70, "color": (255, 170, 120),
        "desc": "大地裂开，范围重击并定身",
    },
    WEAPON_BOW: {
        "type": "arrow_rain", "name": "箭幕", "icon": "幕", "cd": 360,
        "mult": 1.25, "radius": 240, "color": (190, 255, 200),
        "desc": "箭雨覆盖周身，持续压制",
    },
    WEAPON_STAFF: {
        "type": "meteor", "name": "陨石术", "icon": "陨", "cd": 400,
        "mult": 3.2, "radius": 150, "color": (255, 140, 90),
        "desc": "召唤陨石砸向最近的敌人",
    },
}

# 跟宠技能（按职业，阶段解锁）
PET_SKILLS = {
    WEAPON_SWORD: [("烈焰弹", "向最近的敌人喷射火球", 240),
                   ("烈焰爆", "以自身为中心炸开火焰", 480)],
    WEAPON_BOW: [("疾风箭", "三连射支援", 220),
                 ("风之祝福", "短时间提升主角移速", 480)],
    WEAPON_STAFF: [("治疗波", "治疗主角并回复少量蓝", 260),
                   ("魔力涌泉", "大量回蓝并回复生命", 500)],
}

# 每个职业的第二个技能（L 键）
SKILL2_BY_WEAPON = {
    WEAPON_SWORD: {
        "type": "wave", "name": "剑气斩", "icon": "气", "cd": 300,
        "mult": 2.0, "color": (255, 150, 210),
        "desc": "向前斩出穿透剑气",
    },
    WEAPON_BOW: {
        "type": "blast", "name": "爆裂箭", "icon": "爆", "cd": 330,
        "mult": 1.7, "radius": 96, "color": (255, 170, 120),
        "desc": "爆炸箭，范围伤害",
    },
    WEAPON_STAFF: {
        "type": "chain", "name": "连锁闪电", "icon": "电", "cd": 340,
        "mult": 1.4, "targets": 4, "freeze": 40, "color": (190, 160, 255),
        "desc": "闪电连锁 4 个敌人",
    },
}

# 装备部位
SLOT_NAMES = {"weapon": "武器", "armor": "衣甲", "helmet": "头盔",
              "boots": "鞋子", "pants": "裤子", "bracelet": "手镯"}

# 装备品质
Q_WHITE = "white"
Q_SILVER = "green"      # 绿色品质（原“精良”）
Q_PURPLE = "purple"
Q_GOLD = "gold"
Q_RED = "red"

Q_COLOR = {
    Q_WHITE: (230, 230, 230),
    Q_SILVER: (92, 208, 128),
    Q_PURPLE: (180, 50, 220),
    Q_GOLD: (255, 180, 0),
    Q_RED: (255, 50, 50),
}

Q_NAME = {Q_WHITE: "普通", Q_SILVER: "精良", Q_PURPLE: "史诗", Q_GOLD: "传说", Q_RED: "神话"}
Q_RANK = {Q_WHITE: 1, Q_SILVER: 2, Q_PURPLE: 3, Q_GOLD: 4, Q_RED: 5}

# 伤害类型
DMG_PHYS = "phys"
DMG_MAGIC = "magic"
DMG_TYPE_NAME = {DMG_PHYS: "物理", DMG_MAGIC: "法术"}

# 基础伤害（已上调，战士手感最明显）
INIT_SWORD_DMG = 14
INIT_BOW_DMG = 11
INIT_STAFF_DMG = 16

# 每级成长
DMG_PER_LEVEL = {WEAPON_SWORD: 6, WEAPON_BOW: 4, WEAPON_STAFF: 5}

# 武器伤害加成
DMG_BONUS_SILVER = 10
DMG_BONUS_PURPLE = 25
DMG_BONUS_GOLD = 45
DMG_BONUS_RED = 70

# 防御：减伤 = 点数 / (点数 + DEF_K)
DEF_K = 90.0
ARMOR_DEF = {Q_WHITE: 5, Q_SILVER: 11, Q_PURPLE: 18, Q_GOLD: 27, Q_RED: 38}
ARMOR_MRES = {Q_WHITE: 3, Q_SILVER: 6, Q_PURPLE: 10, Q_GOLD: 15, Q_RED: 22}
HELMET_DEF = {Q_WHITE: 2, Q_SILVER: 5, Q_PURPLE: 8, Q_GOLD: 12, Q_RED: 16}
HELMET_MRES = {Q_WHITE: 6, Q_SILVER: 12, Q_PURPLE: 19, Q_GOLD: 28, Q_RED: 38}

# 新部位属性
BOOTS_SPEED = {Q_WHITE: 0.04, Q_SILVER: 0.07, Q_PURPLE: 0.10, Q_GOLD: 0.14, Q_RED: 0.18}
BOOTS_DEF = {Q_WHITE: 1, Q_SILVER: 2, Q_PURPLE: 4, Q_GOLD: 7, Q_RED: 10}
PANTS_DEF = {Q_WHITE: 3, Q_SILVER: 7, Q_PURPLE: 12, Q_GOLD: 18, Q_RED: 26}
PANTS_HP = {Q_WHITE: 10, Q_SILVER: 20, Q_PURPLE: 35, Q_GOLD: 55, Q_RED: 80}
BRACELET_ATK = {Q_WHITE: 2, Q_SILVER: 5, Q_PURPLE: 9, Q_GOLD: 14, Q_RED: 20}
BRACELET_MRES = {Q_WHITE: 2, Q_SILVER: 5, Q_PURPLE: 9, Q_GOLD: 14, Q_RED: 20}

# 角色等级上限
MAX_PLAYER_LEVEL = 45

# 背包容量（格）
INVENTORY_MAX = 150

# 掉落概率（回调到合理范围）
GEAR_DROP_NORMAL = 0.14
GEAR_DROP_ELITE = 0.34
POTION_DROP_NORMAL = 0.22
BOSS_DROP_COUNT = 3          # BOSS 只掉 3 件装备
MYTHIC_HIDDEN_CHANCE = 0.30  # 神话装备带隐藏属性的概率

# 神话隐藏属性
HIDDEN_EFFECTS = {
    "lifesteal": ("吸血", "命中回复 8% 伤害"),
    "crit": ("致命", "暴击率 +8%"),
    "swift": ("疾行", "移动速度 +8%"),
    "mana": ("灵泉", "攻击额外回复 8 点蓝"),
    "guard": ("守护", "受到伤害 -8%"),
}

# 技能消耗（三技能）
SKILL_COST_PRIMARY = 55
SKILL_COST_SECONDARY = 50
SKILL_COST_TERTIARY = 45

# 跟宠成长
PET_MAX_STAGE = 3
PET_STAGE_NAMES = ["幼灵", "精灵", "大精灵", "守护灵"]

# 药水
POTION_HEAL = 35
POTION_ENERGY = 60

# 跟宠
PET_HEAL = 12
PET_HEAL_CD = 300
PET_ATTACK_CD = 70
PET_ATTACK_DMG = 8

# ---------------- 章节（4 大关 × 4 小关） ----------------
CHAPTERS = [
    {
        "key": "forest", "name": "翡翠森林", "color": (120, 210, 140),
        "levels": ["迷雾洞窟", "蘑菇森林", "古树秘境", "森林王座"],
        "weather": "petals",
    },
    {
        "key": "ocean", "name": "珊瑚深海", "color": (90, 190, 240),
        "levels": ["浅海礁林", "沉船墓场", "深渊裂谷", "海皇神殿"],
        "weather": "bubbles",
    },
    {
        "key": "sky", "name": "浮空天域", "color": (200, 210, 250),
        "levels": ["云海栈道", "雷鸣浮岛", "星辰回廊", "天空圣殿"],
        "weather": "feathers",
    },
    {
        "key": "volcano", "name": "熔火地狱", "color": (255, 130, 90),
        "levels": ["熔岩洞窟", "火山腹地", "岩浆之河", "深渊王座"],
        "weather": "embers",
    },
]
LEVELS_PER_CHAPTER = 4
TOTAL_LEVELS = len(CHAPTERS) * LEVELS_PER_CHAPTER
FINAL_LEVEL_INDEX = TOTAL_LEVELS - 1
FINAL_BOSS_LEVEL = 45


def chapter_of(level_index):
    return max(0, min(len(CHAPTERS) - 1, level_index // LEVELS_PER_CHAPTER))


def level_theme(level_index):
    return CHAPTERS[chapter_of(level_index)]["key"]


def level_title(level_index):
    ch = CHAPTERS[chapter_of(level_index)]
    sub = level_index % LEVELS_PER_CHAPTER
    return ch["name"], ch["levels"][sub]


# 每关 BOSS 数量（逐章变多）
def boss_count(level_index):
    chapter = chapter_of(level_index)
    sub = level_index % LEVELS_PER_CHAPTER
    base = [1, 1, 1, 3][sub]
    return min(5, base + chapter)


# ---------------- 装备系列（按大关卡） ----------------
BOSS_ROSTER = {
    "forest": [("slime", "史莱姆王"), ("mushroom", "蘑菇大王"),
               ("tree", "树妖王"), ("skeleton", "骷髅王"), ("golem", "远古石魔")],
    "ocean": [("slime", "潮汐巨兽"), ("mushroom", "珊瑚领主"),
              ("tree", "海妖王"), ("skeleton", "沉船骨王"), ("golem", "深海巨像")],
    "sky": [("slime", "雷云巨灵"), ("mushroom", "星菇王"),
            ("tree", "风暴树精"), ("skeleton", "天空骨王"), ("golem", "雷霆巨像")],
    "volcano": [("slime", "熔岩史莱姆"), ("mushroom", "火焰菇王"),
                ("tree", "灰烬树妖"), ("skeleton", "熔骨王"), ("golem", "熔岩巨像")],
}

GEAR_SETS = {
    "forest": {
        "name": "森之",
        "weapon": {WEAPON_SWORD: "林间长剑", WEAPON_BOW: "翠影长弓", WEAPON_STAFF: "古木法杖"},
        "armor": "藤甲", "helmet": "叶盔", "boots": "疾风靴",
        "pants": "游侠裤", "bracelet": "翠玉镯",
        "color": (120, 210, 140),
    },
    "ocean": {
        "name": "海底",
        "weapon": {WEAPON_SWORD: "珊瑚长剑", WEAPON_BOW: "潮汐长弓", WEAPON_STAFF: "海神法杖"},
        "armor": "贝壳铠甲", "helmet": "海螺头盔", "boots": "浪花战靴",
        "pants": "鱼鳞护腿", "bracelet": "珍珠手镯",
        "color": (90, 190, 240),
    },
    "sky": {
        "name": "天空",
        "weapon": {WEAPON_SWORD: "云刃", WEAPON_BOW: "风暴之弓", WEAPON_STAFF: "星辰法杖"},
        "armor": "云纹战衣", "helmet": "雷羽冠", "boots": "踏云靴",
        "pants": "疾风护腿", "bracelet": "星辰手环",
        "color": (200, 210, 250),
    },
    "volcano": {
        "name": "熔火",
        "weapon": {WEAPON_SWORD: "熔岩巨剑", WEAPON_BOW: "烈阳弓", WEAPON_STAFF: "炎心法杖"},
        "armor": "熔铁战甲", "helmet": "炎魔盔", "boots": "岩浆战靴",
        "pants": "熔火护腿", "bracelet": "炽炎手环",
        "color": (255, 130, 90),
    },
}


# 道具类型中文名
ITEM_NAME = {
    "weapon": "武器", "armor": "衣甲", "helmet": "头盔", "key": "钥匙", "chest": "宝箱",
    "potion_hp": "生命药水", "potion_energy": "能量药水",
    "potion_speed": "疾风药水", "bomb": "炸弹",
}

# 跳跃 / 矮墙 / 平台
LOW_WALL_CHAR = "6"
LOW_WALL_Z = 20            # z 高于这个值就能越过矮墙
JUMP_DODGE_Z = 24          # 跳跃时躲开地面攻击/弹幕
PLATFORM_CHAR = "7"        # 可以跳上去站着的平台
PLATFORM_H = 30            # 平台高度
SPIKE_CHAR = "8"           # 尖刺陷阱
SPIKE_DAMAGE = 9
CRATE_CHAR = "9"           # 木箱：挡住路，能打碎
CRATE_HP = 3

# 道具栏（按 1~4 或点击使用）
ITEM_SLOTS = ["potion_hp", "potion_energy", "potion_speed", "bomb"]
ITEM_HOTKEY = {"potion_hp": "1", "potion_energy": "2", "potion_speed": "3", "bomb": "4"}

# 疾风药水
SPEED_POTION_MULT = 1.65
SPEED_POTION_FRAMES = 9 * 60

# 炸弹
BOMB_RADIUS = 110

# 跟宠：弓箭手跟宠提供攻速加成
PET_HASTE = 0.32
# 跟宠：法师跟宠回蓝间隔
PET_ENERGY_CD = 90
PET_ENERGY_AMOUNT = 12

# 通关密码
FINAL_PASSWORD = "0909"



# ---------------- BOSS 排布：同一大关内每关不重复 ----------------
BOSS_TIER_PREFIX = ["", "狂暴·", "远古·", "深渊·"]


def chapter_boss_plan(level_index):
    """返回该关的 BOSS 列表 [(type, name, tier)]，同一大关内不重复。"""
    chapter = chapter_of(level_index)
    sub = level_index % LEVELS_PER_CHAPTER
    base = BOSS_ROSTER[CHAPTERS[chapter]["key"]]
    offset = sum(boss_count(chapter * LEVELS_PER_CHAPTER + k) for k in range(sub))
    plan = []
    for i in range(boss_count(level_index)):
        slot = offset + i
        tier, idx = divmod(slot, len(base))
        tier = min(tier, len(BOSS_TIER_PREFIX) - 1)
        btype, bname = base[idx]
        plan.append((btype, BOSS_TIER_PREFIX[tier] + bname, tier))
    return plan
