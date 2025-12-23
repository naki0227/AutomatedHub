#!/usr/bin/env python3
"""
Enludus Automation Hub - Web Dashboard
ブラウザからワンボタンで自動化タスクを実行
"""
import subprocess
import threading
from pathlib import Path
from flask import Flask, render_template_string, jsonify, request
import sys
import os

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

app = Flask(__name__)

# 実行中のタスク管理
running_tasks = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 Enludus Automation Hub</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 2rem;
        }
        .container { max-width: 800px; margin: 0 auto; }
        h1 {
            text-align: center;
            font-size: 2rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(90deg, #00d4ff, #7c3aed);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle {
            text-align: center;
            color: #888;
            margin-bottom: 2rem;
        }
        .section {
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .section-title {
            font-size: 1.1rem;
            color: #00d4ff;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .btn-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
        }
        .btn {
            padding: 1rem 1.5rem;
            border: none;
            border-radius: 12px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.5rem;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,0,0,0.3); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .btn-morning { background: linear-gradient(135deg, #ff9500, #ff6b00); color: #fff; }
        .btn-afternoon { background: linear-gradient(135deg, #00d4ff, #0099ff); color: #fff; }
        .btn-evening { background: linear-gradient(135deg, #7c3aed, #5b21b6); color: #fff; }
        .btn-generate { background: linear-gradient(135deg, #10b981, #059669); color: #fff; }
        .btn-post { background: linear-gradient(135deg, #ef4444, #dc2626); color: #fff; }
        .btn-trends { background: linear-gradient(135deg, #f59e0b, #d97706); color: #fff; }
        .btn span.icon { font-size: 1.5rem; }
        .btn span.label { font-size: 0.85rem; }
        .input-group {
            display: flex;
            gap: 1rem;
            margin-bottom: 1rem;
        }
        input[type="text"] {
            flex: 1;
            padding: 0.75rem 1rem;
            border: 2px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            background: rgba(255,255,255,0.05);
            color: #fff;
            font-size: 1rem;
        }
        input[type="text"]:focus {
            outline: none;
            border-color: #00d4ff;
        }
        #output {
            background: #0d1117;
            border-radius: 8px;
            padding: 1rem;
            font-family: 'Menlo', 'Monaco', monospace;
            font-size: 0.85rem;
            max-height: 400px;
            overflow-y: auto;
            white-space: pre-wrap;
            color: #c9d1d9;
        }
        .status { text-align: center; padding: 0.5rem; color: #888; }
        .status.running { color: #00d4ff; }
        .status.success { color: #10b981; }
        .status.error { color: #ef4444; }
        .loading { animation: pulse 1s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Enludus Automation Hub</h1>
        <p class="subtitle">学びを冒険に。壁を、扉に。</p>

        <div class="section">
            <div class="section-title">📅 日次ルーティン</div>
            <div class="btn-grid">
                <button class="btn btn-morning" onclick="runTask('morning')">
                    <span class="icon">🌅</span>
                    <span class="label">朝ルーティン</span>
                </button>
                <button class="btn btn-afternoon" onclick="runTask('afternoon')">
                    <span class="icon">☀️</span>
                    <span class="label">昼ルーティン</span>
                </button>
                <button class="btn btn-evening" onclick="runTask('evening')">
                    <span class="icon">🌙</span>
                    <span class="label">夜ルーティン</span>
                </button>
            </div>
        </div>

        <div class="section">
            <div class="section-title">💡 コンテンツアイデア</div>
            <div class="btn-grid">
                <button class="btn btn-generate" onclick="generateIdeas()">
                    <span class="icon">💡</span>
                    <span class="label">ネタ提案（5件）</span>
                </button>
                <button class="btn btn-evening" onclick="weeklyPlan()">
                    <span class="icon">📅</span>
                    <span class="label">週間プラン</span>
                </button>
            </div>
        </div>

        <div class="section">
            <div class="section-title">📝 テキスト配信（note無料/有料 → X画像+リプ → Instagram）</div>
            <div class="btn-grid">
                <button class="btn btn-post" onclick="publishAll()" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                    <span class="icon">🚀</span>
                    <span class="label">一括投稿（生成→note→X→Instagram）</span>
                </button>
            </div>
            <div class="btn-grid" style="margin-top: 0.5rem;">
                <button class="btn btn-morning" onclick="createEnhancedContent()">
                    <span class="icon">📰</span>
                    <span class="label">生成のみ</span>
                </button>
                <button class="btn btn-trends" onclick="runTask('trends')">
                    <span class="icon">📊</span>
                    <span class="label">トレンド確認</span>
                </button>
            </div>
        </div>

        <div class="section">
            <div class="section-title">🎬 動画配信（YouTube・TikTok）</div>
            <div class="input-group">
                <input type="text" id="video_path" placeholder="動画パス... 例: /path/to/video.mp4">
            </div>
            <div class="btn-grid">
                <button class="btn btn-afternoon" onclick="createVideoContent()">
                    <span class="icon">🎬</span>
                    <span class="label">動画編集・メタデータ生成</span>
                </button>
            </div>
        </div>

        <div class="section">
            <div class="section-title">📤 投稿管理</div>
            <div class="btn-grid">
                <button class="btn btn-post" onclick="runTask('drafts')">
                    <span class="icon">📝</span>
                    <span class="label">下書き一覧</span>
                </button>
            </div>
        </div>

        <div class="section">
            <div class="section-title">📖 note投稿</div>
            <div class="input-group">
                <input type="text" id="note_topic" placeholder="note記事トピック... 例: Encura開発日記">
            </div>
            <div class="btn-grid">
                <button class="btn btn-generate" onclick="postNote()">
                    <span class="icon">📖</span>
                    <span class="label">記事生成・投稿</span>
                </button>
                <button class="btn btn-trends" onclick="runTask('note_login')">
                    <span class="icon">🔐</span>
                    <span class="label">noteログイン</span>
                </button>
            </div>
        </div>

        <div class="section">
            <div class="section-title">🎬 動画編集</div>
            <div class="input-group">
                <input type="text" id="video_path" placeholder="動画パス... 例: /path/to/video.mp4">
                <select id="video_genre" style="padding: 0.75rem; border-radius: 8px; background: rgba(255,255,255,0.05); color: #fff; border: 2px solid rgba(255,255,255,0.1);">
                    <option value="auto">自動検出</option>
                    <option value="tech">Tech</option>
                    <option value="vlog">Vlog</option>
                    <option value="gaming">Gaming</option>
                    <option value="education">Education</option>
                    <option value="short">Short</option>
                </select>
            </div>
            <div class="btn-grid">
                <button class="btn btn-generate" onclick="editVideo()">
                    <span class="icon">🎬</span>
                    <span class="label">動画編集</span>
                </button>
            </div>
        </div>

        <div class="section">
            <div class="section-title">📟 出力</div>
            <div id="status" class="status">待機中...</div>
            <div id="output">ここに実行結果が表示されます</div>
        </div>
    </div>

    <script>
        async function runTask(task) {
            setStatus('running', '実行中...');
            clearOutput();
            try {
                const res = await fetch('/run/' + task, { method: 'POST' });
                const data = await res.json();
                setOutput(data.output);
                setStatus(data.success ? 'success' : 'error', 
                         data.success ? '完了!' : 'エラー');
            } catch (e) {
                setOutput('Error: ' + e.message);
                setStatus('error', 'エラー');
            }
        }

        async function generateIdeas() {
            setStatus('running', 'ネタ提案中...');
            clearOutput();
            try {
                const res = await fetch('/generate_ideas', { method: 'POST' });
                const data = await res.json();
                setOutput(data.output);
                setStatus(data.success ? 'success' : 'error',
                         data.success ? 'アイデア生成完了!' : 'エラー');
            } catch (e) {
                setOutput('Error: ' + e.message);
                setStatus('error', 'エラー');
            }
        }

        async function weeklyPlan() {
            setStatus('running', '週間プラン生成中...');
            clearOutput();
            try {
                const res = await fetch('/weekly_plan', { method: 'POST' });
                const data = await res.json();
                setOutput(data.output);
                setStatus(data.success ? 'success' : 'error',
                         data.success ? '週間プラン生成完了!' : 'エラー');
            } catch (e) {
                setOutput('Error: ' + e.message);
                setStatus('error', 'エラー');
            }
        }

        async function autoDetect() {
            setStatus('running', '変更検知中...');
            clearOutput();
            try {
                const res = await fetch('/auto_detect', { method: 'POST' });
                const data = await res.json();
                setOutput(data.output);
                setStatus(data.success ? 'success' : 'error',
                         data.success ? '自動検知完了!' : '変更なし');
            } catch (e) {
                setOutput('Error: ' + e.message);
                setStatus('error', 'エラー');
            }
        }

        async function publishAll() {
            setStatus('running', '一括投稿中（生成→note→X→Instagram）...');
            clearOutput();
            try {
                const res = await fetch('/publish_all', { method: 'POST' });
                const data = await res.json();
                setOutput(data.output);
                setStatus(data.success ? 'success' : 'error',
                         data.success ? '一括投稿完了!' : '一部失敗');
            } catch (e) {
                setOutput('Error: ' + e.message);
                setStatus('error', 'エラー');
            }
        }

        async function createEnhancedContent() {
            setStatus('running', '拡張コンテンツ生成中（note無料/有料 → X → Instagram）...');
            clearOutput();
            try {
                const res = await fetch('/create_enhanced_content', { method: 'POST' });
                const data = await res.json();
                setOutput(data.output);
                setStatus(data.success ? 'success' : 'error',
                         data.success ? '拡張コンテンツ生成完了!' : 'エラー');
            } catch (e) {
                setOutput('Error: ' + e.message);
                setStatus('error', 'エラー');
            }
        }

        async function createVideoContent() {
            const videoPath = document.getElementById('video_path').value;
            if (!videoPath) {
                alert('動画パスを入力してください');
                return;
            }
            setStatus('running', '動画編集・メタデータ生成中...');
            clearOutput();
            try {
                const res = await fetch('/create_video_content', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ video_path: videoPath })
                });
                const data = await res.json();
                setOutput(data.output);
                setStatus(data.success ? 'success' : 'error',
                         data.success ? '動画コンテンツ生成完了!' : 'エラー');
            } catch (e) {
                setOutput('Error: ' + e.message);
                setStatus('error', 'エラー');
            }
        }

        async function generateContent() {
            const topic = document.getElementById('topic').value;
            if (!topic) {
                alert('トピックを入力してください');
                return;
            }
            setStatus('running', 'コンテンツ生成中...');
            clearOutput();
            try {
                const res = await fetch('/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ topic })
                });
                const data = await res.json();
                setOutput(data.output);
                setStatus(data.success ? 'success' : 'error',
                         data.success ? '生成完了!' : 'エラー');
            } catch (e) {
                setOutput('Error: ' + e.message);
                setStatus('error', 'エラー');
            }
        }

        async function generateConnected() {
            const topic = document.getElementById('topic').value;
            if (!topic) {
                alert('トピックを入力してください');
                return;
            }
            setStatus('running', '連携コンテンツ生成中...');
            clearOutput();
            try {
                const res = await fetch('/generate_connected', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ topic })
                });
                const data = await res.json();
                setOutput(data.output);
                setStatus(data.success ? 'success' : 'error',
                         data.success ? '連携コンテンツ生成完了!' : 'エラー');
            } catch (e) {
                setOutput('Error: ' + e.message);
                setStatus('error', 'エラー');
            }
        }

        async function postNote() {
            const topic = document.getElementById('note_topic').value;
            if (!topic) {
                alert('トピックを入力してください');
                return;
            }
            setStatus('running', 'note記事生成中...');
            clearOutput();
            try {
                const res = await fetch('/note_post', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ topic })
                });
                const data = await res.json();
                setOutput(data.output);
                setStatus(data.success ? 'success' : 'error',
                         data.success ? 'note投稿完了!' : 'エラー');
            } catch (e) {
                setOutput('Error: ' + e.message);
                setStatus('error', 'エラー');
            }
        }

        async function editVideo() {
            const videoPath = document.getElementById('video_path').value;
            const genre = document.getElementById('video_genre').value;
            if (!videoPath) {
                alert('動画パスを入力してください');
                return;
            }
            setStatus('running', '動画編集中...');
            clearOutput();
            try {
                const res = await fetch('/edit_video', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ video_path: videoPath, genre: genre })
                });
                const data = await res.json();
                setOutput(data.output);
                setStatus(data.success ? 'success' : 'error',
                         data.success ? '動画編集完了!' : 'エラー');
            } catch (e) {
                setOutput('Error: ' + e.message);
                setStatus('error', 'エラー');
            }
        }

        function setStatus(type, text) {
            const el = document.getElementById('status');
            el.className = 'status ' + type;
            el.textContent = text;
        }

        function setOutput(text) {
            document.getElementById('output').textContent = text;
        }

        function clearOutput() {
            document.getElementById('output').textContent = '実行中...';
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/run/<task>', methods=['POST'])
def run_task(task):
    """タスクを実行"""
    commands = {
        'morning': ['python', 'scripts/daily_routine.py', 'morning'],
        'afternoon': ['python', 'scripts/daily_routine.py', 'afternoon'],
        'evening': ['python', 'scripts/daily_routine.py', 'evening'],
        'trends': ['python', 'scripts/analyze_trends.py'],
        'drafts': ['python', 'scripts/post_to_x.py', '--list'],
        'note_login': ['python', '-c', 'from sns.note_client import NoteClient; NoteClient().login_sync()'],
    }
    
    if task not in commands:
        return jsonify({'success': False, 'output': f'Unknown task: {task}'})
    
    try:
        env = os.environ.copy()
        env['PYTHONPATH'] = str(PROJECT_ROOT)
        
        result = subprocess.run(
            commands[task],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=PROJECT_ROOT,
            env=env
        )
        
        output = result.stdout + result.stderr
        return jsonify({
            'success': result.returncode == 0,
            'output': output or '(出力なし)'
        })
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'output': 'タイムアウト (120秒)'})
    except Exception as e:
        return jsonify({'success': False, 'output': f'Error: {str(e)}'})

@app.route('/generate', methods=['POST'])
def generate():
    """コンテンツを生成"""
    data = request.get_json()
    topic = data.get('topic', '')
    
    if not topic:
        return jsonify({'success': False, 'output': 'トピックを指定してください'})
    
    try:
        env = os.environ.copy()
        env['PYTHONPATH'] = str(PROJECT_ROOT)
        
        result = subprocess.run(
            ['python', 'scripts/generate_content.py', '--topic', topic],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=PROJECT_ROOT,
            env=env
        )
        
        output = result.stdout + result.stderr
        return jsonify({
            'success': result.returncode == 0,
            'output': output or '(出力なし)'
        })
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'output': 'タイムアウト (120秒)'})
    except Exception as e:
        return jsonify({'success': False, 'output': f'Error: {str(e)}'})

@app.route('/generate_ideas', methods=['POST'])
def generate_ideas():
    """コンテンツアイデアを生成"""
    try:
        env = os.environ.copy()
        env['PYTHONPATH'] = str(PROJECT_ROOT)
        
        result = subprocess.run(
            ['python', '-c', '''
from ai.idea_generator import ContentIdeaGenerator, print_ideas
generator = ContentIdeaGenerator()
ideas = generator.generate_ideas(count=5, platform="all")
print_ideas(ideas)
'''],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=PROJECT_ROOT,
            env=env
        )
        
        output = result.stdout + result.stderr
        return jsonify({
            'success': result.returncode == 0,
            'output': output or '(出力なし)'
        })
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'output': 'タイムアウト (120秒)'})
    except Exception as e:
        return jsonify({'success': False, 'output': f'Error: {str(e)}'})

