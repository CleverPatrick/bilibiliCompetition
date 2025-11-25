import pandas as pd
from DrissionPage import Chromium,ChromiumPage,ChromiumOptions
import time
import requests

# 启动浏览器
try:
    tab = Chromium().latest_tab
    tab.get('https://www.bilibili.com/v/game/match/competition')
except:
    try:
        path = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'  # 改为电脑内默认edge可执行文件路径
        co = ChromiumOptions().set_browser_path(path)
        tab = Chromium(co).latest_tab
        tab.get('https://www.bilibili.com/v/game/match/competition')
    except:
        path = input("启动失败输入edge的可执行文件路径/快捷方式(不知道可以在edge浏览器网址栏输入'edge://version')：")
        # 请改为你电脑内Chrome可执行文件路径  C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe
        ChromiumOptions().set_browser_path(path).save()
        try:
            tab = Chromium().latest_tab
            tab.get('https://www.bilibili.com/v/game/match/competition')
        except:
            print("启动失败,输入路径有误，请重新打开该软件")
            print("5秒后自动退出...")
            time.sleep(5)
            quit()


#获取总场数来判断是否登录
while True:
    sum = tab.ele('x://*[@id="server-game-app"]/div[2]/div[2]/div[2]/div[1]/ul/li[1]/span').text
    if sum == "-":
        input("请登录Bilibili后，再按回车键继续...")
    else:
        break

# 获取当前 Cookie 并转换为字典格式
cookies_list = tab.cookies()
cookies_dict = {cookie['name']: cookie['value'] for cookie in cookies_list}
# print(cookies_dict)  # 用于 requests 的 cookie 字典
tab.close()



headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
    "Referer": "https://www.bilibili.com/",
}

params = {
    "type": 2,    # 1: 进行中，2: 已结束
    "pn": 0,      # 页码
    "ps": 50,     # 每页数量（可尝试调大）
}

url = "https://api.bilibili.com/x/esports/guess/collection/record"

columns = ["比赛名", "对战队伍", "预测选项", "正确选项", "投币数量", "赔率", "获得收益"]
df_total = pd.DataFrame(data=None, columns=columns)
df = pd.DataFrame(data=None)
# 获取数据
while True:
    params["pn"] += 1
    response = requests.get(url, headers=headers, cookies=cookies_dict, params=params)
    data = response.json()

    if data["data"]["record"] is not None:
        #数据处理并且保存为excel文件
        for i in range(len(data["data"]["record"])):
            df.loc[i, 0] = data["data"]["record"][i]["contest"]["season"]["title"]
            df.loc[i, 1] = data["data"]["record"][i]["guess"][0]["title"][:-5]
            df.loc[i, 2] = data["data"]["record"][i]["guess"][0]["option"]
            df.loc[i, 3] = data["data"]["record"][i]["guess"][0]["right_option"]
            df.loc[i, 4] = data["data"]["record"][i]["guess"][0]["stake"]
            df.loc[i, 5] = data["data"]["record"][i]["guess"][0]["odds"]
            df.loc[i, 6] = data["data"]["record"][i]["guess"][0]["income"]

        df.columns = columns  # 修改df的列名
        df_total = df_total._append(df, ignore_index=True)# 将df的数据添加到df_total中
        df = pd.DataFrame(data=None)
        time.sleep(0.1)

    else:
        print("读取结束")
        break

df_total[""] = ""  #df_total增加一列空列


# 按赛事名统计各项指标
event_stats = df_total.groupby('比赛名').agg({
    '投币数量': 'sum',           # 总投币数
    '获得收益': 'sum',           # 总收益
    '预测选项': 'count'          # 总场数
}).reset_index()

# 重命名列
event_stats = event_stats.rename(columns={
    '投币数量': '总投币数',
    '获得收益': '总收益',
    '预测选项': '总场数'
})

# 计算胜场、败场和胜率
def calculate_win_stats(group):
    # 胜场：预测选项 == 正确选项
    wins = (group['预测选项'] == group['正确选项']).sum()
    # 总场数
    total = len(group)
    # 败场
    losses = total - wins
    # 胜率
    win_rate = wins / total if total > 0 else 0
    return pd.Series({
        '胜场': wins,
        '败场': losses,
        '胜率': win_rate
    })

# 按赛事计算胜场统计
win_stats = df_total.groupby('比赛名').apply(calculate_win_stats).reset_index()

# 合并统计数据
final_stats = event_stats.merge(win_stats, on='比赛名')

final_stats.insert(3, '总利润', final_stats['总收益'] - final_stats['总投币数'])

#将final_Stats内各个数据算出一个总数在最后一行
total = final_stats.shape[0] + 1
final_stats.loc[total] = [
    "总",
    final_stats["总投币数"].sum(),
    final_stats["总收益"].sum(),
    final_stats["总利润"].sum(),
    final_stats["总场数"].sum(),
    final_stats["胜场"].sum(),
    final_stats["败场"].sum(),
    final_stats["胜场"].sum() / final_stats["总场数"].sum(),
]

# 格式化胜率为百分比
final_stats['胜率'] = (final_stats['胜率'] * 100).round(2).astype(str) + '%'
#重置final_stats的索引
final_stats.reset_index(drop=True, inplace=True)


df_total["赛事名"] = "" #[0,8]
df_total["总投币数"] = ""
df_total["总收益"] = ""
df_total["总利润"] = ""
df_total["总场数"] = ""
df_total["胜场"] =  ""
df_total["败场"] = ""
df_total["胜率"] = ""

for i in range(0, final_stats.shape[0]):
    df_total.loc[i, "赛事名"] = final_stats.loc[i, "比赛名"]
    df_total.loc[i, "总投币数"] = final_stats.loc[i, "总投币数"]
    df_total.loc[i, "总收益"] = final_stats.loc[i, "总收益"]
    df_total.loc[i, "总利润"] = final_stats.loc[i, "总利润"]
    df_total.loc[i, "总场数"] = final_stats.loc[i, "总场数"]
    df_total.loc[i, "胜场"] = final_stats.loc[i, "胜场"]
    df_total.loc[i, "败场"] = final_stats.loc[i, "败场"]
    df_total.loc[i, "胜率"] = final_stats.loc[i, "胜率"]

df_total.index = df_total.index + 1  # 修改df_total的索引
df_total.to_excel("bili赛事预测统计数据.xlsx")
