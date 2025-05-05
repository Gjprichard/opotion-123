import sys
sys.path.append('.')

from services.exchange_api_ccxt import get_option_market_data

# 获取BTC期权数据
options = get_option_market_data('BTC')
print(f'获取到 {len(options)} 个BTC期权合约数据')

# 打印示例数据
if options:
    print('示例期权数据:')
    print(options[0])
else:
    print('没有获取到期权数据')