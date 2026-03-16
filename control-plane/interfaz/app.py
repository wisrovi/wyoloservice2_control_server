import gradio as gr
import requests
import os
import json
from datetime import datetime

API_URL = os.getenv("API_URL", "http://fastapi:8000")


def get_workers():
    try:
        r = requests.get(f"{API_URL}/workers", timeout=10)
        return r.json() if r.status_code == 200 else []
    except:
        return []


def get_queued_tasks():
    try:
        r = requests.get(f"{API_URL}/tasks", timeout=10)
        return r.json() if r.status_code == 200 else {"queued_tasks": []}
    except:
        return {"queued_tasks": []}


def get_all_status():
    workers = get_workers()
    tasks = get_queued_tasks()
    return len(workers), len(tasks.get("queued_tasks", []))


def refresh_workers_table():
    workers = get_workers()
    if not workers:
        return [["No workers available"]]
    return [[w] for w in workers]


def refresh_tasks_table():
    result = get_queued_tasks()
    tasks = result.get("queued_tasks", [])
    if not tasks:
        return [["No tasks in queue", "", "", ""]]
    rows = []
    for t in tasks:
        rows.append(
            [
                t.get("task_id", "")[:16] + "...",
                t.get("state", ""),
                t.get("worker", ""),
                t.get("args", "")[:35] + "...",
            ]
        )
    return rows


def start_training(config_file, mode, priority, worker_name):
    if config_file is None:
        return "⚠️ Please upload a YAML file first."
    try:
        with open(config_file.name, "rb") as f:
            files = {
                "config_file": (
                    os.path.basename(config_file.name),
                    f,
                    "application/x-yaml",
                )
            }
            data = {
                "mode": mode,
                "priority": priority if mode == "public" else "medium",
                "worker_name": worker_name if mode == "private" else "",
            }
            r = requests.post(f"{API_URL}/train", files=files, data=data, timeout=30)
        if r.status_code == 200:
            res = r.json()
            return f"""✅ <b>Study Queued Successfully!</b>

📋 <b>Study ID:</b> <code>{res["study_id"]}</code>
🔧 <b>Mode:</b> {res["mode"]}
🎯 <b>Worker/Queue:</b> {res["worker_queue"]}

⏰ <b>Time:</b> {datetime.now().strftime("%H:%M:%S")}"""
        return f"❌ Error: {r.text}"
    except Exception as e:
        return f"❌ Connection Error: {str(e)}"


def check_status(study_id):
    if not study_id:
        return "⚠️ Enter a Study ID"
    try:
        r = requests.get(f"{API_URL}/status/{study_id}")
        if r.status_code == 200:
            data = r.json()
            state = data.get("state", "UNKNOWN")
            state_emoji = {
                "PENDING": "⏳",
                "STARTED": "🔄",
                "SUCCESS": "✅",
                "FAILURE": "❌",
                "RETRY": "🔁",
            }.get(state, "❓")
            return f"""<b>Status for:</b> <code>{study_id}</code>

{state_emoji} <b>State:</b> {state}

📦 <b>Result:</b>
<pre>{json.dumps(data.get("result", {}), indent=2)}</pre>"""
        return f"❌ Error: {r.text}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


def delete_task(task_id):
    if not task_id:
        return "⚠️ Enter a Task ID"
    try:
        r = requests.delete(f"{API_URL}/tasks/{task_id}")
        if r.status_code == 200:
            return f"✅ <b>Task Revoked</b><br>ID: <code>{task_id[:20]}...</code>"
        return f"❌ Error: {r.text}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


def requeue_task(task_id, new_priority):
    if not task_id:
        return "⚠️ Enter a Task ID"
    try:
        r = requests.post(
            f"{API_URL}/tasks/{task_id}/requeue?priority={new_priority}", timeout=15
        )
        if r.status_code == 200:
            res = r.json()
            return f"""✅ <b>Task Requeued</b>

📤 <b>Original:</b> <code>{task_id[:16]}...</code>
📥 <b>New ID:</b> <code>{res["new_task_id"][:16]}...</code>
🔢 <b>Priority:</b> {res["new_priority"]}"""
        return f"❌ Error: {r.text}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


