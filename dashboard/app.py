"""
David Flip Dashboard - Flask Web Application

Mission Control for AI personalities. Provides:
- Content review queue (video/script cards with Approve/Reject)
- Per-platform feeds (X, YouTube, TikTok)
- Approve = schedule to optimal time slot, Oprah posts automatically
- Reject = feedback goes into David's memory to improve
- System status, research findings, activity timeline
"""

import json
import os
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps

from flask import (
    Flask, render_template, jsonify, request, redirect,
    url_for, session, send_file
)
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("DASHBOARD_SECRET_KEY", "david-flip-dashboard-secret-2026")

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
APPROVAL_DB = DATA_DIR / "approval_queue.db"
RESEARCH_DB = DATA_DIR / "research.db"
AUDIT_LOG = DATA_DIR / "audit.db"
SCHEDULER_DB = DATA_DIR / "scheduler.db"
FEEDBACK_DIR = DATA_DIR / "content_feedback"

# Ensure feedback directory exists
Path(FEEDBACK_DIR).mkdir(parents=True, exist_ok=True)

# Simple auth (single operator)
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "flipt2026")

# Platform-specific optimal posting times (UTC) — targeting US audience peaks.
# Must match core/scheduler.py PLATFORM_OPTIMAL_HOURS
PLATFORM_OPTIMAL_HOURS = {
    "twitter": [12, 15, 18, 21, 0, 3],  # 7am, 10am, 1pm, 4pm, 7pm, 10pm ET — 6 slots, 3h apart
    "youtube": [18, 21, 0],              # 1pm, 4pm, 7pm ET
    "tiktok": [16, 19, 23, 1],          # 11am, 2pm, 6pm, 8pm ET
}


def get_db(db_path):
    """Get database connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def login_required(f):
    """Decorator to require login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ============== AUTH ==============

@app.route("/login", methods=["GET", "POST"])
def login():
    """Login page."""
    if request.method == "POST":
        if request.form.get("password") == DASHBOARD_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        return render_template("login.html", error="Invalid password")
    return render_template("login.html")


@app.route("/logout")
def logout():
    """Logout."""
    session.pop("logged_in", None)
    return redirect(url_for("login"))


# ============== MAIN PAGES ==============

@app.route("/")
@login_required
def index():
    """Dashboard home - overview of everything."""
    stats = get_stats()
    stats["content_queue"] = get_content_count()
    recent_activity = get_recent_activity(limit=20)
    schedule = get_schedule_data()
    hour_labels = {13: "8am ET", 16: "11am ET", 19: "2pm ET", 22: "5pm ET"}

    return render_template(
        "index.html",
        stats=stats,
        recent_activity=recent_activity,
        schedule=schedule,
        hour_labels=hour_labels,
    )


@app.route("/approvals")
@login_required
def approvals():
    """Pending approvals page."""
    pending = get_pending_approvals()
    return render_template("approvals.html", approvals=pending)


@app.route("/research")
@login_required
def research():
    """Research findings page."""
    findings = get_research_findings(limit=50)
    return render_template("research.html", findings=findings)


@app.route("/tweets")
@login_required
def tweets():
    """Tweet history page."""
    tweet_history = get_tweet_history(limit=50)
    return render_template("tweets.html", tweets=tweet_history)


@app.route("/activity")
@login_required
def activity():
    """Full activity timeline."""
    timeline = get_recent_activity(limit=100)
    return render_template("activity.html", timeline=timeline)


@app.route("/schedule")
@login_required
def schedule_view():
    """Schedule calendar — pipeline visibility across time."""
    data = get_schedule_data()
    hour_labels = {13: "8am ET", 16: "11am ET", 19: "2pm ET", 22: "5pm ET"}
    return render_template("schedule.html", **data, hour_labels=hour_labels)


@app.route("/content")
@login_required
def content_queue():
    """Content review queue — the main Mission Control feed."""
    platform_filter = request.args.get("platform", "")

    # Get all pending video/content approvals
    content_items = get_pending_content(platform_filter=platform_filter)
    platform_counts = get_content_platform_counts()
    scheduled_items = get_scheduled_content()

    return render_template(
        "content.html",
        content_items=content_items,
        platform_filter=platform_filter,
        platform_counts=platform_counts,
        scheduled_items=scheduled_items,
        personality_name="David Flip",
    )


# ============== CONTENT API ENDPOINTS ==============