@app.route('/weekly_plan', methods=['POST'])
def weekly_plan():
    """週間コンテンツプランを生成"""
    try:
        env = os.environ.copy()
        env['PYTHONPATH'] = str(PROJECT_ROOT)
        
        result = subprocess.run(
            ['python', '-c', '''
from ai.idea_generator import ContentIdeaGenerator, print_weekly_plan
generator = ContentIdeaGenerator()
plan = generator.get_weekly_plan()
print_weekly_plan(plan)
'''],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=PROJECT_ROOT,
            env=env
        )
        
        output = result.stdout + result.stderr
        return jsonify({
            'success': result.returncode == 0,
            'output': output or '(出力なし)'
        })
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'output': 'タイムアウト (180秒)'})
    except Exception as e:
        return jsonify({'success': False, 'output': f'Error: {str(e)}'})

@app.route('/create_enhanced_content', methods=['POST'])
def create_enhanced_content():
    """拡張コンテンツを生成（note無料/有料 → X画像+リプ → Instagram）"""
    try:
        env = os.environ.copy()
        env['PYTHONPATH'] = str(PROJECT_ROOT)
        
        result = subprocess.run(
            ['python', '-c', '''
from ai.enhanced_workflow import EnhancedContentWorkflow, print_enhanced_content
workflow = EnhancedContentWorkflow()
content = workflow.create_content()
print_enhanced_content(content)
'''],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=PROJECT_ROOT,
            env=env
        )
        
        output = result.stdout + result.stderr
        return jsonify({
            'success': result.returncode == 0,
            'output': output or '(出力なし)'
        })
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'output': 'タイムアウト (180秒)'})
    except Exception as e:
        return jsonify({'success': False, 'output': f'Error: {str(e)}'})

