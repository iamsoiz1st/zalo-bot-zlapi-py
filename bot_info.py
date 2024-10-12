import json
import re
from zlapi import ZaloAPI, ZaloAPIException
from threading import Thread
from zlapi.models import *
from datetime import datetime
import time


SETTING_FILE = 'setting.json'
CONFIG_FILE = 'config.json'


def load_message_log():
    """Đọc thông tin tin nhắn từ file settings.json."""
    try:
        with open(SETTING_FILE, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            return settings.get("message_log", {})
    except FileNotFoundError:
        return {}

def save_message_log(message_log):
    """Lưu thông tin tin nhắn vào file settings.json."""
    try:
        with open(SETTING_FILE, 'r', encoding='utf-8') as f:
            settings = json.load(f)
    except FileNotFoundError:
        settings = {}


    settings["message_log"] = message_log
    
    with open(SETTING_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)



def get_content_message(message_object):

    if message_object.msgType == 'chat.sticker':
        return ""
    

    content = message_object.content
    

    if isinstance(content, dict) and 'title' in content:
        
        text_to_check = content['title']
    else:
       
        text_to_check = content if isinstance(content, str) else ""
    return text_to_check

def is_url_in_message(message_object):
 
    if message_object.msgType == 'chat.sticker':
        return False
    
  
    content = message_object.content
    
 
    if isinstance(content, dict) and 'title' in content:

        text_to_check = content['title']
    else:
  
        text_to_check = content if isinstance(content, str) else ""
    

    url_regex = re.compile(
        r'http[s]?://' 
        r'(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|' 
        r'(?:%[0-9a-fA-F][0-9a-fA-F]))+'  
    )
   
    if re.search(url_regex, text_to_check):
        return True
    
    return False


def is_spamming(author_id, thread_id):
    max_messages = 15  
    time_window = 2
    min_interval = 2  
    
    message_log = load_message_log()
    
    key = f"{thread_id}_{author_id}"
    current_time = time.time()
    
    if key in message_log:
        user_data = message_log[key]
        last_message_time = user_data['last_message_time']
        message_times = user_data['message_times']
        
    
        if current_time - last_message_time < min_interval:
       
            recent_messages = [t for t in message_times if current_time - t <= min_interval]
            if len(recent_messages) >= 10:
                return True  
        
    
        message_times = [t for t in message_times if current_time - t <= time_window]
        
 
        message_times.append(current_time)
        
        message_log[key] = {
            'last_message_time': current_time,
            'message_times': message_times
        }
        
       
        if len(message_times) > max_messages:
            return True  
    
    else:
        message_log[key] = {
            'last_message_time': current_time,
            'message_times': [current_time]
        }
    
    save_message_log(message_log)
    
    return False 







def read_settings():
    """Đọc toàn bộ nội dung từ file JSON."""
    try:
        with open(SETTING_FILE, 'r', encoding='utf-8') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def write_settings(settings):
    """Ghi toàn bộ nội dung vào file JSON."""
    with open(SETTING_FILE, 'w', encoding='utf-8') as file:
        json.dump(settings, file, ensure_ascii=False, indent=4)

def load_config():
    """Đọc cấu hình từ file JSON và trả về các giá trị cấu hình."""
    try:
        with open(CONFIG_FILE, 'r') as file:
            config = json.load(file)
            imei = config.get('imei')
            session_cookies = config.get('cookies')
            return imei, session_cookies
    except FileNotFoundError:
        print(f"Error: File {CONFIG_FILE} not found.")
        return None, None
    except json.JSONDecodeError:
        print(f"Error: File {CONFIG_FILE} contains invalid JSON.")
        return None, None

def is_admin(author_id):
    settings = read_settings()
    admin_bot = settings.get("admin_bot", [])
    if author_id in admin_bot:
        return True
    else:
        return False

def handle_self_admin(self):
    settings = read_settings()
    admin_bot = settings.get("admin_bot", [])
    if self.uid not in admin_bot:
        admin_bot.append(self.uid)
        settings['admin_bot'] = admin_bot
        write_settings(settings)
        print(f"Đã thêm 👑{get_user_name_by_id(self, self.uid)} 🆔 {self.uid} cho lần đầu tiên khởi động vào danh sách Admin 🤖self ✅")


def get_allowed_thread_ids():
    """Lấy danh sách các thread ID được phép từ setting.json."""
    settings = read_settings()
    return settings.get('allowed_thread_ids', [])

def self_on_group(self, thread_id):
    """Thêm thread_id vào danh sách được phép."""
    try:
        settings = read_settings()
        allowed_thread_ids = settings.get('allowed_thread_ids', [])
        group = self.fetchGroupInfo(thread_id).gridInfoMap[thread_id]

        if thread_id not in allowed_thread_ids:
            allowed_thread_ids.append(thread_id)
            settings['allowed_thread_ids'] = allowed_thread_ids
            write_settings(settings)

            return f"[🤖self {self.me_name} {self.version}] đã được bật trong Group: {group.name} - ID: {thread_id}\n➜ Gõ lệnh ➡️ /help hoặc /self để xem danh sách tính năng self💡"
    except Exception as e:
        print(f"Error: {e}")
        return "Đã xảy ra lỗi gì đó🤧"

def self_off_group(self, thread_id):
    """Loại bỏ thread_id khỏi danh sách được phép."""
    try:
        settings = read_settings()
        allowed_thread_ids = settings.get('allowed_thread_ids', [])
        group = self.fetchGroupInfo(thread_id).gridInfoMap[thread_id]

        if thread_id in allowed_thread_ids:
            allowed_thread_ids.remove(thread_id)
            settings['allowed_thread_ids'] = allowed_thread_ids
            write_settings(settings)

            return f"[🤖self {self.me_name} {self.version}] đã được tắt trong Group: {group.name} - ID: {thread_id}\n➜ Chào tạm biệt chúc bạn luôn may mắn🍀"
    except Exception as e:
        print(f"Error: {e}")
        return "Đã xảy ra lỗi gì đó🤧"
        
        #soiz
def get_info(self, author_id):
  username = self.fetchUserInfo(author_id).changed_profiles[author_id].displayName
  
  response= f"🔴 Something went wrong\n| Không thể lấy thông tin tài khoản {get_user_name_by_id(self, author_id)}!"
                 
                 
                 #soizz

def add_forbidden_word(word):
    """Thêm một từ vào danh sách từ ngữ cấm."""
    settings = read_settings()
    forbidden_words = settings.get('forbidden_words', [])
    
    if word not in forbidden_words:
        forbidden_words.append(word)
        settings['forbidden_words'] = forbidden_words
        write_settings(settings)
        return f"➜ Từ '{word}' đã được thêm vào danh sách từ cấm ✅"
    else:
        return f"➜ Từ '{word}' đã tồn tại trong danh sách từ cấm 🤧"

def remove_forbidden_word(word):
    """Xóa một từ khỏi danh sách từ ngữ cấm."""
    settings = read_settings()
    forbidden_words = settings.get('forbidden_words', [])
    
    if word in forbidden_words:
        forbidden_words.remove(word)
        settings['forbidden_words'] = forbidden_words
        write_settings(settings)
        return f"➜ Từ '{word}' đã được xóa khỏi danh sách từ cấm ✅"
    else:
        return f"Từ '{word}' không có trong danh sách từ cấm 🤧"

def is_forbidden_word(word):
    """Kiểm tra xem một từ có nằm trong danh sách từ ngữ cấm hay không."""
    settings = read_settings()
    forbidden_words = settings.get('forbidden_words', [])
    return word in forbidden_words



def setup_self_on(self, thread_id):
   
    group = self.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
  
    admin_ids = group.adminIds.copy()
    if group.creatorId not in admin_ids:
        admin_ids.append(group.creatorId)
    
 
    if self.uid in admin_ids:
      
        settings = read_settings()
        
      
        if 'group_admins' not in settings:
            settings['group_admins'] = {}
        
        settings['group_admins'][thread_id] = admin_ids
        
      
        write_settings(settings)
        
        return f"[🤖self {self.me_name} {self.version}]\n➜ Cấu hình thành công nội quy nhóm: {group.name} - ID: {thread_id} ✅\n➜ Hãy nhắn tin một cách văn minh lịch sự! ✨\n➜ Chúc bạn luôn may mắn! 🍀"
    else:
        return f"[🤖self {self.me_name} {self.version}]\n➜ Cấu hình thất bại  cho nhóm: {group.name} - ID: {thread_id} ⚠️\n➜ Bạn không có quyền quản trị nhóm này! 🤧"


def setup_self_off(self,thread_id):
    group = self.fetchGroupInfo(thread_id).gridInfoMap[thread_id]

    settings = read_settings()


    if 'group_admins' in settings:
     
        if thread_id in settings['group_admins']:
     
            del settings['group_admins'][thread_id]

     
            write_settings(settings)
            
            return f"[🤖self {self.me_name} {self.version}]\n➜ Đã hủy bỏ thành công cấu hình quản trị cho nhóm: {group.name} - ID: {thread_id} ✅\n➜ Hãy quẫy lên đi! 🤣"
        else:
            return f"[🤖self {self.me_name} {self.version}]]\n➜ Không tìm thấy cấu hình quản trị cho nhóm: {group.name} - ID: {thread_id} để hủy bỏ! 🤧"
    else:
        return f"[🤖self {self.me_name} {self.version}]\n➜ Không có thông tin quản trị nào trong cài đặt để hủy bỏ! 🤧"

def check_admin_group(self,thread_id):
    group = self.fetchGroupInfo(thread_id).gridInfoMap[thread_id]

    admin_ids = group.adminIds.copy()
    if group.creatorId not in admin_ids:
        admin_ids.append(group.creatorId)
    settings = read_settings()
    if 'group_admins' not in settings:
        settings['group_admins'] = {}
    settings['group_admins'][thread_id] = admin_ids
    

    write_settings(settings)

    if self.uid in admin_ids:
        return True
    else:
        return False


def get_allow_link_status(thread_id):

    settings = read_settings()


    if 'allow_link' in settings:
      
        return settings['allow_link'].get(thread_id, False)
    else:
      
        return False

    

def handle_check_profanity(self, author_id, thread_id, message_object, thread_type, message):
    def send_check_profanity_response():
        settings = read_settings()
        admin_ids = settings.get('group_admins', {}).get(thread_id, [])
        if self.uid not in admin_ids:
            return
        if is_spamming(author_id, thread_id): 
            response=add_users_to_ban_list(self,[author_id],thread_id,"Spam tè le trong nhóm")
            self.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type)
            return
        
        if get_allow_link_status(thread_id) and is_url_in_message(message_object):
            self.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)
            return
       
        
        muted_users = settings.get('muted_users', [])
        for muted_user in muted_users:
            if muted_user['author_id'] == author_id and muted_user['thread_id'] == thread_id:
                self.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)
        if not isinstance(message, str):
            return
        message_text = str(message)
        forbidden_words = settings.get('forbidden_words', [])
        violations = settings.get('violations', {})

        rules = settings.get("rules", {})
        current_time = int(time.time())

        word_rule = rules.get("word", {"threshold": 3, "duration": 30})
        threshold_word = word_rule["threshold"]
        duration_word = word_rule["duration"]

        for muted_user in muted_users:
            if muted_user['author_id'] == author_id and muted_user['thread_id'] == thread_id:
                if current_time >= muted_user['muted_until']:
                    muted_users.remove(muted_user)
                    settings['muted_users'] = muted_users

                    if author_id in violations and thread_id in violations[author_id]:
                        violations[author_id][thread_id]['profanity_count'] = 0

                    write_settings(settings)
                    response = "➜ 🎉 Bạn đã được phép phát ngôn! Hãy nói chuyện 💬 lịch sự nhé! 😊👍"
                    self.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type)
                self.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)
                return


        if any(word.lower() in message_text.lower() for word in forbidden_words):
            user_violations = violations.setdefault(author_id, {}).setdefault(thread_id, {'profanity_count': 0, 'spam_count': 0, 'penalty_level': 0})
            user_violations['profanity_count'] += 1
            profanity_count = user_violations['profanity_count']
            penalty_level = user_violations['penalty_level']

            if penalty_level >= 2:

                response = f"➜ ⛔ Bạn đã bị loại khỏi nhóm do vi phạm nhiều lần\n➜ 💢 Nội dung vi phạm: Sử dụng từ ngữ thô tục: 🤬 '{message_text}'"
                self.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type)
                self.kickUsersInGroup( author_id, thread_id)
                self.blockUsersInGroup( author_id, thread_id)
                

          
                muted_users = [user for user in muted_users if not (user['author_id'] == author_id and user['thread_id'] == thread_id)]
                settings['muted_users'] = muted_users

                if author_id in violations:
                    violations[author_id].pop(thread_id, None)
                    if not violations[author_id]: 
                        violations.pop(author_id, None)

                write_settings(settings)
                return

            if profanity_count >= threshold_word:
                penalty_level += 1
                user_violations['penalty_level'] = penalty_level 

                muted_users.append({
                    'author_id': author_id,
                    'thread_id': thread_id,
                    'reason': f'{message_text}',
                    'muted_until': current_time + 60 * duration_word
                })
                settings['muted_users'] = muted_users
                write_settings(settings)

                response = f"➜ 🚫 Bạn đã vi phạm {threshold_word} lần\n➜ 🤐 Bạn đã bị khóa mõm trong {duration_word} phút\n➜ 💢 Nội dung vi phạm: Sử dụng từ ngữ thô tục: 🤬 '{message_text}'"
                self.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type)
                return
            elif profanity_count == threshold_word - 1:
                response = f"➜ ⚠️ Cảnh báo: Bạn đã vi phạm {profanity_count}/{threshold_word} lần\n➜ 🤐 Nếu bạn tiếp tục vi phạm, bạn sẽ bị khóa mõm trong {duration_word} phút\n➜ 💢 Nội dung vi phạm: Sử dụng từ ngữ thô tục: 🤬 '{message_text}'"
                self.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type)
            else:
                
                response = f"➜ ⚠️ Bạn đã vi phạm {profanity_count}/{threshold_word} lần\n➜ 💢 Nội dung vi phạm: Sử dụng từ ngữ thô tục: 🤬 '{message_text}'"
                self.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type)

            write_settings(settings)  

    thread = Thread(target=send_check_profanity_response)
    thread.start()

