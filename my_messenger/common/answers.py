from my_messenger.common.utils import get_configs

CONFIGS = get_configs()

# Словари - ответы:
# 200
RESPONSE_200 = {CONFIGS.get('RESPONSE'): 200}
# 202
RESPONSE_202 = {CONFIGS.get('RESPONSE'): 202,
                CONFIGS.get('LIST_INFO'): None
                }
# 400
RESPONSE_400 = {
    CONFIGS.get('RESPONSE'): 400,
    CONFIGS.get('ERROR'): None
}
# 205
RESPONSE_205 = {
    CONFIGS.get('RESPONSE'): 205
}

# 511
RESPONSE_511 = {
    CONFIGS.get('RESPONSE'): 511,
    CONFIGS.get('DATA'): None
}