@app.route('/publish_all', methods=['POST'])
def publish_all():
    """一括投稿（生成→note→X→Instagram）"""
    try:
        env = os.environ.copy()
        env['PYTHONPATH'] = str(PROJECT_ROOT)
        
        result = subprocess.run(
            ['python', '-c', '''
from sns.publish_workflow import PublishWorkflow, print_result
workflow = PublishWorkflow()
result = workflow.run()
print_result(result)
'''],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=PROJECT_ROOT,
            env=env
        )
        
        output = result.stdout + result.stderr
        return jsonify({
            'success': result.returncode == 0,
            'output': output or '(出力なし)'
        })
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'output': 'タイムアウト (300秒)'})
    except Exception as e:
        return jsonify({'success': False, 'output': f'Error: {str(e)}'})

@app.route('/create_video_content', methods=['POST'])
def create_video_content():
    """動画コンテンツを生成（編集→YouTube/TikTok）"""
    data = request.get_json()
    video_path = data.get('video_path', '')
    
    if not video_path:
        return jsonify({'success': False, 'output': '動画パスを指定してください'})
    
    try:
        env = os.environ.copy()
        env['PYTHONPATH'] = str(PROJECT_ROOT)
        
        result = subprocess.run(
            ['python', '-c', f'''
from ai.content_workflow import ContentWorkflow, print_video_content
workflow = ContentWorkflow()
content = workflow.create_video_content("{video_path}")
print_video_content(content)
'''],
            capture_output=True,
            text=True,
            timeout=600,
            cwd=PROJECT_ROOT,
            env=env
        )
        
        output = result.stdout + result.stderr
        return jsonify({
            'success': result.returncode == 0,
            'output': output or '(出力なし)'
        })
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'output': 'タイムアウト (10分)'})
    except Exception as e:
        return jsonify({'success': False, 'output': f'Error: {str(e)}'})