def load_stats():
    w, t = get_all_status()
    return w, t


def load_workers():
    workers = get_workers()
    return workers if workers else []


css = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    --primary: #6366f1;
    --primary-dark: #4f46e5;
    --primary-light: #818cf8;
    --bg-dark: #0a0a0f;
    --bg-card: #12121a;
    --bg-card-hover: #1a1a25;
    --bg-input: #0d0d12;
    --text-main: #e4e4e7;
    --text-muted: #71717a;
    --text-dim: #52525b;
    --border: #27272a;
    --border-light: #3f3f46;
    --success: #10b981;
    --success-bg: rgba(16, 185, 129, 0.15);
    --danger: #ef4444;
    --danger-bg: rgba(239, 68, 68, 0.15);
    --warning: #f59e0b;
    --warning-bg: rgba(245, 158, 11, 0.15);
    --info: #3b82f6;
    --info-bg: rgba(59, 130, 246, 0.15);
}

* { font-family: 'Inter', sans-serif !important; }

body {
    background: var(--bg-dark) !important;
    color: var(--text-main) !important;
}

.gradio-container {
    max-width: 1600px !important;
    margin: 0 auto !important;
    padding: 20px !important;
}

body::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: 
        radial-gradient(circle at 20% 20%, rgba(99, 102, 241, 0.08) 0%, transparent 50%),
        radial-gradient(circle at 80% 80%, rgba(139, 92, 246, 0.06) 0%, transparent 50%);
    pointer-events: none;
    z-index: -1;
}

.header {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(139, 92, 246, 0.15) 100%);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 24px;
    backdrop-filter: blur(10px);
}

.header-title {
    font-size: 32px !important;
    font-weight: 700 !important;
    background: linear-gradient(135deg, #fff 0%, #a5b4fc 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 !important;
}

.header-subtitle {
    color: var(--text-muted) !important;
    margin: 8px 0 0 0 !important;
    font-size: 14px !important;
}

.stats-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
}

.stat-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    transition: all 0.3s ease;
}

.stat-card:hover {
    border-color: var(--primary);
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(99, 102, 241, 0.15);
}

.stat-icon {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    margin-bottom: 12px;
}

.stat-value {
    font-size: 32px;
    font-weight: 700;
    color: var(--text-main);
}

.stat-label {
    font-size: 13px;
    color: var(--text-muted);
    margin-top: 4px;
}

.tabs {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 16px;
    overflow: hidden;
}

.tab-nav {
    background: var(--bg-input);
    border-bottom: 1px solid var(--border);
    padding: 8px;
    display: flex;
    gap: 4px;
}

.tab-nav button {
    background: transparent !important;
    color: var(--text-muted) !important;
    border: none !important;
    padding: 12px 20px !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    border-radius: 8px !important;
    transition: all 0.2s ease !important;
}

.tab-nav button:hover {
    background: var(--bg-card-hover) !important;
    color: var(--text-main) !important;
}

.tab-nav button.selected {
    background: var(--primary) !important;
    color: white !important;
}

.tab-content {
    padding: 24px;
}

.dark input, .dark textarea, .dark select, .dark .dropdown {
    background: var(--bg-input) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-main) !important;
    border-radius: 10px !important;
    padding: 12px 16px !important;
    font-size: 14px !important;
}

.dark input:focus, .dark textarea:focus, .dark select:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2) !important;
    outline: none !important;
}

.dark input::placeholder {
    color: var(--text-dim) !important;
}

.btn-primary {
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
    color: white;
    border: none;
    padding: 12px 24px;
    border-radius: 10px;
    font-weight: 600;
    cursor: pointer;
}

.btn-primary:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4);
}