def get_user_name_by_id(self,author_id):
    try:
        user = self.fetchUserInfo(author_id).changed_profiles[author_id].zaloName
        return user
    except:
        return "Unknown User"

def get_gender_by_id(self, author_id):
    response = "Gay"  # Initialize response with a default value
    if self.fetchUserInfo(author_id).changed_profiles[author_id].gender == 0:
        response = "Male"
    elif self.fetchUserInfo(author_id).changed_profiles[author_id].gender == 1:
        response = "Female"  # Correctly assign to response
    return response  # Return the final response

def print_muted_users_in_group(self, thread_id):
    settings = read_settings()
    muted_users = settings.get("muted_users", [])
    current_time = int(time.time())
    muted_users_list = []


    for user in muted_users:
        if user['thread_id'] == thread_id:
            author_id = user['author_id']
            user_name = get_user_name_by_id(self, author_id)
            muted_until = user['muted_until']
            remaining_time = muted_until - current_time
            reason = user['reason']

            if remaining_time > 0:
                minutes_left = remaining_time // 60
                muted_users_list.append({
                    "author_id": author_id,
                    "name": user_name,
                    "minutes_left": minutes_left,
                    "reason": reason
                })


    muted_users_list.sort(key=lambda x: x['minutes_left'])

    if muted_users_list:
        result = "➜ 🚫 Danh sách các thành viên nhóm bị khóa mõm: 🤐\n"
        result += "\n".join(f"{i}. 😷 {user['name']} - ⏳ {user['minutes_left']} phút - ⚠️ Lý do: {user['reason']}" 
                            for i, user in enumerate(muted_users_list, start=1))
    else:
        result = "➜ 🎉 Xin chúc mừng!\n➜ Nhóm không có thành viên nào tiêu cực ❤ 🌺 🌻 🌹 🌷 🌼\n➜ Hãy tiếp tục phát huy nhé 🤗"

    return result