@app.route('/auto_detect', methods=['POST'])
def auto_detect():
    """変更を検知してコンテンツを生成"""
    try:
        env = os.environ.copy()
        env['PYTHONPATH'] = str(PROJECT_ROOT)
        
        result = subprocess.run(
            ['python', '-c', '''
from research.change_detector import ChangeDetector, auto_generate_content
from ai.connected_content import print_content

detector = ChangeDetector()
changes = detector.check_all()

if changes:
    print(f"{len(changes)} 件の変更を検知:")
    for c in changes:
        print(f"  - [{c.change_type}] {c.source_name}: {c.description}")
    
    print("\\nコンテンツを生成中...")
    contents = auto_generate_content()
    
    if contents:
        for content in contents:
            print_content(content)
else:
    print("変更なし")
'''],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=PROJECT_ROOT,
            env=env
        )
        
        output = result.stdout + result.stderr
        has_changes = "変更を検知" in output
        return jsonify({
            'success': has_changes,
            'output': output or '変更なし'
        })
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'output': 'タイムアウト (300秒)'})
    except Exception as e:
        return jsonify({'success': False, 'output': f'Error: {str(e)}'})

@app.route('/trend_generate', methods=['POST'])
def trend_generate():
    """トレンドからコンテンツを生成"""
    try:
        env = os.environ.copy()
        env['PYTHONPATH'] = str(PROJECT_ROOT)
        
        result = subprocess.run(
            ['python', '-c', '''
from research.change_detector import get_trending_topic
from ai.connected_content import ConnectedContentGenerator, print_content

topic = get_trending_topic()

if topic:
    print(f"トレンドトピック: {topic}\\n")
    
    generator = ConnectedContentGenerator()
    content = generator.generate(topic)
    print_content(content)
else:
    print("トピックが見つかりません")
'''],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=PROJECT_ROOT,
            env=env
        )
        
        output = result.stdout + result.stderr
        return jsonify({
            'success': result.returncode == 0,
            'output': output or '(出力なし)'
        })
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'output': 'タイムアウト (180秒)'})
    except Exception as e:
        return jsonify({'success': False, 'output': f'Error: {str(e)}'})

