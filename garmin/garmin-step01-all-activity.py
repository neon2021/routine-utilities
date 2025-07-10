import requests
import json
import os
import re
from datetime import datetime
from global_config.config import yaml_config
print(yaml_config)

global_dir = yaml_config.get('global_dir')

date_ymd=datetime.now().strftime('%Y-%m-%d')
json_fp = os.path.join(global_dir,f"garmin-activities-{date_ymd}.json")
curl_fp = os.path.join(global_dir,"garmin-activity-curl.txt")


headers={}
with open(curl_fp, "r", encoding="utf-8") as f:
    header_lines = f.readlines()
    for line in header_lines:
        found = re.findall(r'\s*-H\s*\'([^:]+)\s*:\s*([^\']+)\'\s*\\?', line)
        print(f'found: {found}')
        if(len(found)<=0):
            found_cookie = re.findall(r'\s*-b\s*\'([^\']+)\'\s*\\?', line)
            print(f'found_cookie: {found_cookie}')
            if(len(found_cookie)<=0):
                continue
            cookie = found_cookie[0]
            key='cookie'
            value=cookie
        else:
            key=found[0][0]
            value=found[0][1]
            # print(f'key:{key},value:{value}')
        headers[key]=value


results = []
url = f"https://connect.garmin.cn/activitylist-service/activities/search/activities?limit=2000&start=0"

# # 你也可以自定义 headers
# headers = {
#     "accept": "application/json, text/plain, */*",
#     "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,ko;q=0.7"
# }

try:
    # resp = requests.get(url, headers=headers, timeout=10)
    resp = requests.get(url, headers=headers, timeout=10, verify="/etc/ssl/cert.pem") # for macos
    resp.raise_for_status()
    results.append(resp.json())
    print(f"✅ 成功请求")
except Exception as e:
    print(f"❌ 请求 失败：{e}")

# 写入所有结果
output_fp=os.path.join(global_dir, f"garmin-activities-{date_ymd}.json")
with open(output_fp, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"🎉 已完成写入 {output_fp}")