def print_blocked_users_in_group(self, thread_id):
    settings = read_settings()
    blocked_users_group = settings.get("block_user_group", {})


    if thread_id not in blocked_users_group:
        return "➜ 🎉 Nhóm này không có ai bị block! 🌟"

    blocked_users = blocked_users_group[thread_id].get('blocked_users', [])
    blocked_users_list = []


    for author_id in blocked_users:
        user_name = get_user_name_by_id(self, author_id)  
        blocked_users_list.append({
            "author_id": author_id,
            "name": user_name
        })


    blocked_users_list.sort(key=lambda x: x['name'])


    if blocked_users_list:
        result = "➜ 🚫 Danh sách các thành viên bị block khỏi nhóm: 🤧\n"
        result += "\n".join(f"{i}. 🙅 {user['name']} - {user['author_id']}" for i, user in enumerate(blocked_users_list, start=1))
    else:
        result = "➜ 🎉 Nhóm không có ai bị block khỏi nhóm! 🌼"

    return result


def add_users_to_ban_list(self, author_ids, thread_id, reason):
    settings = read_settings()

    current_time = int(time.time())
    muted_users = settings.get("muted_users", [])
    violations = settings.get("violations", {})
    duration_minutes = settings.get("rules", {}).get("word", {}).get("duration", 30)

    response=""
    for author_id in author_ids:
        user = self.fetchUserInfo(author_id).changed_profiles[author_id].displayName


        if not any(entry["author_id"] == author_id and entry["thread_id"] == thread_id for entry in muted_users):
            muted_users.append({
                "author_id": author_id,
                "thread_id": thread_id,
                "reason": reason,
                "muted_until": current_time + 60 * duration_minutes
            })


        if author_id not in violations:
            violations[author_id] = {}

        if thread_id not in violations[author_id]:
            violations[author_id][thread_id] = {
                "profanity_count": 0,
                "spam_count": 0,
                "penalty_level": 0
            }

        violations[author_id][thread_id]["profanity_count"] += 1  
        violations[author_id][thread_id]["penalty_level"] += 1 

        response += f"➜ 🚫 {user} đã bị cấm phát ngôn trong {duration_minutes} ⏳ phút\n"
    

    settings['muted_users'] = muted_users
    settings['violations'] = violations
    write_settings(settings)
    return response