@app.route('/generate_connected', methods=['POST'])
def generate_connected():
    """連携コンテンツを生成"""
    data = request.get_json()
    topic = data.get('topic', '')
    
    if not topic:
        return jsonify({'success': False, 'output': 'トピックを指定してください'})
    
    try:
        env = os.environ.copy()
        env['PYTHONPATH'] = str(PROJECT_ROOT)
        
        result = subprocess.run(
            ['python', '-c', f'''
from ai.connected_content import ConnectedContentGenerator, print_content
generator = ConnectedContentGenerator()
content = generator.generate("{topic}")
print_content(content)
'''],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=PROJECT_ROOT,
            env=env
        )
        
        output = result.stdout + result.stderr
        return jsonify({
            'success': result.returncode == 0,
            'output': output or '(出力なし)'
        })
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'output': 'タイムアウト (180秒)'})
    except Exception as e:
        return jsonify({'success': False, 'output': f'Error: {str(e)}'})

@app.route('/note_post', methods=['POST'])
def note_post():
    """note記事を生成・投稿（強化版 + X投稿文も生成）"""
    data = request.get_json()
    topic = data.get('topic', '')
    
    if not topic:
        return jsonify({'success': False, 'output': 'トピックを指定してください'})
    
    try:
        env = os.environ.copy()
        env['PYTHONPATH'] = str(PROJECT_ROOT)
        
        # 強化版ワークフローで記事とX投稿を生成
        result = subprocess.run(
            ['python', '-c', f'''
import asyncio
import json
from datetime import datetime
from pathlib import Path
from ai.enhanced_workflow import EnhancedContentWorkflow
from sns.note_client import NoteClient

# 強化版ワークフローでコンテンツ生成
workflow = EnhancedContentWorkflow()
content = workflow.create_content(topic="{topic}")

print("=" * 60)
print("📖 note記事生成完了")
print("=" * 60)
print(f"タイトル: {{content.note.title}}")
print(f"タグ: {{', '.join(content.note.tags)}}")
print(f"無料版: {{len(content.note.free_content)}}文字")
print(f"有料版: {{len(content.note.paid_content)}}文字")
print(f"ヘッダー画像プロンプト: {{content.note.header_image_prompt}}")
print()
print("=" * 60)
print("🐦 X投稿文")
print("=" * 60)
print(f"メイン: {{content.x_post.main_text}}")
print(f"ハッシュタグ: {{' '.join(content.x_post.hashtags)}}")
print(f"リプ欄: {{content.x_post.reply_text}}")
print()

# note投稿（タイトル + 無料版のみ下書きとして）
print("=" * 60)
print("📤 noteに下書き保存中...")
print("=" * 60)

full_content = content.note.free_content + "\\n\\n---\\n\\n" + content.note.paid_content

async def post_note():
    client = NoteClient()
    result = await client.post_article(
        content.note.title,
        full_content,
        publish=False
    )
    if result.success:
        print("✅ 下書き保存完了")
    else:
        print(f"❌ エラー: {{result.error}}")

asyncio.run(post_note())

# X下書きも保存
x_draft = {{
    "platform": "x",
    "main_text": content.x_post.main_text,
    "hashtags": content.x_post.hashtags,
    "reply_text": content.x_post.reply_text,
    "source_url": content.x_post.source_url,
    "created_at": datetime.now().isoformat()
}}

draft_path = Path("sns/drafts") / f"x_note_{{datetime.now().strftime('%Y%m%d_%H%M%S')}}.json"
draft_path.parent.mkdir(parents=True, exist_ok=True)
with open(draft_path, "w", encoding="utf-8") as f:
    json.dump(x_draft, f, ensure_ascii=False, indent=2)
print(f"\\n📝 X投稿下書き保存: {{draft_path}}")
'''],
            capture_output=True,
            text=True,
            timeout=600,  # 10分に延長
            cwd=PROJECT_ROOT,
            env=env
        )
        
        output = result.stdout + result.stderr
        return jsonify({
            'success': result.returncode == 0,
            'output': output or '(出力なし)'
        })
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'output': 'タイムアウト (600秒)'})
    except Exception as e:
        return jsonify({'success': False, 'output': f'Error: {str(e)}'})