.btn-secondary {
    background: var(--bg-card-hover);
    color: var(--text-main);
    border: 1px solid var(--border);
    padding: 12px 24px;
    border-radius: 10px;
    font-weight: 500;
    cursor: pointer;
}

.btn-secondary:hover {
    border-color: var(--primary);
    background: rgba(99, 102, 241, 0.1);
}

.dark .dataframe {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
}

.dark .dataframe th {
    background: var(--bg-input) !important;
    color: var(--text-muted) !important;
    font-weight: 600 !important;
    font-size: 12px !important;
    text-transform: uppercase !important;
    padding: 14px 16px !important;
}

.dark .dataframe td {
    background: var(--bg-card) !important;
    color: var(--text-main) !important;
    padding: 12px 16px !important;
}

.section-title {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-main);
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 10px;
}

.section-title::before {
    content: '';
    width: 4px;
    height: 20px;
    background: var(--primary);
    border-radius: 2px;
}

.footer {
    text-align: center;
    padding: 24px;
    color: var(--text-dim);
    font-size: 12px;
}
"""

with gr.Blocks(css=css) as demo:
    gr.HTML("""
        <div class="header">
            <h1 class="header-title">🚀 ML Cluster Control Panel</h1>
            <p class="header-subtitle">Manage training studies, monitor workers, and track progress in real-time</p>
        </div>
    """)

    # Stats que se cargan dinámicamente
    with gr.Row():
        gr.HTML("""
            <div class="stats-row" style="width: 100%;">
                <div class="stat-card">
                    <div class="stat-icon" style="background: rgba(99, 102, 241, 0.15);">👥</div>
                    <div class="stat-value" id="workers-count">-</div>
                    <div class="stat-label">Active Workers</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon" style="background: rgba(245, 158, 11, 0.15);">📋</div>
                    <div class="stat-value" id="tasks-count">-</div>
                    <div class="stat-label">Queued Tasks</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon" style="background: rgba(16, 185, 129, 0.15);">✅</div>
                    <div class="stat-value">0</div>
                    <div class="stat-label">Completed Studies</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon" style="background: rgba(59, 130, 246, 0.15);">⚡</div>
                    <div class="stat-value">Online</div>
                    <div class="stat-label">System Status</div>
                </div>
            </div>
        """)

    # Cargar stats al inicio
    demo.load(
        fn=load_stats, outputs=[gr.Number(visible=False), gr.Number(visible=False)]
    )

    with gr.Tabs():
        with gr.Tab("📊 Dashboard", id="dashboard"):
            with gr.Row():
                gr.HTML("""
                    <div class="section-title">Quick Actions</div>
                    <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                        <button class="btn-primary" onclick="document.querySelectorAll('.tab-nav button')[1].click()">➕ New Training Study</button>
                        <button class="btn-secondary" onclick="document.querySelectorAll('.tab-nav button')[2].click()">👥 View Workers</button>
                        <button class="btn-secondary" onclick="document.querySelectorAll('.tab-nav button')[3].click()">📋 Manage Tasks</button>
                    </div>
                """)
            gr.HTML("""
                <div class="section-title" style="margin-top: 24px;">Recent Activity</div>
                <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; color: var(--text-muted);">
                    <p>No recent activity. Launch a study to see results here.</p>
                </div>
            """)

        with gr.Tab("👥 Workers", id="workers"):
            gr.HTML('<div class="section-title">Active Private Workers</div>')
            workers_table = gr.Dataframe(
                headers=["Worker Name"], datatype=["str"], max_height=350
            )
            with gr.Row():
                btn_refresh_workers = gr.Button(
                    "🔄 Refresh Workers", variant="secondary"
                )

            # Cargar al inicio y al hacer click
            demo.load(fn=refresh_workers_table, outputs=workers_table)
            btn_refresh_workers.click(fn=refresh_workers_table, outputs=workers_table)

        with gr.Tab("➕ New Study", id="new-study"):
            gr.HTML('<div class="section-title">Launch New Training Study</div>')

            # Hidden state para workers
            workers_state = gr.State([])

            with gr.Row():
                with gr.Column(scale=1):
                    yaml_input = gr.File(
                        label="📁 YAML Configuration", file_types=[".yaml", ".yml"]
                    )

                    mode_radio = gr.Radio(
                        choices=["public", "private"],
                        value="public",
                        label="Dispatch Mode",
                    )

                    priority_dropdown = gr.Dropdown(
                        choices=["high", "medium", "low"],
                        value="medium",
                        label="Priority (Public Mode)",
                        visible=True,
                    )

                    worker_dropdown = gr.Dropdown(
                        choices=[],  # Se carga dinámicamente
                        label="Select Worker (Private Mode)",
                        visible=False,
                    )

                    btn_start = gr.Button(
                        "🚀 Launch Study", variant="primary", size="lg"
                    )

                with gr.Column(scale=1):
                    gr.HTML('<div class="section-title">Response</div>')
                    output_start = gr.HTML()

            # Cargar workers al iniciar
            demo.load(fn=load_workers, outputs=workers_state)

            def toggle_mode(mode, workers):
                if mode == "public":
                    return gr.update(visible=True), gr.update(visible=False), workers
                return (
                    gr.update(visible=False),
                    gr.update(visible=True, choices=workers if workers else []),
                    workers,
                )

            mode_radio.change(
                toggle_mode,
                inputs=[mode_radio, workers_state],
                outputs=[priority_dropdown, worker_dropdown, workers_state],
            )
            btn_start.click(
                fn=start_training,
                inputs=[yaml_input, mode_radio, priority_dropdown, worker_dropdown],
                outputs=output_start,
            )

        with gr.Tab("🔍 Monitor", id="monitor"):
            gr.HTML('<div class="section-title">Check Study Status</div>')
            with gr.Row():
                study_id_input = gr.Textbox(placeholder="Enter study ID...", scale=4)
                btn_check_status = gr.Button("🔍 Check Status", variant="primary")
            status_output = gr.HTML()
            btn_check_status.click(
                fn=check_status, inputs=study_id_input, outputs=status_output
            )

        with gr.Tab("📋 Tasks", id="tasks"):
            gr.HTML('<div class="section-title">Queued Tasks</div>')
            tasks_table = gr.Dataframe(
                headers=["Task ID", "State", "Worker", "Args"],
                datatype=["str", "str", "str", "str"],
                max_height=250,
            )
            with gr.Row():
                btn_refresh_tasks = gr.Button("🔄 Refresh", variant="secondary")

            gr.HTML(
                '<div class="section-title" style="margin-top: 24px;">Task Actions</div>'
            )
            with gr.Row():
                with gr.Column(scale=2):
                    task_id_input = gr.Textbox(placeholder="Task ID...")
                with gr.Column(scale=1):
                    new_priority = gr.Dropdown(
                        choices=["high", "medium", "low"],
                        value="medium",
                        label="Priority",
                    )
                with gr.Column(scale=1):
                    btn_requeue = gr.Button("🔄 Requeue", variant="primary")
                with gr.Column(scale=1):
                    btn_delete = gr.Button("🗑️ Delete", variant="secondary")

            manage_output = gr.HTML()

            # Cargar al inicio
            demo.load(fn=refresh_tasks_table, outputs=tasks_table)
            btn_refresh_tasks.click(fn=refresh_tasks_table, outputs=tasks_table)
            btn_requeue.click(
                fn=requeue_task,
                inputs=[task_id_input, new_priority],
                outputs=manage_output,
            )
            btn_delete.click(
                fn=delete_task, inputs=task_id_input, outputs=manage_output
            )

    gr.HTML("""
        <div class="footer">
            ML Cluster Control Panel v2.0 | FastAPI • Celery • Gradio
        </div>
    """)

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0", server_port=7860, inbrowser=True, show_error=True
    )