def remove_users_from_ban_list(self, author_ids, thread_id):
    settings = read_settings()

    muted_users = settings.get("muted_users", [])
    violations = settings.get("violations", {})

    response = ""
    for author_id in author_ids:
        user = self.fetchUserInfo(author_id).changed_profiles[author_id].displayName

  
        initial_count = len(muted_users)
        muted_users = [entry for entry in muted_users if not (entry["author_id"] == author_id and entry["thread_id"] == thread_id)]
        

        removed = False
        if author_id in violations:
            if thread_id in violations[author_id]:
                del violations[author_id][thread_id]

                if not violations[author_id]:
                    del violations[author_id]
                removed = True

   
        if (initial_count != len(muted_users)) or removed:
            response += f"➜ 🎉 Chúc mừng {user} đã được phép phát ngôn 😤\n"
        else:
            response += f"➜ 😲 {user} không có trong danh sách cấm phát ngôn 🤧\n"
    
    
    settings['muted_users'] = muted_users
    settings['violations'] = violations
    write_settings(settings)

    return response

def block_users_from_group(self, author_ids, thread_id):
    response = ''
    block_user = [] 

   
    settings = read_settings()

 
    if "block_user_group" not in settings:
        settings["block_user_group"] = {}


    if thread_id not in settings["block_user_group"]:
        settings["block_user_group"][thread_id] = {'blocked_users': []}

    for author_id in author_ids:
    
        user = self.fetchUserInfo(author_id).changed_profiles[author_id].displayName

       
        self.blockUsersInGroup(author_id, thread_id)  
        block_user.append(user) 

 
        if author_id not in settings["block_user_group"][thread_id]['blocked_users']:
            settings["block_user_group"][thread_id]['blocked_users'].append(author_id)

  
    write_settings(settings)


    if block_user:
        blocked_users_str = ', '.join(block_user)  
        response = f"➜ :v {blocked_users_str} đã bị chặn khỏi nhóm 🤧"
    else:
        response = "➜ Không ai bị chặn khỏi nhóm 🤧"
    
    return response

