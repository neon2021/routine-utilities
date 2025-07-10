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
print(f'json_fp:{json_fp}, curl_fp:{curl_fp}')

limit_ids_len = 20
# limit_ids_len = 2000

# 从文件中读取ID
with open(json_fp, "r", encoding="utf-8") as f:
    activies_json_array = json.loads(f.read())
    ids = [str(act['activityId']) for act in activies_json_array[0]]

print('act_ids: ', ','.join(ids[0:10]))
# ids = ids[0:1]

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

# crawl_type = 'summary'
crawl_type = 'exerciseSets'

max_len = limit_ids_len if len(ids) > limit_ids_len else len(ids)
ids = ids[0:max_len]
for id_value in ids:
    if crawl_type=='summary':
        # 拼接 url
        url = f"https://connect.garmin.cn/activity-service/activity/{id_value}"
    else:
        url = f"https://connect.garmin.cn/activity-service/activity/{id_value}/exerciseSets"
    
    
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
        print(f"✅ 成功请求 id={id_value}")
    except Exception as e:
        print(f"❌ 请求 id={id_value} 失败：{e}")

# 写入所有结果
output_fp=os.path.join(global_dir, f"{crawl_type}-all_results-{date_ymd}.json")
with open(output_fp, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"🎉 已完成写入 {output_fp}")
