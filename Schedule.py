import streamlit as st
import pandas as pd
import re
from collections import Counter

# 設定網頁標題
st.set_page_config(page_title="排班系統")
st.title("Artale炎魔排團")

#==============================================================================
#                             建立上傳按鈕
#==============================================================================
uploaded_file = st.file_uploader("請上傳 Excel 檔案 (Member.xlsx)", type=['xlsx'])

if uploaded_file is not None:
    #==============================================================================
    #                             讀取excel
    #==============================================================================
    st.info(f"正在讀取...")
    df = pd.read_excel(uploaded_file, header=0, usecols="B:F") 
    df = df.fillna('') # Excel 空值填滿
    data = df.to_dict('records')

    st.success(f"成功讀到 {len(data)} 筆資料！")

    #==============================================================================
    #                             定義時間函式
    #==============================================================================
    def timeslots(text):
        text = str(text).replace(" ","")
        day_map = {'一':'一' , '二':'二' , '三':'三' , '四':'四' , '五':'五' , '六':'六' , '日':'日'} 
        all_morning = [10,11]
        all_afternoon = [13,14,15]
        all_night = [21,22,23] 

        result_slots = []
        parts = re.split(r'[,，、]', text)
        for part in parts:
            if not part: continue
            catch_day = []
            for char in part:
                if char in day_map:
                    catch_day.append(day_map[char])
            catch_hour = [int(n) for n in re.findall(r'\d+' , part)]
            if not catch_hour:
                if "早" in part: catch_hour.extend(all_morning)
                if "午" in part: catch_hour.extend(all_afternoon)
                if "晚" in part: catch_hour.extend(all_night)
                
                if not catch_hour: 
                    catch_hour.extend(all_night)

            catch_hour = sorted(list(set(catch_hour)))
            for d in catch_day:
                for h in catch_hour:
                    result_slots.append(f"週{d} {h}:00")
        return result_slots

    #==============================================================================
    #                             資料預處理
    #==============================================================================
    votebox = []
    for p in data:
        p['ID'] = str(p['ID']).strip()
        p['職業'] = str(p['職業']).strip()
        
        raw_lv = str(p.get('等級', '')).replace('.0', '')
        p['Level_Str'] = raw_lv if raw_lv and raw_lv != 'nan' else ''

        try: ticket = int(p.get('場數', 1)) 
        except: ticket = 1
        p['max_ticket'] = 2 if ticket >= 14 else 1

        raw_time = p.get('配合時間', '')
        p['new_slots'] = timeslots(raw_time)
        p['first'] = len(p['new_slots'])
        votebox.extend(p['new_slots'])

    # ==============================================================================
    #                             定義職業
    # ==============================================================================
    Jobs_Magic = ['主教', '冰雷', '火毒']       
    Jobs_DK = ['黑騎士']                      
    Jobs_Archer = ['箭神', '神射手']           
    Jobs_Pirate = ['槍手', '拳霸']             

    necessary_jobs = ['法師', '黑騎士', '弓箭手']
    Max_Magic = 2      
    Max_DK = 1        
    Max_Archer = 99   
    Max_Pirate = 99   
    Max_TeamSize = 6 

    def role_type(job):
        job = str(job).strip()
        if job in Jobs_Magic: return '法師'
        if job in Jobs_DK: return '黑騎士'
        if job in Jobs_Archer: return '弓箭手'
        if job in Jobs_Pirate: return '海盜'
        return '一般輸出'

    #==============================================================================
    #                             決定開團時間
    #==============================================================================
    vote_result = Counter(votebox)
    vote_rank = vote_result.most_common(10) 

    teambox = []
    st.write("### 開團時段")
    
    MAX_TOTAL_TEAMS = 6
    
    for time, count in vote_rank:
        if len(teambox) >= MAX_TOTAL_TEAMS: break
        
        # 判斷人數與職業是否需要開新團
        people_in_this_time = [p for p in data if time in p['new_slots']]
        c_mage = sum(1 for p in people_in_this_time if role_type(p['職業']) == '法師')
        c_dk = sum(1 for p in people_in_this_time if role_type(p['職業']) == '黑騎士')
        
        teams_to_open = 1
        
        # 判斷邏輯: 人數>6 或 法師>2 或 黑騎>1 就要開第2團
        if count > 6 or c_mage > 2 or c_dk > 1:
            teams_to_open = 2
        
        # 判斷邏輯: 人數>12 或 法師>4 或 黑騎>2 就要開第3團
        if count > 12 or c_mage > 4 or c_dk > 2:
            teams_to_open = 3
            
        for i in range(teams_to_open):
            if len(teambox) >= MAX_TOTAL_TEAMS: break
            
            if teams_to_open > 1:
                team_name = f"{time} #{i+1}"
            else:
                team_name = f"{time}"
            
            teambox.append(team_name)
            
        if teams_to_open > 0:
            st.text(f"  - {time} (共有 {count} 人有空)")

    # ==============================================================================
    #                             人員分配邏輯
    # ==============================================================================
    data.sort(key=lambda x: x['first'])
    final_teams = {name: [] for name in teambox}
    entry_times = Counter()  
    entry_qualify = {}       

    def get_raw_time(t):
        return t.split(' #')[0]

    for team_time in teambox:
        raw_time_key = get_raw_time(team_time)
        day_char = raw_time_key[1]
        
        for role in necessary_jobs:
            current_members = final_teams[team_time]
            if any(role_type(m['職業']) == role for m in current_members): continue
            
            for p in data:
                p_id = p['ID']
                if entry_times[p_id] >= p['max_ticket']: continue 
                if raw_time_key not in p['new_slots']: continue
                if day_char in entry_qualify.get(p_id, []): continue 
                
                if role_type(p['職業']) == role:
                    final_teams[team_time].append(p)
                    entry_times[p_id] += 1
                    entry_qualify.setdefault(p_id, []).append(day_char)
                    break 
        
        current_members = final_teams[team_time]
        current_roles = [role_type(m['職業']) for m in current_members]
        
        reserved_slots = 0
        if '黑騎士' not in current_roles: reserved_slots += 1
        if '弓箭手' not in current_roles: reserved_slots += 1
        if '法師' not in current_roles: reserved_slots += 1 
        
        remaining_position = Max_TeamSize - reserved_slots
        
        count_mage = sum(1 for m in current_members if role_type(m['職業']) == '法師')
        count_dk = sum(1 for m in current_members if role_type(m['職業']) == '黑騎士')
        count_archer = sum(1 for m in current_members if role_type(m['職業']) == '弓箭手')
        count_pirate = sum(1 for m in current_members if role_type(m['職業']) == '海盜')
        
        for p in data:
            if len(final_teams[team_time]) >= remaining_position: break
            
            p_id = p['ID']
            if entry_times[p_id] >= p['max_ticket']: continue
            if raw_time_key not in p['new_slots']: continue
            if day_char in entry_qualify.get(p_id, []): continue 
            
            p_role = role_type(p['職業'])
            if p_role == '法師' and count_mage >= Max_Magic: continue
            if p_role == '黑騎士' and count_dk >= Max_DK: continue
            if p_role == '弓箭手' and count_archer >= Max_Archer: continue
            if p_role == '海盜' and count_pirate >= Max_Pirate: continue
                
            final_teams[team_time].append(p)
            entry_times[p_id] += 1
            entry_qualify.setdefault(p_id, []).append(day_char)
            
            if p_role == '法師': count_mage += 1
            elif p_role == '黑騎士': count_dk += 1
            elif p_role == '弓箭手': count_archer += 1
            elif p_role == '海盜': count_pirate += 1

    # ==============================================================================
    # 7. 印出結果
    # ==============================================================================
    st.markdown("---")
    st.write("### 📅 排團結果")

    print_tracker = {} 

    for time, members in final_teams.items():
        # 如果這團沒有人，就不顯示
        if len(members) == 0: continue

        current_roles = [role_type(m['職業']) for m in members]
        c_mage = current_roles.count('法師')
        c_dk = current_roles.count('黑騎士')
        c_arch = current_roles.count('弓箭手')
        
        missing_list = []
        if '黑騎士' not in current_roles: missing_list.append("待補(火)")
        if '弓箭手' not in current_roles: missing_list.append("待補(眼)")
        if '法師' not in current_roles: missing_list.append("待補(法)")
        
        current_total = len(members) + len(missing_list)
        remaining_slots = Max_TeamSize - current_total
        for _ in range(remaining_slots):
            missing_list.append("待補(輸出)")

        st.subheader(f"【{time}】")
        st.text(f"配置: 法{c_mage} / 火{c_dk} / 眼{c_arch} / 輸出")
        
        output_text