def unblock_users_from_group(self, author_ids, thread_id):
    response = ''
    unblocked_users = [] 

 
    settings = read_settings()


    if "block_user_group" in settings and thread_id in settings["block_user_group"]:
        blocked_users = settings["block_user_group"][thread_id]['blocked_users']
        
        for author_id in author_ids:
      
            user = self.fetchUserInfo(author_id).changed_profiles[author_id].displayName

     
            if author_id in blocked_users:
                self.unblockUsersInGroup(author_id, thread_id) 
                unblocked_users.append(user)  
                blocked_users.remove(author_id)  

       
        if not blocked_users:
            del settings["block_user_group"][thread_id]
        
       
        write_settings(settings)


    if unblocked_users:
        unblocked_users_str = ', '.join(unblocked_users)  
        response = f"➜ :v {unblocked_users_str} đã được bỏ chặn khỏi nhóm 🎉"
    else:
        response = "➜ Không có ai bị chặn trong nhóm 🤧"
    
    return response



def kick_users_from_group(self, uids, thread_id):
    response = ""
    for uid in uids:
        try:
        
            self.kickUsersInGroup(uid, thread_id)
            self.blockUsersInGroup( uid, thread_id)
     
            user_name = get_user_name_by_id(self, uid)
         
            response += f"➜ 💪 Đã kick người dùng 😫 {user_name} khỏi nhóm thành công ✅\n"
        except Exception as e:
           
            user_name = get_user_name_by_id(self, uid)
            response += f"➜ 😲 Không thể kick người dùng 😫 {user_name} khỏi nhóm 🤧\n"
    
    return response




def extract_uids_from_mentions(message_object):
    uids = []
    if message_object.mentions:
      
        uids = [mention['uid'] for mention in message_object.mentions if 'uid' in mention]
    return uids


def add_admin(self, author_id, mentioned_uids, settings):
    admin_bot = settings.get("admin_bot", [])
    response = ""
    for uid in mentioned_uids:
        if author_id not in admin_bot:
            response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
        elif uid not in admin_bot:
            admin_bot.append(uid)
            response += f"➜ Đã thêm người dùng 👑 {get_user_name_by_id(self, uid)} vào danh sách Admin 🤖self ✅\n"
        else:
            response += f"➜ Người dùng 👑 {get_user_name_by_id(self, uid)} đã có trong danh sách Admin 🤖self 🤧\n"

    settings['admin_bot'] = admin_bot
    write_settings(settings)
    return response

def remove_admin(self, author_id, mentioned_uids, settings):
    admin_bot = settings.get("admin_bot", [])
    response = ""
    for uid in mentioned_uids:
        if author_id not in admin_bot:
            response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
        elif uid in admin_bot:
            admin_bot.remove(uid)
            response += f"➜ Đã xóa người dùng 👑 {get_user_name_by_id(self, uid)} khỏi danh sách Admin 🤖self ✅\n"
        else:
            response += f"➜ Người dùng 👑 {get_user_name_by_id(self, uid)} không có trong danh sách Admin 🤖self 🤧\n"

    settings['admin_bot'] = admin_bot
    write_settings(settings)
    return response

