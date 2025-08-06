# app/config.py

# Redis 连接配置
# 建议在生产环境中使用环境变量来获取这些值
REDIS_HOST = "localhost"
REDIS_PORT = 6379

# 滑动窗口的持续时间（秒）
WINDOW_SECONDS = 60

# API Key 的速率限制配置
# 在真实应用中，这些信息通常存储在数据库或专门的配置服务中
# Key: API Key
# Value: 一个包含 rpm, input_tpm, output_tpm 的字典
API_KEYS_CONFIG = {
    "test-key-1": {
        "name": "Default Tier",
        "rpm": 500,          # 每分钟请求数限制
        "input_tpm": 60000,  # 每分钟输入 token 数限制
        "output_tpm": 20000, # 每分钟输出 token 数限制
    },
    "test-key-2": {
        "name": "High-Throughput Tier",
        "rpm": 1000,
        "input_tpm": 200000,
        "output_tpm": 80000,
    },
    # 你可以在这里添加更多的 API Key
    "unlimited-key": {
        "name": "Unlimited Test",
        "rpm": 999999,
        "input_tpm": 99999999,
        "output_tpm": 99999999,
    },

    "free-tier-key": {
        "name": "Free Tier",
        "rpm": 20,
        "input_tpm": 4000,
        "output_tpm": 1000,
    }
}