@app.route("/api/video/<int:approval_id>")
@login_required
def api_serve_video(approval_id):
    """Serve a video file for preview in the content queue."""
    try:
        conn = get_db(APPROVAL_DB)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT action_data FROM approvals WHERE id = ?", (approval_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return jsonify({"error": "Not found"}), 404

        action_data = json.loads(row["action_data"])
        video_path = action_data.get("video_path", "")

        # Resolve relative paths from project root
        if video_path and not os.path.isabs(video_path):
            video_path = str(BASE_DIR / video_path)

        if video_path and os.path.exists(video_path):
            return send_file(video_path, mimetype="video/mp4")

        return jsonify({"error": "Video file not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/content/approve/<int:approval_id>", methods=["POST"])
@login_required
def api_content_approve(approval_id):
    """
    Approve content and schedule to optimal time slots per platform.

    Oprah picks up scheduled items and posts automatically.
    """
    try:
        data = request.json or {}
        platforms = data.get("platforms", ["twitter", "youtube", "tiktok"])

        conn = get_db(APPROVAL_DB)
        cursor = conn.cursor()

        # Get the approval record
        cursor.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({"success": False, "error": "Approval not found"})

        action_data = json.loads(row["action_data"])

        # Mark as approved
        cursor.execute(
            "UPDATE approvals SET status = 'approved', operator_notes = ?, reviewed_at = ? WHERE id = ?",
            (json.dumps({"platforms": platforms}), datetime.now().isoformat(), approval_id)
        )
        conn.commit()
        conn.close()

        # Schedule to optimal time slots per platform
        scheduled_time = _get_next_optimal_slot(platforms)

        # Write a schedule request file that main.py's poller picks up
        schedule_request = {
            "approval_id": approval_id,
            "action_data": action_data,
            "platforms": platforms,
            "scheduled_time": scheduled_time.isoformat(),
            "approved_at": datetime.now().isoformat(),
        }
        request_path = FEEDBACK_DIR / f"schedule_{approval_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(request_path, "w") as f:
            json.dump(schedule_request, f, indent=2)

        log_activity("content", f"Approved content #{approval_id} for {', '.join(platforms)} at {scheduled_time.strftime('%I:%M %p')}")

        return jsonify({
            "success": True,
            "scheduled_time": scheduled_time.strftime("%b %d, %I:%M %p"),
            "platforms": platforms,
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/content/approve-script/<int:approval_id>", methods=["POST"])
@login_required
def api_content_approve_script(approval_id):
    """
    Approve a script and trigger video rendering.

    Stage 1 -> Stage 2 transition. Writes a render_{id}.json file
    that main.py's poller picks up to start video rendering.
    """
    try:
        conn = get_db(APPROVAL_DB)
        cursor = conn.cursor()

        # Get the approval record
        cursor.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({"success": False, "error": "Approval not found"})

        if row["action_type"] != "script_review":
            conn.close()
            return jsonify({"success": False, "error": "Not a script review item"})

        # Idempotency: prevent duplicate renders from double-clicks or page refreshes
        if row["status"] != "pending":
            conn.close()
            return jsonify({"success": False, "error": f"Already {row['status']} — video render already triggered"})

        action_data = json.loads(row["action_data"])

        # Mark script as approved
        cursor.execute(
            "UPDATE approvals SET status = 'approved', operator_notes = 'script_approved_for_render', reviewed_at = ? WHERE id = ?",
            (datetime.now().isoformat(), approval_id)
        )
        conn.commit()
        conn.close()

        # Write render request file for main.py poller
        render_request = {
            "approval_id": approval_id,
            "script": action_data.get("script", ""),
            "pillar": action_data.get("pillar", 1),
            "theme_title": action_data.get("theme_title", ""),
            "category": action_data.get("category", ""),
            "mood": action_data.get("mood", ""),
            "approved_at": datetime.now().isoformat(),
        }
        request_path = FEEDBACK_DIR / f"render_{approval_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(request_path, "w") as f:
            json.dump(render_request, f, indent=2)

        log_activity("content", f"Script #{approval_id} approved — rendering video")

        return jsonify({"success": True, "message": "Script approved. Video rendering started."})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/content/reject/<int:approval_id>", methods=["POST"])
@login_required
def api_content_reject(approval_id):
    """
    Reject content with feedback.

    The feedback is saved to David's memory so he learns and adjusts
    future content generation.
    """
    try:
        data = request.json or {}
        reason = data.get("reason", "").strip()

        if not reason:
            return jsonify({"success": False, "error": "Feedback reason required"})

        conn = get_db(APPROVAL_DB)
        cursor = conn.cursor()

        # Get the approval record for context
        cursor.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({"success": False, "error": "Approval not found"})

        action_data = json.loads(row["action_data"])

        # Mark as rejected with feedback
        cursor.execute(
            "UPDATE approvals SET status = 'rejected', operator_notes = ?, reviewed_at = ? WHERE id = ?",
            (reason, datetime.now().isoformat(), approval_id)
        )
        conn.commit()
        conn.close()

        # Save feedback for David's memory (picked up by main.py poller)
        feedback = {
            "type": "content_rejection",
            "approval_id": approval_id,
            "reason": reason,
            "content_context": {
                "text": action_data.get("text", "")[:500],
                "script": action_data.get("script", "")[:500],
                "action_type": row["action_type"],
                "theme_title": action_data.get("theme_title", ""),
                "category": action_data.get("category", ""),
                "pillar": action_data.get("pillar", ""),
                "mood": action_data.get("mood", ""),
            },
            "timestamp": datetime.now().isoformat(),
        }
        feedback_path = FEEDBACK_DIR / f"feedback_{approval_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(feedback_path, "w") as f:
            json.dump(feedback, f, indent=2)

        log_activity("content", f"Rejected content #{approval_id}: {reason[:100]}")

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ============== API ENDPOINTS ==============

@app.route("/api/approve/<int:approval_id>", methods=["POST"])
@login_required
def api_approve(approval_id):
    """Approve a pending item and schedule it via Oprah."""
    try:
        conn = get_db(APPROVAL_DB)
        cursor = conn.cursor()

        # Get the approval record
        cursor.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({"success": False, "error": "Not found"})

        action_data = json.loads(row["action_data"])
        action_type = row["action_type"]

        cursor.execute(
            "UPDATE approvals SET status = 'approved', reviewed_at = ? WHERE id = ?",
            (datetime.now().isoformat(), approval_id)
        )
        conn.commit()
        conn.close()

        # Pick the next available tweet slot
        scheduled_time = _get_next_available_tweet_slot()

        # Write schedule request for main.py poller
        schedule_request = {
            "approval_id": approval_id,
            "action_type": action_type,
            "action_data": action_data,
            "content_type": action_type,
            "scheduled_time": scheduled_time.isoformat(),
            "approved_at": datetime.now().isoformat(),
        }
        request_path = FEEDBACK_DIR / f"schedule_{approval_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(request_path, "w") as f:
            json.dump(schedule_request, f, indent=2)

        log_activity("approval", f"Approved & scheduled {action_type} #{approval_id} for {scheduled_time.strftime('%I:%M %p UTC')}")

        return jsonify({
            "success": True,
            "scheduled_time": scheduled_time.strftime("%I:%M %p UTC"),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/reject/<int:approval_id>", methods=["POST"])
@login_required
def api_reject(approval_id):
    """Reject a pending item with feedback for David's memory."""
    reason = request.json.get("reason", "Rejected by operator")
    try:
        conn = get_db(APPROVAL_DB)
        cursor = conn.cursor()

        # Get record for context
        cursor.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({"success": False, "error": "Not found"})

        action_data = json.loads(row["action_data"])
        action_type = row["action_type"]

        cursor.execute(
            "UPDATE approvals SET status = 'rejected', operator_notes = ?, reviewed_at = ? WHERE id = ?",
            (reason, datetime.now().isoformat(), approval_id)
        )
        conn.commit()
        conn.close()

        # Save feedback for David's memory
        if reason and reason != "Rejected by operator":
            feedback = {
                "type": "content_rejection",
                "approval_id": approval_id,
                "reason": reason,
                "content_context": {
                    "action_type": action_type,
                    "text": action_data.get("text", action_data.get("script", ""))[:500],
                },
                "timestamp": datetime.now().isoformat(),
            }
            feedback_path = FEEDBACK_DIR / f"feedback_{approval_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(feedback_path, "w") as f:
                json.dump(feedback, f, indent=2)

        log_activity("approval", f"Rejected {action_type} #{approval_id}: {reason}")

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/edit/<int:approval_id>", methods=["POST"])
@login_required
def api_edit(approval_id):
    """Edit and approve a pending item, then schedule it."""
    new_text = request.json.get("text", "")
    if not new_text:
        return jsonify({"success": False, "error": "No text provided"})

    try:
        conn = get_db(APPROVAL_DB)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({"success": False, "error": "Not found"})

        action_data = json.loads(row["action_data"])
        action_type = row["action_type"]
        action_data["text"] = new_text

        cursor.execute(
            "UPDATE approvals SET action_data = ?, status = 'approved', reviewed_at = ? WHERE id = ?",
            (json.dumps(action_data), datetime.now().isoformat(), approval_id)
        )
        conn.commit()
        conn.close()

        # Pick the next available tweet slot
        scheduled_time = _get_next_available_tweet_slot()

        # Write schedule request with edited data
        schedule_request = {
            "approval_id": approval_id,
            "action_type": action_type,
            "action_data": action_data,
            "content_type": action_type,
            "scheduled_time": scheduled_time.isoformat(),
            "approved_at": datetime.now().isoformat(),
        }
        request_path = FEEDBACK_DIR / f"schedule_{approval_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(request_path, "w") as f:
            json.dump(schedule_request, f, indent=2)

        log_activity("approval", f"Edited & scheduled {action_type} #{approval_id} for {scheduled_time.strftime('%I:%M %p UTC')}")

        return jsonify({
            "success": True,
            "scheduled_time": scheduled_time.strftime("%I:%M %p UTC"),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/health")
def api_health():
    """Health check endpoint — no auth required (for monitoring tools).

    Returns 200 if David's status file was updated within the last 5 minutes.
    Returns 503 if stale or missing.
    """
    status_file = DATA_DIR / "david_status.json"
    try:
        if not status_file.exists():
            return jsonify({"healthy": False, "reason": "No status file"}), 503

        import os
        mtime = os.path.getmtime(status_file)
        age_seconds = (datetime.now().timestamp() - mtime)

        with open(status_file) as f:
            status = json.load(f)

        if age_seconds > 300:  # 5 minutes = stale
            return jsonify({
                "healthy": False,
                "reason": "Status file stale",
                "age_seconds": int(age_seconds),
                "last_status": status.get("status", "unknown"),
            }), 503

        return jsonify({
            "healthy": True,
            "status": status.get("status", "unknown"),
            "age_seconds": int(age_seconds),
            "timestamp_utc": status.get("timestamp_utc", ""),
        })

    except Exception as e:
        return jsonify({"healthy": False, "reason": str(e)}), 503


@app.route("/api/stats")
@login_required
def api_stats():
    """Get current stats."""
    return jsonify(get_stats())


@app.route("/api/activity")
@login_required
def api_activity():
    """Get recent activity."""
    limit = request.args.get("limit", 20, type=int)
    return jsonify(get_recent_activity(limit=limit))


# ============== DATA FUNCTIONS ==============

def get_david_status():
    """Get David's current status from status file."""
    status_file = DATA_DIR / "david_status.json"
    try:
        if status_file.exists():
            with open(status_file) as f:
                return json.load(f)
    except:
        pass
    return {
        "online": False,
        "timestamp_dubai": "Unknown",
        "status": "unknown"
    }


def get_stats():
    """Get dashboard statistics."""
    david_status = get_david_status()
    stats = {
        "pending_approvals": 0,
        "tweets_today": 0,
        "tweets_week": 0,
        "research_items_today": 0,
        "high_score_findings": 0,
        "system_status": david_status["status"],
        "david_online": david_status["online"],
        "david_timestamp": david_status["timestamp_dubai"]
    }

    try:
        # Pending approvals
        if APPROVAL_DB.exists():
            conn = get_db(APPROVAL_DB)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM approvals WHERE status = 'pending'")
            stats["pending_approvals"] = cursor.fetchone()[0]

            # Tweets today
            today = datetime.now().date().isoformat()
            cursor.execute(
                "SELECT COUNT(*) FROM approvals WHERE status = 'approved' AND action_type = 'tweet' AND reviewed_at LIKE ?",
                (f"{today}%",)
            )
            stats["tweets_today"] = cursor.fetchone()[0]

            # Tweets this week
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            cursor.execute(
                "SELECT COUNT(*) FROM approvals WHERE status = 'approved' AND action_type = 'tweet' AND reviewed_at > ?",
                (week_ago,)
            )
            stats["tweets_week"] = cursor.fetchone()[0]
            conn.close()

        # Research items
        if RESEARCH_DB.exists():
            conn = get_db(RESEARCH_DB)
            cursor = conn.cursor()
            today = datetime.now().date().isoformat()
            cursor.execute(
                "SELECT COUNT(*) FROM research_items WHERE scraped_at LIKE ?",
                (f"{today}%",)
            )
            stats["research_items_today"] = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM research_items WHERE relevance_score >= 8"
            )
            stats["high_score_findings"] = cursor.fetchone()[0]
            conn.close()

        # System status is already set from david_status.json above

    except Exception as e:
        stats["error"] = str(e)

    return stats


def get_pending_approval_count():
    """Get count of pending approvals."""
    try:
        if APPROVAL_DB.exists():
            conn = get_db(APPROVAL_DB)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM approvals WHERE status = 'pending'")
            count = cursor.fetchone()[0]
            conn.close()
            return count
    except:
        pass
    return 0


def get_pending_approvals():
    """Get all pending approvals."""
    approvals = []
    try:
        if APPROVAL_DB.exists():
            conn = get_db(APPROVAL_DB)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, project_id, agent_id, action_type, action_data,
                       context_summary, created_at
                FROM approvals
                WHERE status = 'pending'
                ORDER BY created_at DESC
            """)
            for row in cursor.fetchall():
                approval = dict(row)
                approval["action_data"] = json.loads(approval["action_data"])
                approvals.append(approval)
            conn.close()
    except Exception as e:
        print(f"Error getting approvals: {e}")
    return approvals


def get_research_findings(limit=50):
    """Get research findings sorted by score."""
    findings = []
    try:
        if RESEARCH_DB.exists():
            conn = get_db(RESEARCH_DB)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, source, title, url, summary, relevance_score,
                       priority, suggested_action, scraped_at
                FROM research_items
                WHERE relevance_score > 0
                ORDER BY relevance_score DESC, scraped_at DESC
                LIMIT ?
            """, (limit,))
            findings = [dict(row) for row in cursor.fetchall()]
            conn.close()
    except Exception as e:
        print(f"Error getting research: {e}")
    return findings


def get_tweet_history(limit=50):
    """Get approved tweets."""
    tweets = []
    try:
        if APPROVAL_DB.exists():
            conn = get_db(APPROVAL_DB)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, action_data, context_summary, reviewed_at
                FROM approvals
                WHERE status = 'approved' AND action_type = 'tweet'
                ORDER BY reviewed_at DESC
                LIMIT ?
            """, (limit,))
            for row in cursor.fetchall():
                tweet = dict(row)
                tweet["action_data"] = json.loads(tweet["action_data"])
                tweets.append(tweet)
            conn.close()
    except Exception as e:
        print(f"Error getting tweets: {e}")
    return tweets


def get_recent_activity(limit=20):
    """Get recent activity from audit log."""
    activity = []
    try:
        audit_db = DATA_DIR / "audit.db"
        if audit_db.exists():
            conn = get_db(audit_db)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT timestamp, project_id, event_type, category, message, details
                FROM audit_log
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            activity = [dict(row) for row in cursor.fetchall()]
            conn.close()
    except Exception as e:
        print(f"Error getting activity: {e}")

    return activity


def log_activity(category, message):
    """Log an activity to the audit log."""
    try:
        audit_db = DATA_DIR / "audit.db"
        if audit_db.exists():
            conn = get_db(audit_db)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_log (timestamp, project_id, event_type, category, message)
                VALUES (?, ?, ?, ?, ?)
            """, (datetime.now().isoformat(), "dashboard", "info", category, message))
            conn.commit()
            conn.close()
    except Exception as e:
        print(f"Error logging activity: {e}")


def get_schedule_data():
    """Build schedule data for the calendar view."""
    now = datetime.utcnow()
    today = now.date()
    week_ago = (now - timedelta(days=7)).isoformat()
    optimal_hours = PLATFORM_OPTIMAL_HOURS["twitter"]

    stats = {"pending": 0, "approved": 0, "scheduled": 0, "posted": 0, "failed": 0}
    scheduled_items = []
    pending_items = []

    # Approval queue — pending items + recent history
    try:
        if APPROVAL_DB.exists():
            conn = get_db(APPROVAL_DB)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, action_type, action_data, status, created_at, reviewed_at, agent_id
                FROM approvals
                WHERE created_at > ? OR status = 'pending'
                ORDER BY created_at DESC
            """, (week_ago,))
            for row in cursor.fetchall():
                item = dict(row)
                action_data = json.loads(item["action_data"])
                text = action_data.get("text", action_data.get("script", ""))

                if item["status"] == "pending":
                    stats["pending"] += 1
                    pending_items.append({
                        "id": item["id"],
                        "type": item["action_type"],
                        "text": (text or "")[:80],
                        "status": "pending",
                        "created_at": item["created_at"],
                        "agent": item["agent_id"] or "david",
                    })
                elif item["status"] == "approved":
                    stats["approved"] += 1
                    # Show approved items on calendar (approved != posted)
                    ts = item["reviewed_at"] or item["created_at"]
                    if ts:
                        platform = "twitter" if item["action_type"] in ("tweet", "thread", "reply") else "multi"
                        scheduled_items.append({
                            "id": f"ap_{item['id']}",
                            "type": item["action_type"],
                            "text": (text or "")[:80],
                            "status": "approved",
                            "scheduled_time": ts,
                            "executed_at": None,
                            "agent": item["agent_id"] or "david",
                            "platform": platform,
                        })
            conn.close()
    except Exception as e:
        print(f"Schedule: error reading approval queue: {e}")

    # Scheduler — items with actual scheduled times (these are the source of truth)
    scheduler_approval_ids = set()  # Track which approval IDs have scheduler entries
    try:
        if SCHEDULER_DB.exists():
            conn = get_db(SCHEDULER_DB)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT job_id, content_type, content_data, scheduled_time,
                       status, created_at, executed_at
                FROM scheduled_content
                WHERE scheduled_time > ? OR status = 'pending'
                ORDER BY scheduled_time ASC
            """, (week_ago,))
            for row in cursor.fetchall():
                item = dict(row)
                content_data = json.loads(item["content_data"])
                text = content_data.get("text", content_data.get("script", ""))

                # Track approval IDs so we can deduplicate
                aid = content_data.get("approval_id")
                if aid:
                    scheduler_approval_ids.add(int(aid))

                display_status = item["status"]
                if display_status == "executed":
                    display_status = "posted"
                    stats["posted"] += 1
                elif display_status == "pending":
                    display_status = "scheduled"
                    stats["scheduled"] += 1
                elif display_status == "failed":
                    stats["failed"] += 1

                platform = content_data.get("platform", "twitter")
                if item["content_type"] in ("tweet", "thread", "reply"):
                    platform = "twitter"

                scheduled_items.append({
                    "id": item["job_id"],
                    "type": item["content_type"],
                    "text": (text or "")[:80],
                    "status": display_status,
                    "scheduled_time": item["scheduled_time"],
                    "executed_at": item["executed_at"],
                    "agent": content_data.get("agent", "david"),
                    "platform": platform,
                })
            conn.close()
    except Exception as e:
        print(f"Schedule: error reading scheduler: {e}")

    # Remove approval queue items that already have scheduler entries (prevent duplicates)
    scheduled_items = [
        si for si in scheduled_items
        if not (si["id"].startswith("ap_") and int(si["id"][3:]) in scheduler_approval_ids)
    ]

    # Build 7-day grid (3 past + today + 3 future)
    days = []
    for day_offset in range(-3, 4):
        day_date = today + timedelta(days=day_offset)
        day_slots = {}
        for hour in optimal_hours:
            slot_content = []
            for si in scheduled_items:
                try:
                    ts = datetime.fromisoformat(si["scheduled_time"])
                    if ts.date() != day_date:
                        continue
                    # Place item in nearest optimal slot
                    nearest = min(optimal_hours, key=lambda h: abs(ts.hour + ts.minute / 60 - h))
                    if nearest == hour:
                        slot_content.append(si)
                except (ValueError, TypeError):
                    pass
            day_slots[hour] = slot_content
        days.append({
            "date": day_date.isoformat(),
            "label": day_date.strftime("%a %b %d"),
            "is_today": day_date == today,
            "is_past": day_date < today,
            "slots": day_slots,
        })

    # Calculate gaps (future empty optimal slots, next 3 days)
    gaps = 0
    next_empty = None
    for day_offset in range(4):
        day_date = today + timedelta(days=day_offset)
        for hour in optimal_hours:
            slot_time = datetime(day_date.year, day_date.month, day_date.day, hour)
            if slot_time <= now:
                continue
            has_content = False
            for si in scheduled_items:
                if si["status"] != "scheduled":
                    continue
                try:
                    ts = datetime.fromisoformat(si["scheduled_time"])
                    if abs((ts - slot_time).total_seconds()) < 3600:
                        has_content = True
                        break
                except (ValueError, TypeError):
                    pass
            if not has_content:
                gaps += 1
                if next_empty is None:
                    next_empty = slot_time
    stats["gaps"] = gaps

    # Recent posted items for bottom section
    recent_posted = [si for si in scheduled_items if si["status"] == "posted"]
    recent_posted.sort(key=lambda x: x["scheduled_time"], reverse=True)

    return {
        "days": days,
        "stats": stats,
        "optimal_hours": optimal_hours,
        "next_empty": next_empty.strftime("%a %I%p UTC") if next_empty else None,
        "pending_items": pending_items,
        "recent_posted": recent_posted[:20],
    }


# ============== CONTENT DATA FUNCTIONS ==============

def get_pending_content(platform_filter: str = "") -> list[dict]:
    """Get pending video/content items for the content review queue.

    Returns both script_review (Stage 1) and video_distribute (Stage 2) items.
    """
    items = []
    try:
        if APPROVAL_DB.exists():
            conn = get_db(APPROVAL_DB)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, project_id, agent_id, action_type, action_data,
                       context_summary, created_at
                FROM approvals
                WHERE status = 'pending'
                AND action_type IN ('script_review', 'video_distribute', 'video_create', 'video_tweet')
                ORDER BY created_at DESC
            """)
            for row in cursor.fetchall():
                item = dict(row)
                action_data = json.loads(item["action_data"])

                # Determine stage based on action_type
                if item["action_type"] == "script_review":
                    stage = 1
                    stage_label = "Stage 1: Script Review"
                else:
                    stage = 2
                    stage_label = "Stage 2: Video Review"

                item.update({
                    "script": action_data.get("script", ""),
                    "video_path": action_data.get("video_path", ""),
                    "mood": action_data.get("mood", ""),
                    "pillar": action_data.get("pillar", ""),
                    "theme_title": action_data.get("theme_title", ""),
                    "category": action_data.get("category", ""),
                    "word_count": action_data.get("word_count", 0),
                    "estimated_duration": action_data.get("estimated_duration", 0),
                    "stage": stage,
                    "stage_label": stage_label,
                })
                items.append(item)
            conn.close()
    except Exception as e:
        print(f"Error getting content: {e}")
    return items


def get_content_platform_counts() -> dict:
    """Get count of pending content per platform.

    Since all video content targets all platforms, counts are the same.
    This will differ when platform-specific content is supported.
    """
    total = 0
    try:
        if APPROVAL_DB.exists():
            conn = get_db(APPROVAL_DB)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM approvals
                WHERE status = 'pending'
                AND action_type IN ('script_review', 'video_distribute', 'video_create', 'video_tweet')
            """)
            total = cursor.fetchone()[0]
            conn.close()
    except Exception:
        pass
    return {"twitter": total, "youtube": total, "tiktok": total}


def get_content_count():
    """Get count of pending content items."""
    try:
        if APPROVAL_DB.exists():
            conn = get_db(APPROVAL_DB)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM approvals
                WHERE status = 'pending'
                AND action_type IN ('script_review', 'video_distribute', 'video_create', 'video_tweet')
            """)
            count = cursor.fetchone()[0]
            conn.close()
            return count
    except Exception:
        pass
    return 0


def get_scheduled_content() -> list[dict]:
    """Get upcoming scheduled content posts."""
    items = []
    try:
        if SCHEDULER_DB.exists():
            conn = get_db(SCHEDULER_DB)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT job_id, content_type, content_data, scheduled_time, status
                FROM scheduled_content
                WHERE status = 'pending'
                ORDER BY scheduled_time ASC
                LIMIT 20
            """)
            items = [dict(row) for row in cursor.fetchall()]
            conn.close()
    except Exception as e:
        print(f"Error getting scheduled content: {e}")
    return items


def _get_next_optimal_slot(platforms: list[str]) -> datetime:
    """
    Find the next optimal posting time based on platform engagement research.

    Picks the soonest time that's at least 30 minutes from now,
    across all target platforms.
    """
    now = datetime.utcnow()
    min_post_time = now + timedelta(minutes=30)

    # Collect all candidate hours across requested platforms
    candidate_hours = set()
    for platform in platforms:
        hours = PLATFORM_OPTIMAL_HOURS.get(platform, [12, 18])
        candidate_hours.update(hours)

    # Find the next available slot
    candidates = []
    for hour in sorted(candidate_hours):
        slot = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if slot <= min_post_time:
            slot += timedelta(days=1)
        candidates.append(slot)

    if candidates:
        return min(candidates)

    # Fallback: 2 hours from now
    return now + timedelta(hours=2)


def _get_next_available_tweet_slot() -> datetime:
    """
    Find the next available tweet slot from Momo's daily plan.

    Reads today's plan from growth.db (daily_tweet_schedule table).
    Assigns approved tweet to next available planned slot (90min conflict window).
    Fallback: organic time 2-4h from now with natural-looking minute.
    """
    now = datetime.utcnow()
    GROWTH_DB = DATA_DIR / "growth.db"

    # --- Try Momo's plan first ---
    try:
        if GROWTH_DB.exists():
            conn = sqlite3.connect(str(GROWTH_DB))
            conn.row_factory = sqlite3.Row
            today = now.strftime("%Y-%m-%d")
            row = conn.execute(
                "SELECT slot_times FROM daily_tweet_schedule WHERE schedule_date = ? ORDER BY id DESC LIMIT 1",
                (today,),
            ).fetchone()
            conn.close()

            if row:
                import json as _json
                slot_times = _json.loads(row["slot_times"])

                # Read already-scheduled times from scheduler.db
                taken_times = []
                try:
                    if SCHEDULER_DB.exists():
                        sconn = sqlite3.connect(str(SCHEDULER_DB))
                        sconn.row_factory = sqlite3.Row
                        rows = sconn.execute(
                            "SELECT scheduled_time FROM scheduled_content WHERE status = 'pending'"
                        ).fetchall()
                        sconn.close()
                        taken_times = [datetime.fromisoformat(r["scheduled_time"]) for r in rows]
                except Exception:
                    pass

                # Find next available planned slot
                for slot_str in slot_times:
                    slot = datetime.fromisoformat(slot_str)
                    # Strip timezone info for comparison with naive utcnow
                    if slot.tzinfo is not None:
                        slot = slot.replace(tzinfo=None)
                    # Must be at least 5 minutes from now
                    if slot <= now + timedelta(minutes=5):
                        continue
                    # Check conflict: no other post within 90 minutes of this slot
                    def _strip_tz(dt):
                        return dt.replace(tzinfo=None) if dt.tzinfo else dt
                    conflict = any(
                        abs((_strip_tz(t) - slot).total_seconds()) < 5400
                        for t in taken_times
                    )
                    if not conflict:
                        return slot

    except Exception as e:
        print(f"Error reading Momo's plan: {e}")

    # --- Fallback: organic time 2-4h from now ---
    hours_ahead = random.uniform(2.0, 4.0)
    fallback = now + timedelta(hours=hours_ahead)
    # Natural-looking minute (never :00 or :30)
    minute = random.randint(1, 58)
    while minute in (0, 30):
        minute = random.randint(1, 58)
    fallback = fallback.replace(minute=minute, second=0, microsecond=0)
    return fallback


# ============== TEMPLATE CONTEXT ==============

# Registered AI personalities
PERSONALITIES = [
    {
        "id": "david-flip",
        "name": "David Flip",
        "role": "Content Creator",
        "color": "#58a6ff",
        "gradient": "linear-gradient(135deg, #58a6ff, #a371f7)",
    },
    {
        "id": "echo",
        "name": "Echo",
        "role": "Intelligence Analyst",
        "color": "#3fb950",
        "gradient": "linear-gradient(135deg, #3fb950, #58a6ff)",
    },
    {
        "id": "oprah",
        "name": "Oprah",
        "role": "Operations",
        "color": "#f0883e",
        "gradient": "linear-gradient(135deg, #f0883e, #da3633)",
    },
    {
        "id": "deva",
        "name": "Deva",
        "role": "Game Developer",
        "color": "#a371f7",
        "gradient": "linear-gradient(135deg, #a371f7, #f778ba)",
    },
    {
        "id": "momentum",
        "name": "Momentum",
        "role": "Growth Agent",
        "color": "#f778ba",
        "gradient": "linear-gradient(135deg, #f778ba, #58a6ff)",
    },
]


@app.context_processor
def inject_counts():
    """Inject counts and personality info into all templates."""
    return {
        "pending_count": get_pending_approval_count(),
        "content_count": get_content_count(),
        "personalities": PERSONALITIES,
    }


# ============== MAIN ==============

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