# Xử lý lệnh self
def handle_self_command(self, message_object, author_id, thread_id, thread_type,command):
    def send_self_response():
        try:
            parts = message_object.content.split()
            if len(parts) == 1:
                response = (
                    "🎉 Chào mừng đến với menu 🤖self! ⚙️\n"
                    "   ➜ !help info: ♨️ Xem thông tin chi tiết về self\n"
                    "   ➜ /self on/off: 🚀 Bật/ 🛑 Tắt self trong Group (OA)\n"
                    "   ➜ /self admin add/remove/list: 👑 Thêm/xóa/xem danh sách Admin 🤖self\n"
                    "   ➜ /self noiquy: 💢 Nội quy Group\n"
                    "   ➜ /self ban/unban list: 🚫 Danh sách/ 😷 Khóa / 😘 Mở mỗm người dùng\n"
                    "   ➜ /self kick: 💪 Kick người dùng ra khỏi nhóm(OA)\n"
                    "   ➜ /self block/unblock/list: 💪 Chặn người dùng khỏi nhóm(OA)\n"
                    "   ➜ /self setup on/off: ⚙️ Bật/Tắt nội quy nội quy self (OA)\n"
                    "   ➜ /self link on/off: 🔗 Bật/Tắt cho phép gởi link nhóm (OA)\n"
                    "   ➜ /self rule word [n] [m]: 📖 Quy định cấm n lần vi phạm, phạt m phút (OA)\n"
                    "   ➜ /self word add/remove [từ cấm]: ✍️ Thêm/xóa từ ngữ cấm (OA)\n"
                    "🤖 self luôn sẵn sàng phục vụ bạn! 🌸"
                )

            else:
                action = parts[1].lower()
                if action == 'on':
                    if not is_admin(author_id):
                        response = "➜ Lệnh này chỉ khả thi với Admin 🤧"
                    elif thread_type != ThreadType.GROUP:
                        response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                    else:
                        response = self_on_group(self, thread_id)
                elif action == 'off':
                    if not is_admin(author_id):
                        response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
                    elif thread_type != ThreadType.GROUP:
                        response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                    else:
                        response = self_off_group(self, thread_id)
                elif action == 'info':
                    response = f" • ID: {self.fetchUserInfo(author_id).changed_profiles[author_id].userId}\n• Name: {get_user_name_by_id(self, author_id)}\n• Bio: {self.fetchUserInfo(author_id).changed_profiles[author_id].status}\n• Business: {self.fetchUserInfo(author_id).changed_profiles[author_id].bizPkg.label}\n• Giới tính: {get_gender_by_id(self, author_id)}\n• Sinh nhật: {self.fetchUserInfo(author_id).changed_profiles[author_id].dobs}\n• Số điện thoại: {self.fetchUserInfo(author_id).changed_profiles[author_id].phoneNumber}\n• Tham gia Zalo từ: {self.fetchUserInfo(author_id).changed_profiles[author_id].createdTs}\n"
                    
                    
                elif action == 'admin':
                    if len(parts) < 3:
                        response = "➜ Vui lòng nhập [list/add/remove] sau lệnh: /self admin 🤧\n➜ Ví dụ: /self admin list hoặc /self admin add @Soiz hoặc /self admin remove @Soiz ✅"
                    else:
                        settings = read_settings()
                        admin_bot = settings.get("admin_bot", [])  
                        sub_action = parts[2].lower()
                        if sub_action == 'add':
                            if len(parts) < 4:
                                response = "➜ Vui lòng @tag tên người dùng sau lệnh: /self admin add 🤧\n➜ Ví dụ: /self admin add @Soiz ✅"
                            else:
                                if author_id not in admin_bot:
                                    response = "➜ Lệnh này chỉ khả thi với Admin 🤧"
                                else:
                                    mentioned_uids = extract_uids_from_mentions(message_object)
                                    response = add_admin(self, author_id, mentioned_uids, settings)
                        elif sub_action == 'remove':
                            if len(parts) < 4:
                                response = "➜ Vui lòng @tag tên người dùng sau lệnh: /self admin remove 🤧\n➜ Ví dụ: /self admin remove @Soiz ✅"
                            else:
                                if author_id not in admin_bot:
                                    response = "➜ Lệnh này chỉ khả thi với Admin 🤧"
                                else:
                                    mentioned_uids = extract_uids_from_mentions(message_object)
                                    response = remove_admin(self, author_id, mentioned_uids, settings)
                        elif sub_action == 'list':
                            if admin_bot:
                                response = "➜ 🛡️ Danh sách Admin self 👑\n"
                                for idx, uid in enumerate(admin_bot, start=1):
                                    response += f"      ➜ {idx}. 👑 {get_user_name_by_id(self, uid)}\n"
                            else:
                                response = "➜ Không có Admin self nào trong danh sách 🤧"
                        else:
                            response = f"➜ Lệnh /self admin {sub_action} không được hỗ trợ 🤧"


                elif action == 'setup':
                    if len(parts) < 3:
                        response = "➜ Vui lòng nhập [on/off] sau lệnh: /self setup 🤧\n➜ Ví dụ: /self setup on hoặc /self setup off ✅"
                    else:
                        setup_action = parts[2].lower()
                        if setup_action == 'on':
                            if not is_admin(author_id):
                                response = "➜ Lệnh này chỉ khả thi với Admin 🤧"
                            elif thread_type != ThreadType.GROUP:
                                response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                            else:
                                response = setup_self_on(self, thread_id)
                        elif setup_action == 'off':
                            if not is_admin(author_id):
                                response = "➜ Lệnh này chỉ khả thi với Admin 🤧"
                            elif thread_type != ThreadType.GROUP:
                                response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                            else:
                                response = setup_self_off(self,thread_id)
                        else:
                            response = f"➜ Lệnh /self setup {setup_action} không được hỗ trợ 🤧"
                elif action == 'link':
                    if len(parts) < 3:
                        response = "➜ Vui lòng nhập [on/off] sau lệnh: /self link 🤧\n➜ Ví dụ: /self link on hoặc /self link off ✅"
                    else:
                        link_action = parts[2].lower()
                        if not is_admin(author_id):
                            response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
                        elif thread_type != ThreadType.GROUP:
                            response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                        else:
                            settings = read_settings()

                            if 'allow_link' not in settings:
                                settings['allow_link'] = {}

                            
                            if link_action == 'on':
                                settings['allow_link'][thread_id] = True
                                response = "➜ Tùy chọn cho phép gởi link 🔗 đã được bật 🟢 cho nhóm này ✅"
                            elif link_action == 'off':
                                settings['allow_link'][thread_id] = False
                                response = "➜ Tùy chọn cho phép gởi link 🔗 đã được tắt 🔴 cho nhóm này ✅"
                            else:
                                response = f"➜ Lệnh /self link {link_action} không được hỗ trợ 🤧"
                        write_settings(settings)
                elif action == 'word':
                    if len(parts) < 4:
                        response = "➜ Vui lòng nhập [add/reomve] [từ khóa] sau lệnh: /self word 🤧\n➜ Ví dụ: /self word add [từ khóa] hoặc /self word remove [từ khóa] ✅"
                    else:
                        if not is_admin(author_id):
                            response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
                        elif thread_type != ThreadType.GROUP:
                            response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                        else:
                            word_action = parts[2].lower()
                            word = ' '.join(parts[3:]) 
                            if word_action == 'add':
                                response = add_forbidden_word(word)
                            elif word_action == 'remove':
                                response = remove_forbidden_word(word)
                            else:
                                response = f"➜ Lệnh [/self word {word_action}] không được hỗ trợ 🤧\n➜ Ví dụ: /self word add [từ khóa] hoặc /self word remove [từ khóa] ✅"
                elif action == 'noiquy':
                    settings = read_settings()
                    rules=settings.get("rules", {})
                    word_rule = rules.get("word", {"threshold": 3, "duration": 30})
                    threshold_word = word_rule["threshold"]
                    duration_word = word_rule["duration"]
                    group_admins = settings.get('group_admins', {})
                    admins = group_admins.get(thread_id, [])
                    group = self.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
                    if admins:
                        response = (
                            f"➜ 💢 Nội quy 🤖self {self.me_name} được áp dụng cho nhóm: {group.name} - ID: {thread_id} ✅\n"
                            f"➜ 🚫 Cấm sử dụng các từ ngữ thô tục 🤬 trong nhóm\n"
                            f"➜ 💢 Vi phạm {threshold_word} lần sẽ bị 😷 khóa mõm {duration_word} phút\n"
                            f"➜ ⚠️ Nếu tái phạm 2 lần sẽ bị 💪 kick khỏi nhóm 🤧"
                        )
                    else:
                        response = (
                            f"➜ 💢 Nội quy không áp dụng cho nhóm: {group.name} - ID: {thread_id} 💔\n➜ Lý do: 🤖self {self.me_name} chưa được setup hoặc Self không có quyền cầm key quản trị nhóm 🤧"
                        )
                elif action == 'ban':
                    
                    if len(parts) < 3:
                        response = "➜ Vui lòng nhập list hoặc ban @tag tên sau lệnh: /self 🤧\n➜ Ví dụ: /self list hoặc /self ban @Heoder ✅"
                    else:
                        s_action = parts[2] 
                        
                        if s_action == 'list':
                            response = print_muted_users_in_group(self, thread_id)
                        else:
                            
                            if not is_admin(author_id):
                                response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
                            elif thread_type != ThreadType.GROUP:
                                response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                            elif check_admin_group(self,thread_id)==False:
                                response = "➜ Lệnh này không khả thi do 🤖self không có quyền cầm 🔑 key nhóm 🤧"
                            else:
                               
                                uids = extract_uids_from_mentions(message_object)
                                response = add_users_to_ban_list(self, uids, thread_id,"Quản trị viên cấm")

                elif action == 'unban':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập @tag tên sau lệnh: /self unban 🤧\n➜ Ví dụ: /self unban @Soiz ✅"
                    else:
                        if not is_admin(author_id):
                            response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
                        elif thread_type != ThreadType.GROUP:
                            response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                        else:
                            
                            uids = extract_uids_from_mentions(message_object)
                            response = remove_users_from_ban_list(self, uids, thread_id)
                elif action == 'block':
                      
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập @tag tên sau lệnh: /self block 🤧\n➜ Ví dụ: /self block @Soiz ✅"
                    else:
                        s_action = parts[2]  
                      
                        if s_action == 'list':
                            response = print_blocked_users_in_group(self, thread_id)
                        else:
                         
                            if not is_admin(author_id):
                                response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
                            elif thread_type != ThreadType.GROUP:
                                response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                            elif check_admin_group(self,thread_id)==False:
                                response = "➜ Lệnh này không khả thi do 🤖self không có quyền cầm 🔑 key nhóm 🤧"
                            else:
                              
                                uids = extract_uids_from_mentions(message_object)
                                response = block_users_from_group(self, uids, thread_id)

                elif action == 'unblock':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập UID sau lệnh: /self unblock 🤧\n➜ Ví dụ: /self unblock 8421834556970988033, 842183455697098804... ✅"
                    else:
                        if not is_admin(author_id):
                            response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
                        elif thread_type != ThreadType.GROUP:
                            response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                        else:
                           
                            ids_str = parts[2]  
                            print(f"Chuỗi UIDs: {ids_str}")

                            uids = [uid.strip() for uid in ids_str.split(',') if uid.strip()]
                            print(f"Danh sách UIDs: {uids}")

                            
                            if uids:
                              
                                response = unblock_users_from_group(self, uids, thread_id)
                            else:
                                response = "➜ Không có UID nào hợp lệ để bỏ chặn 🤧"

                elif action == 'kick':
                    if len(parts) < 3:
                        response = f"➜ Vui lòng nhập @tag tên sau lệnh: /self kick 🤧\n➜ Ví dụ: /self kick @Heoder ✅"
                    else:
                        if not is_admin(author_id):
                            response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
                        elif thread_type != ThreadType.GROUP:
                            response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                        elif check_admin_group(self,thread_id)==False:
                                response = "➜ Lệnh này không khả thi do 🤖self không có quyền cầm 🔑 key nhóm 🤧"
                        else:
                            uids = extract_uids_from_mentions(message_object)
                            response = kick_users_from_group(self, uids, thread_id)

                elif action == 'rule':
                    if len(parts) < 5:
                        response = "➜ Vui lòng nhập word [n lần] [m phút] sau lệnh: /self rule 🤧\n➜ Ví dụ: /self rule word 3 30 ✅"
                    else:
                        rule_type = parts[2].lower()
                        try:
                            threshold = int(parts[3])
                            duration = int(parts[4])
                        except ValueError:
                            response = "➜ Số lần và phút phạt phải là số nguyên 🤧"
                        else:
                            settings = read_settings()
                            if rule_type not in ["word", "spam"]:
                                response = f"➜ Lệnh /self rule {rule_type} không được hỗ trợ 🤧\n➜ Ví dụ: /self rule word 3 30✅"
                            else:
                                if not is_admin(author_id):
                                    response = "➜ Lệnh này chỉ khả thi với chủ nhân 🤧"
                                elif thread_type != ThreadType.GROUP:
                                    response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                                else:
                                    settings.setdefault("rules", {})
                                    settings["rules"][rule_type] = {
                                        "threshold": threshold,
                                        "duration": duration
                                    }
                                    write_settings(settings)
                                    response = f"➜ 🔄 Đã cập nhật nội quy cho {rule_type}: Nếu vi phạm {threshold} lần sẽ bị phạt {duration} phút ✅"
                else:
                    response = f"➜ Lệnh [/self {action}] không được hỗ trợ 🤧"
            
            if response:
                self.replyMessage(Message(text=f"{response}"), message_object, thread_id=thread_id, thread_type=thread_type)
        
        except Exception as e:
            print(f"Error: {e}")
            self.replyMessage(Message(text="➜ 🐞 Đã xảy ra lỗi gì đó 🤧"), message_object, thread_id=thread_id, thread_type=thread_type)

    thread = Thread(target=send_self_response)
    thread.start()

