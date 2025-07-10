from jsonpath_ng import jsonpath, parse
import json
import os
from datetime import datetime
from global_config.config import yaml_config
print(yaml_config)
global_dir = yaml_config.get('global_dir')

json_fp = os.path.join(global_dir,"exerciseSets-all_results-2025-07-06.json")

group_by_date_json_fp = os.path.join(global_dir,"exerciseSets-group_by_date-2025-07-06.json")
group_by_movement_json_fp = os.path.join(global_dir,"exerciseSets-group_by_movement-2025-07-06.json")

with open(json_fp,'r',encoding='utf-8') as json_file:
    json_data = json.loads(json_file.read())

# print(json_data[0:500])

# JSONPath 表达式
jsonpath_expr = parse('$[*].exerciseSets[*].exercises[*].name')

found_movements = [match.value for match in jsonpath_expr.find(json_data) if match.value is not None]
# print(matches)
# unique_matches = list(dict.fromkeys(found_movements))
unique_movements = set(found_movements)
unique_matches_str= '\n'.join(unique_movements)
print(f'unique_matches:{unique_matches_str}')

def find_exercise_records(exercise_name:str):
    result=[]
    for act in json_data:
        exercise_sets = act.get('exerciseSets')
        if exercise_sets:
            for exercise_set in exercise_sets:
                exercises = exercise_set.get('exercises', [])
                if any(ex.get('name')==exercise_name for ex in exercises):
                    result.append((act.get('activityId'), exercise_set))
                    
    print(f'\n\nbegin to output wrong data for {exercise_name}:')
    for activityId, res in result:
        if 'startTime' not in res or res['startTime'] is None:
            print(f'activityId: {activityId}, res: {res}')
    print(f'ending of output wrong data for {exercise_name}, len(result): {len(result)}')
    
    result_removed_illegal_ones = [(activityId, res) for activityId, res in result if 'startTime' in res and res['startTime'] is not None]
    print(f'len(result_removed_illegal_ones): {len(result_removed_illegal_ones)}')
    
    filtered_result = [
        {
            "duration": res.get("duration"),
            "repetitionCount": res.get("repetitionCount"),
            "weight": res.get("weight"),
            "setType": res.get("setType"),
            "startTime": res.get("startTime"),
            "activityId": activityId,
            "fmtStartTime": datetime.strftime(datetime.strptime(res.get("startTime"),"%Y-%m-%dT%H:%M:%S.0"),"%Y-%m-%d %H:%M:%S"),
            "fmtExerciseDate": datetime.strftime(datetime.strptime(res.get("startTime"),"%Y-%m-%dT%H:%M:%S.0"),"%Y-%m-%d"),
            "fmtMovement":exercise_name
        }
        for activityId, res in result_removed_illegal_ones
    ]
    print(f'len(filtered_result): {len(filtered_result)}')
    return filtered_result

exercise_group_by_date = {}
exercise_volume_stat = {}

for movement in unique_movements:
    found_records = find_exercise_records(movement)
    print(f'movement: {movement}, found_records: {found_records}')
    
    for record in found_records:
        fmtExerciseDate = record["fmtExerciseDate"]
        # print(f'fmtExerciseDate: {fmtExerciseDate}')
        daily_exercise_list = exercise_group_by_date.get(fmtExerciseDate,[])
        if len(daily_exercise_list) == 0:
            exercise_group_by_date[fmtExerciseDate]=daily_exercise_list
        daily_exercise_list.append(record)
        
        fmtMovement = record["fmtMovement"]
        movement_exercise_list = exercise_volume_stat.get(fmtMovement,[])
        if len(movement_exercise_list) == 0:
            exercise_volume_stat[fmtMovement]=movement_exercise_list
        movement_exercise_list.append(record)

# print(f'exercise_group_by_date: {list(exercise_group_by_date.items())[0:3]}')
# print(f'exercise_volume_stat: {list(exercise_volume_stat.items())[0:3]}')

with open(group_by_date_json_fp,'w',encoding='utf-8') as by_date_file:
    by_date_file.write(json.dumps(exercise_group_by_date))
    
with open(group_by_movement_json_fp,'w',encoding='utf-8') as by_movement_file:
    by_movement_file.write(json.dumps(exercise_volume_stat))