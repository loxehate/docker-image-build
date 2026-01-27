import os
from flask import Flask, render_template, jsonify, request
import ansible_runner

app = Flask(__name__)

# 配置路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLAYBOOK_DIR = os.path.join(BASE_DIR, 'playbooks')
PRIVATE_DATA_DIR = os.path.join(BASE_DIR, 'ansible_data') # 存放执行记录

# 确保目录存在
os.makedirs(PLAYBOOK_DIR, exist_ok=True)
os.makedirs(PRIVATE_DATA_DIR, exist_ok=True)

def get_playbook_list():
    """获取剧本目录下的 yml 文件信息"""
    playbooks = []
    if not os.path.exists(PLAYBOOK_DIR):
        return playbooks
    
    for filename in os.listdir(PLAYBOOK_DIR):
        if filename.endswith(('.yml', '.yaml')):
            playbooks.append({
                "name": filename,
                "author": "System Admin",  # 实际可从文件 metadata 或 Git 获取
                "time": "刚刚",
                "tag": "YAML"
            })
    return playbooks

@app.route('/')
def index():
    playbooks = get_playbook_list()
    return render_template('index.html', playbooks=playbooks)

@app.route('/api/source/<filename>')
def get_source(filename):
    """读取剧本内容"""
    try:
        # 防止目录遍历攻击
        safe_path = os.path.basename(filename)
        path = os.path.join(PLAYBOOK_DIR, safe_path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({"success": True, "content": content})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/run', methods=['POST'])
def run_playbook():
    """异步执行 Ansible 剧本"""
    data = request.json
    playbook_name = data.get('playbook')
    
    if not playbook_name:
        return jsonify({"success": False, "error": "No playbook specified"})

    # 启动异步执行
    # 注意：在生产环境中，你可能需要配置 inventory 路径
    thread, runner = ansible_runner.run_async(
        private_data_dir=PRIVATE_DATA_DIR,
        playbook=os.path.join(PLAYBOOK_DIR, playbook_name),
        extravars={'ansible_connection': 'local'} # 演示用，默认连本地
    )
    
    return jsonify({
        "success": True, 
        "job_id": runner.config.ident,
        "message": f"Job {playbook_name} started"
    })

if __name__ == '__main__':
    # 如果你是 WSL 用户，建议指定 host='0.0.0.0' 以便 Windows 浏览器访问
    app.run(debug=True, host='0.0.0.0', port=5000)