class Client(ZaloAPI):
    def __init__(self, api_key, secret_key, imei, session_cookies):
        super().__init__(api_key, secret_key, imei=imei, session_cookies=session_cookies)
        self.version = 1.1
        self.me_name = "Bot by Soiz"
        self.date_update = "26/9/2024"

    def onMessage(self, mid, author_id, message, message_object, thread_id, thread_type):
        if isinstance(message,str) and message_object.content.startswith("//"): #Soiz: /self -> //
            command =message_object.content
            handle_self_command(self,message_object, author_id, thread_id, thread_type, command)

imei = "038366e2-c323-47f8-b250-d196e14d1420-16453d6e2683b8800ded2a27c7f595d9"
session_cookies ={'_ga': 'GA1.2.903196771.1728571096', '_gid': 'GA1.2.797667413.1728571096', '_zlang': 'vn', 'zpsid': '89NB.423101413.0.3a-Lm5Ks27omDJ1bMJO8V215UaXd1JbCP08vJtgsuTsIz1rHL4FXUp8s27m', 'zpw_sek': 'dqPI.423101413.a0.XWYQT-wpi-KBi8lypxEpvPMHrexCYP6zeyk5iC67mPISoi3NdUJHhwVZXQw_Zex7avmp34zqSV33iiKCwTIpvG', '__zi': '3000.SSZzejyD6zOgdh2mtnLQWYQN_RAG01ICFjIXe9fEM8WyckoacKbOYt6VwgNTJLY8Vfpgh3Cn.1', '__zi-legacy': '3000.SSZzejyD6zOgdh2mtnLQWYQN_RAG01ICFjIXe9fEM8WyckoacKbOYt6VwgNTJLY8Vfpgh3Cn.1', 'app.event.zalo.me': '6417841313632871577'}
client = Client('api_key', 'secret_key', imei=imei, session_cookies=session_cookies)
client.listen(delay=0)