@app.route('/edit_video', methods=['POST'])
def edit_video():
    """動画を編集"""
    data = request.get_json()
    video_path = data.get('video_path', '')
    genre = data.get('genre', 'auto')
    
    if not video_path:
        return jsonify({'success': False, 'output': '動画パスを指定してください'})
    
    try:
        env = os.environ.copy()
        env['PYTHONPATH'] = str(PROJECT_ROOT)
        
        genre_arg = "" if genre == "auto" else f"--genre {genre}"
        
        result = subprocess.run(
            ['python', '-c', f'''
from pathlib import Path
from media.video_editor import VideoEditor

editor = VideoEditor()
outputs = editor.edit_video(
    Path("{video_path}"),
    output_format="both",
    genre={repr(genre) if genre != "auto" else None}
)

print(f"編集完了: {{len(outputs)}} ファイル")
for out in outputs:
    print(f"  - {{out}}")
'''],
            capture_output=True,
            text=True,
            timeout=600,  # 動画は時間がかかる
            cwd=PROJECT_ROOT,
            env=env
        )
        
        output = result.stdout + result.stderr
        return jsonify({
            'success': result.returncode == 0,
            'output': output or '(出力なし)'
        })
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'output': 'タイムアウト (10分)'})
    except Exception as e:
        return jsonify({'success': False, 'output': f'Error: {str(e)}'})

if __name__ == '__main__':
    print("🚀 Enludus Automation Hub - Web Dashboard")
    print("   http://localhost:3000")
    print("   Ctrl+C で停止")
    app.run(host='0.0.0.0', port=3000, debug=False)
