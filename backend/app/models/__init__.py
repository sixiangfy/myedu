# 需要在数据库初始化时注册的模型列表
TORTOISE_MODELS = [
    "app.models.user",
    "app.models.grade",
    "app.models.class_model",
    "app.models.subject",
    "app.models.teacher",
    "app.models.student",
    "app.models.exam",
    "app.models.score",
    "app.models.analytics",
]

# 避免在此处导入模型类，防止循环引用
# 需要在其他地方明确导入具体模型 