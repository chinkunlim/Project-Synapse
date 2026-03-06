from flask import Blueprint, render_template, jsonify, request
import os
import requests

n8n_bp = Blueprint('n8n', __name__)

# Helper to get N8N Base URL
def get_n8n_url():
    # In Docker, we might access via container name 'n8n' port 5678
    # But from user perspective clicking links, it's localhost:5678
    # For server-side requests (Flask -> N8N), we should use internal docker name if possible, 
    # OR env var. Let's use env var with fallback.
    return os.getenv('N8N_BASE_URL', 'http://localhost:5678')

def get_n8n_api_key():
    return os.getenv('N8N_API_KEY', '')

@n8n_bp.route('/n8n')
def n8n_dashboard():
    return render_template('n8n.html')

@n8n_bp.route('/api/n8n/workflows')
def list_workflows():
    api_key = get_n8n_api_key()
    base_url = get_n8n_url()
    
    if not api_key:
        return jsonify({"status": "error", "message": "N8N_API_KEY not found in env."})
        
    try:
        # N8N API: GET /workflows
        # Note: If running inside Docker container 'web', 'localhost' refers to 'web' container.
        # Needs to point to 'n8n' container or host. 
        # Ideally user sets N8N_BASE_URL=http://n8n:5678 in .env for docker-compose internal network
        
        # We try strict URL first, if fails, inform user to set env.
        resp = requests.get(
            f"{base_url}/api/v1/workflows",
            headers={"X-N8N-API-KEY": api_key},
            timeout=5
        )
        
        if resp.status_code == 200:
            data = resp.json()
            workflows = []
            for wf in data.get('data', []):
                # Detect trigger type from nodes
                nodes = wf.get('nodes', [])
                node_types = [n.get('type', '').lower() for n in nodes]
                has_webhook  = any('webhook' in t for t in node_types)
                has_schedule = any('schedule' in t or 'cron' in t or 'interval' in t for t in node_types)
                has_manual   = any('manualtrigger' in t for t in node_types)

                if has_webhook:
                    trigger_type = 'webhook'
                elif has_schedule:
                    trigger_type = 'schedule'
                elif has_manual:
                    trigger_type = 'manual'
                else:
                    trigger_type = 'other'

                wf['trigger_type'] = trigger_type
                workflows.append(wf)

            return jsonify({
                "status": "success",
                "workflows": workflows,
                "n8n_url": get_n8n_url()
            })

        else:
             return jsonify({"status": "error", "message": f"N8N Error: {resp.status_code} {resp.text}"})
             
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@n8n_bp.route('/api/n8n/execute/<id>', methods=['POST'])
def execute_workflow(id):
    api_key = get_n8n_api_key()
    base_url = get_n8n_url()

    if not api_key:
        return jsonify({"status": "error", "message": "N8N_API_KEY not set. Please configure it in System Settings."})

    headers = {"X-N8N-API-KEY": api_key}

    try:
        # Step 1: Fetch workflow details to find its trigger type
        resp = requests.get(f"{base_url}/api/v1/workflows/{id}", headers=headers, timeout=5)
        if resp.status_code != 200:
            return jsonify({"status": "error", "message": f"Cannot fetch workflow: {resp.status_code} {resp.text}"})

        workflow = resp.json()
        nodes = workflow.get("nodes", [])

        # Step 2: Find webhook nodes
        webhook_nodes = [n for n in nodes if "webhook" in n.get("type", "").lower()]

        if webhook_nodes:
            # Get the webhook path from the first webhook node
            webhook_path = webhook_nodes[0].get("parameters", {}).get("path", "")
            if webhook_path:
                # Call the production webhook URL
                webhook_url = f"{base_url}/webhook/{webhook_path}"
                trigger_resp = requests.post(webhook_url, json={}, timeout=10)
                if trigger_resp.status_code in (200, 201):
                    return jsonify({"status": "success", "message": f"✅ Webhook triggered successfully (HTTP {trigger_resp.status_code})"})
                else:
                    # Try test webhook as fallback
                    test_webhook_url = f"{base_url}/webhook-test/{webhook_path}"
                    trigger_resp2 = requests.post(test_webhook_url, json={}, timeout=10)
                    if trigger_resp2.status_code in (200, 201):
                        return jsonify({"status": "success", "message": f"✅ Test webhook triggered (HTTP {trigger_resp2.status_code}). Note: Activate the workflow for production."})
                    return jsonify({"status": "error", "message": f"Webhook call failed: {trigger_resp.status_code}. Make sure the workflow is Active."})
            else:
                return jsonify({"status": "warning", "message": "⚠️ Webhook node found but path is not set. Please configure the webhook path in n8n."})

        # Step 3: For all other trigger types, try POST /run to force execution
        # (works for schedule, manual, and any other trigger type in newer n8n versions)
        run_resp = requests.post(f"{base_url}/api/v1/workflows/{id}/run", headers=headers, json={}, timeout=10)
        if run_resp.status_code in (200, 201):
            return jsonify({"status": "success", "message": "✅ Workflow executed successfully."})
        else:
            return jsonify({"status": "error", "message": f"❌ Could not execute workflow (HTTP {run_resp.status_code}: {run_resp.text[:200]}). Please try running it from the n8n UI."})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

